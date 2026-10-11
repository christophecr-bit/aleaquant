"""Évaluation nouvelle : oracles combinatoires et reprise bornée sans doublon."""
import copy
import fcntl
from hashlib import sha256
from itertools import combinations
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import portfolio_evaluation as evaluation  # noqa: E402
from portfolio_import import content_hash  # noqa: E402

GRIDS = [[[1, 2, 3, 4, 5], [1, 2]], [[6, 7, 8, 9, 10], [3, 4]]]
OTHER_GRIDS = [[[1, 6, 11, 16, 21], [5, 6]], [[2, 7, 12, 17, 22], [7, 8]]]


def portfolio(grids):
    return {'content_sha256': content_hash(grids), 'grids': copy.deepcopy(grids)}


def protocol(**changes):
    value = {'method': 'monte_carlo', 'draws': 257, 'seed': 2026100907,
             'batch_size': 64, 'max_seconds': 5,
             'metrics': list(evaluation.EVENTS)}
    value.update(changes)
    return value


def checksum(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class ExplicitDrawTests(unittest.TestCase):
    def test_prizes_are_counted_on_each_individual_grid(self):
        draws = [
            [[1, 2, 3, 4, 5], [3, 4]],  # 5+0 on first; 0+2 is not a prize
            [[1, 6, 11, 12, 13], [3, 4]], # 1+0 first, 1+2 second
            [[1, 6, 11, 12, 13], [1, 3]], # 1+1 twice: zero prizes
            [[1, 2, 6, 7, 11], [5, 6]],  # two winning 2+0 grids
            [[1, 2, 3, 11, 12], [5, 6]], # one 3+0 grid
        ]
        self.assertEqual(evaluation.evaluate_draws(GRIDS, draws), {
            'any_prize': 4, 'multiple_prizes': 1, 'at_least_3_numbers': 2,
            'at_least_4_numbers': 1, 'winning_grids_sum': 5})

    def test_exhaustive_miniature_against_a_set_intersection_oracle(self):
        draws = [[list(numbers), list(stars)]
                 for numbers in combinations(range(1, 11), 5)
                 for stars in combinations(range(1, 5), 2)]
        expected = {name: 0 for name in evaluation.COUNTERS}
        for numbers, stars in draws:
            hits = [(len(set(numbers) & set(grid[0])), len(set(stars) & set(grid[1])))
                    for grid in GRIDS]
            wins = sum(number_hits >= 2 or (number_hits == 1 and star_hits == 2)
                       for number_hits, star_hits in hits)
            expected['any_prize'] += wins >= 1
            expected['multiple_prizes'] += wins >= 2
            expected['at_least_3_numbers'] += any(n >= 3 for n, s in hits)
            expected['at_least_4_numbers'] += any(n >= 4 for n, s in hits)
            expected['winning_grids_sum'] += wins
        self.assertEqual(len(draws), 1512)
        self.assertEqual(evaluation.evaluate_draws(GRIDS, draws), expected)
        self.assertEqual(evaluation.evaluate_draws(GRIDS, []),
                         {name: 0 for name in evaluation.COUNTERS})

    def test_single_grid_exact_law_covers_all_139838160_outcomes_analytically(self):
        weights = {}
        for number_hits in range(6):
            for star_hits in range(3):
                weights[number_hits, star_hits] = (
                    math.comb(5, number_hits) * math.comb(45, 5 - number_hits)
                    * math.comb(2, star_hits) * math.comb(10, 2 - star_hits))
        total = sum(weights.values())
        self.assertEqual(total, 139838160)
        prize_count = sum(weight for (n, s), weight in weights.items()
                          if (n, s) in {(1, 2), (2, 0), (2, 1), (2, 2),
                                        (3, 0), (3, 1), (3, 2), (4, 0),
                                        (4, 1), (4, 2), (5, 0), (5, 1), (5, 2)})
        single = evaluation.exact_analytics(GRIDS[:1])
        double = evaluation.exact_analytics(GRIDS)
        self.assertAlmostEqual(single['theoretical_mean_winning_grids'], prize_count / total)
        self.assertEqual(single['jackpot_probability'], weights[5, 2] / total)
        self.assertAlmostEqual(double['theoretical_mean_winning_grids'], 2 * prize_count / total)
        self.assertEqual(double['jackpot_probability'], 2 / total)

    def test_uniform_draws_have_exact_cardinalities_and_no_replacement(self):
        first = np.random.Generator(np.random.PCG64(17))
        second = np.random.Generator(np.random.PCG64(17))
        numbers, stars = evaluation._uniform_draws(first, 101)
        same_numbers, same_stars = evaluation._uniform_draws(second, 101)
        np.testing.assert_array_equal(numbers, same_numbers)
        np.testing.assert_array_equal(stars, same_stars)
        self.assertEqual(numbers.shape, (101, 5))
        self.assertEqual(stars.shape, (101, 2))
        self.assertTrue(all(len(set(row)) == 5 for row in numbers))
        self.assertTrue(all(len(set(row)) == 2 for row in stars))
        self.assertTrue(np.all((1 <= numbers) & (numbers <= 50)))
        self.assertTrue(np.all((1 <= stars) & (stars <= 12)))

    def test_malformed_grids_and_draws_are_rejected(self):
        for grids in [[], GRIDS + [GRIDS[0]], [[[1, 2, 3, 4, True], [1, 2]]],
                      [[[1, 2, 3, 4, 51], [1, 2]]], [[[1, 2, 3, 4, 5], [1, 13]]],
                      [[[1, 2, 3, 4, 5], [1, 1]]]]:
            with self.subTest(grids=grids), self.assertRaises(ValueError):
                evaluation.evaluate_draws(grids, [])
        for draw in [[[1, 2, 3, 4, 5], [1]], [[1, 2, 3, 4, 4], [1, 2]],
                     [[0, 2, 3, 4, 5], [1, 2]], [[1, 2, 3, 4, 5], [False, 2]]]:
            with self.subTest(draw=draw), self.assertRaises(ValueError):
                evaluation.evaluate_draws(GRIDS, [draw])


class ResumableEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.portfolios = [portfolio(GRIDS), portfolio(OTHER_GRIDS)]

    def run_at(self, name, **options):
        return evaluation.evaluate_many(self.portfolios, protocol(), self.directory / name, **options)

    def test_resume_and_complete_checkpoint_do_not_double_count(self):
        full = self.run_at('full')
        progress = []
        paused = self.run_at('resumed', progress=progress.append, stop_after_batches=1)
        self.assertEqual(paused['status'], 'interrupted')
        self.assertEqual(paused['completed_draws'], 64)
        self.assertEqual(paused['results'], {})
        self.assertFalse((self.directory / 'resumed/results.json').exists())
        self.assertEqual(progress[0]['completed_draws'], 64)
        resumed = self.run_at('resumed')
        self.assertEqual(resumed['status'], 'complete')
        self.assertEqual(resumed['completed_draws'], 257)
        self.assertEqual(resumed['batch_count'], 5)
        self.assertEqual(full['signature'], resumed['signature'])
        self.assertEqual(full['draw_stream_sha256'], resumed['draw_stream_sha256'])
        self.assertEqual(full['results'], resumed['results'])
        again = self.run_at('resumed')
        self.assertEqual(again, resumed)
        self.assertFalse(list((self.directory / 'resumed').glob('*.tmp')))
        self.assertEqual(json.loads((self.directory / 'resumed/results.json').read_text()), resumed)
        for fingerprint, sim in resumed['results'].items():
            self.assertEqual(sim['content_sha256'], fingerprint)
            self.assertEqual(sim['draws'], 257)
            self.assertEqual(sim['seed'], protocol()['seed'])
            self.assertTrue(sim['same_draws_for_all'])
            self.assertTrue(sim['independent_of_generation'])
            self.assertEqual(sim['engine_version'], evaluation.ENGINE_VERSION)
            self.assertEqual(sim['source_sha256'], evaluation._source_hash())
            self.assertEqual(sim['environment']['numpy'], np.__version__)
            self.assertRegex(sim['evaluation_sha256'], '^[0-9a-f]{64}$')
            for metric in sim['metrics'].values():
                self.assertEqual(metric['probability'], metric['count'] / 257)
                self.assertTrue(0 <= metric['ci95_wilson'][0] <= metric['ci95_wilson'][1] <= 1)

    def test_all_portfolios_share_the_draws_and_order_does_not_change_results(self):
        together = self.run_at('together')
        reversed_order = evaluation.evaluate_many(list(reversed(self.portfolios)), protocol(),
                                                  self.directory / 'reversed')
        alone = evaluation.evaluate_many(self.portfolios[:1], protocol(), self.directory / 'alone')
        self.assertEqual(together['signature'], reversed_order['signature'])
        self.assertEqual(together['results'], reversed_order['results'])
        self.assertEqual(together['draw_stream_sha256'], alone['draw_stream_sha256'])
        key = self.portfolios[0]['content_sha256']
        for name in ['metrics', 'mean_winning_grids', 'theoretical_mean_winning_grids']:
            self.assertEqual(together['results'][key][name], alone['results'][key][name])

    def test_compute_budget_interrupts_without_a_final_result(self):
        with patch.object(evaluation.time, 'monotonic', side_effect=[0, 10]):
            result = evaluation.evaluate_many(self.portfolios, protocol(max_seconds=1),
                                              self.directory / 'timed')
        self.assertEqual(result['status'], 'interrupted')
        self.assertEqual(result['completed_draws'], 0)
        self.assertEqual(result['results'], {})
        self.assertFalse((self.directory / 'timed/results.json').exists())

    def test_configuration_set_and_content_mismatches_are_rejected(self):
        self.run_at('paused', stop_after_batches=1)
        directory = self.directory / 'paused'
        for change in [{'seed': 18}, {'draws': 258}, {'batch_size': 63}, {'max_seconds': 4},
                       {'metrics': list(reversed(evaluation.EVENTS))}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                evaluation.evaluate_many(self.portfolios, protocol(**change), directory)
        with self.assertRaises(ValueError):
            evaluation.evaluate_many(self.portfolios[:1], protocol(), directory)
        changed = copy.deepcopy(self.portfolios)
        changed[0]['grids'][0][0][-1] = 50
        with self.assertRaises(ValueError):
            evaluation.evaluate_many(changed, protocol(), directory)

    def test_code_change_refuses_resume_even_if_engine_version_is_unchanged(self):
        paused = self.run_at('paused-code', stop_after_batches=1)
        self.assertEqual(paused['source_sha256'], evaluation._source_hash())
        with patch.object(evaluation, '_source_hash', return_value='a' * 64):
            with self.assertRaises(ValueError):
                self.run_at('paused-code')

    def test_corrupt_checkpoint_and_recomputed_but_invalid_payload_are_rejected(self):
        self.run_at('paused', stop_after_batches=1)
        path = self.directory / 'paused/checkpoint.json'
        original = json.loads(path.read_text())
        fingerprint = self.portfolios[0]['content_sha256']
        mutations = [
            lambda p: p.__setitem__('completed_draws', 63),
            lambda p: p['counts'][fingerprint].__setitem__('any_prize', True),
            lambda p: p['counts'][fingerprint].__setitem__('winning_grids_sum', 999),
            lambda p: p['rng_state']['state'].__setitem__('state', -1),
            lambda p: p['rng_state'].__setitem__('bit_generator', 'MT19937'),
            lambda p: p.__setitem__('portfolio_hashes', []),
            lambda p: p['environment'].__setitem__('numpy', 'other'),
            lambda p: p.__setitem__('unknown', 1),
            lambda p: p['protocol'].__setitem__('batch_size', True),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(mutation=index):
                document = copy.deepcopy(original)
                mutation(document['payload'])
                document['checksum_sha256'] = checksum(document['payload'])
                path.write_text(json.dumps(document))
                with self.assertRaises(ValueError):
                    self.run_at('paused')
        document = copy.deepcopy(original)
        document['checksum_sha256'] = '0' * 64
        path.write_text(json.dumps(document))
        with self.assertRaises(ValueError):
            self.run_at('paused')
        path.write_text('{not json')
        with self.assertRaises(ValueError):
            self.run_at('paused')
        path.write_text('{"payload": {}, "payload": {}}')
        with self.assertRaises(ValueError):
            self.run_at('paused')

    def test_failed_persistence_replays_from_the_previous_durable_frontier(self):
        original_write = evaluation._checkpoint_write
        calls = []
        def failing_write(path, payload):
            calls.append(payload['completed_draws'])
            if len(calls) == 2:
                raise OSError('test disk write failure')
            original_write(path, payload)
        with patch.object(evaluation, '_checkpoint_write', side_effect=failing_write):
            with self.assertRaises(OSError):
                self.run_at('failed')
        checkpoint = json.loads((self.directory / 'failed/checkpoint.json').read_text())
        self.assertEqual(checkpoint['payload']['completed_draws'], 0)
        replayed, full = self.run_at('failed'), self.run_at('full')
        self.assertEqual(replayed['results'], full['results'])
        self.assertEqual(replayed['draw_stream_sha256'], full['draw_stream_sha256'])

    def test_concurrent_run_and_orphan_results_are_rejected(self):
        directory = self.directory / 'locked'
        directory.mkdir()
        with (directory / '.evaluation.lock').open('a+') as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(ValueError):
                self.run_at('locked')
        orphan = self.directory / 'orphan'
        orphan.mkdir()
        (orphan / 'results.json').write_text('{}')
        with self.assertRaises(ValueError):
            self.run_at('orphan')

    def test_malformed_protocol_and_portfolios_are_rejected(self):
        for changes in [{'draws': True}, {'draws': 0}, {'draws': 1.5}, {'seed': -1},
                        {'seed': False}, {'batch_size': 0}, {'batch_size': 10001},
                        {'max_seconds': float('inf')}, {'max_seconds': float('nan')},
                        {'max_seconds': 10 ** 1000}, {'max_seconds': True},
                        {'metrics': ['any_prize'] * 4}, {'unknown': 1}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                evaluation.evaluate_many(self.portfolios, protocol(**changes), self.directory / 'invalid')
        for portfolios in [[], self.portfolios + self.portfolios[:1],
                           [{'content_sha256': '0' * 64, 'grids': GRIDS}],
                           [{'content_sha256': content_hash(GRIDS), 'grids': []}]]:
            with self.subTest(portfolios=portfolios), self.assertRaises(ValueError):
                evaluation.evaluate_many(portfolios, protocol(), self.directory / 'invalid')


if __name__ == '__main__':
    unittest.main()
