"""Bounded operator and exact-selection checks; no simulation is executed."""
from collections import Counter
from copy import deepcopy
import itertools
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))

from evolution.operators import OPERATORS, construct_candidate, select_survivors  # noqa: E402
from portfolio_contract import validate_grids  # noqa: E402
from portfolio_import import content_hash  # noqa: E402


def profile(count=3, numbers=15, stars=5, max_overlap=5):
    value = deepcopy(json.loads((ROOT / 'configs/studies/minimize-overlap-20x15x5-v1.json').read_text())['base_profile'])
    value['pool'].update(numbers=list(range(1, numbers + 1)), stars=list(range(1, stars + 1)),
                         number_count=numbers, star_count=stars)
    value['constraints'].update(grid_count=count, budget_max_eur=2.5 * count,
                                max_pairwise_overlap={'numbers': max_overlap, 'stars': 2})
    return value


def record(identifier, grids):
    return {'id': identifier, 'grids': deepcopy(grids), 'content_sha256': content_hash(grids)}


PARENT_A = [
    [[1, 2, 3, 4, 5], [1, 2]],
    [[6, 7, 8, 9, 10], [2, 3]],
    [[1, 6, 11, 12, 13], [4, 5]],
]
PARENT_B = [
    [[1, 2, 3, 4, 5], [1, 2]],
    [[2, 5, 8, 12, 14], [1, 4]],
    [[3, 7, 11, 14, 15], [3, 5]],
]


def grid_keys(grids):
    return {(tuple(grid[0]), tuple(grid[1])) for grid in grids}


class ForcedDuplicate(random.Random):
    """A single replacement of 5 by 6 must collide, with no hidden retry."""
    def __init__(self):
        super().__init__(0)
        self.calls = 0

    def randrange(self, *args):
        self.calls += 1
        if self.calls > 3:
            raise AssertionError('operator exceeded one proposal')
        return 0

    def choice(self, values):
        self.calls += 1
        if self.calls > 3:
            raise AssertionError('operator exceeded one proposal')
        return values[-1]


class EvolutionOperatorTests(unittest.TestCase):
    def test_explicit_rng_determinism_and_parent_conservation_for_all_operators(self):
        physical = profile()
        parents = [record('parent-a', PARENT_A), record('parent-b', PARENT_B)]
        original = json.dumps(parents, sort_keys=True)
        original_profile = deepcopy(physical)
        global_rng_state = random.getstate()
        for operator in OPERATORS:
            selected = parents if operator == 'grid_crossover_v1' else parents[:1]
            first = construct_candidate(operator, selected, physical, random.Random(111), 7)
            second = construct_candidate(operator, selected, physical, random.Random(111), 7)
            self.assertIsNotNone(first, operator)
            self.assertEqual(first, second)
            self.assertEqual(first['operator'], operator)
            self.assertEqual(first['parent_ids'], ['portfolio:' + p['content_sha256'] for p in selected])
            self.assertEqual(first['metadata']['parent_context_ids'], [p['id'] for p in selected])
            self.assertEqual(first['metadata']['attempt_index'], 7)
            self.assertTrue(first['metadata']['requires_pipeline_validation'])
            self.assertNotIn('certificate', first)
            self.assertEqual(validate_grids(first['grids'], physical), [])
            first['grids'][0][0][0] = -1
            self.assertEqual(json.dumps(parents, sort_keys=True), original)
        self.assertEqual(physical, original_profile)
        self.assertEqual(random.getstate(), global_rng_state)

    def test_number_mutation_changes_exactly_one_number_and_keeps_stars(self):
        parent = record('parent-a', PARENT_A)
        child = construct_candidate('replace_number_v1', [parent], profile(), random.Random(111), 0)
        changed = [i for i, (before, after) in enumerate(zip(parent['grids'], child['grids'])) if before != after]
        self.assertEqual(len(changed), 1)
        index = changed[0]
        self.assertEqual(len(set(parent['grids'][index][0]) ^ set(child['grids'][index][0])), 2)
        self.assertEqual([g[1] for g in child['grids']], [g[1] for g in parent['grids']])

    def test_number_swap_preserves_number_occurrences_and_all_star_components(self):
        parent = record('parent-a', PARENT_A)
        child = construct_candidate('swap_numbers_v1', [parent], profile(), random.Random(111), 0)
        self.assertEqual(Counter(n for g in child['grids'] for n in g[0]),
                         Counter(n for g in parent['grids'] for n in g[0]))
        self.assertEqual([g[1] for g in child['grids']], [g[1] for g in parent['grids']])
        differences = [len(set(a[0]) ^ set(b[0])) for a, b in zip(parent['grids'], child['grids']) if a != b]
        self.assertEqual(sorted(differences), [2, 2])

    def test_whole_grid_replacement_keeps_m_and_other_grids(self):
        parent = record('parent-a', PARENT_A)
        child = construct_candidate('replace_grid_v1', [parent], profile(), random.Random(111), 0)
        self.assertEqual(len(child['grids']), 3)
        self.assertEqual(sum(a != b for a, b in zip(parent['grids'], child['grids'])), 1)
        self.assertEqual(validate_grids(child['grids'], profile()), [])

    def test_crossover_uses_real_contributions_from_both_parents_without_new_grids(self):
        parents = [record('parent-a', PARENT_A), record('parent-b', PARENT_B)]
        left, right = grid_keys(PARENT_A), grid_keys(PARENT_B)
        for seed in range(32):
            child = construct_candidate('grid_crossover_v1', parents, profile(), random.Random(seed), seed)
            self.assertIsNotNone(child)
            keys = grid_keys(child['grids'])
            self.assertEqual(len(keys), 3)
            self.assertLessEqual(keys, left | right)
            self.assertTrue(keys & (left - right))
            self.assertTrue(keys & (right - left))
            self.assertNotIn(content_hash(child['grids']), [p['content_sha256'] for p in parents])
            self.assertEqual(validate_grids(child['grids'], profile()), [])
            for grid, sources in zip(child['grids'], child['metadata']['grid_parent_context_ids']):
                for source in sources:
                    original = parents[0] if source == 'parent-a' else parents[1]
                    self.assertIn((tuple(grid[0]), tuple(grid[1])), grid_keys(original['grids']))

    def test_duplicate_or_impossible_mutations_are_rejected_without_retry_or_repair(self):
        grids = [[[1, 2, 3, 4, 5], [1, 2]], [[1, 2, 3, 4, 6], [1, 2]]]
        parent = record('full-small-pool', grids)
        rng = ForcedDuplicate()
        self.assertIsNone(construct_candidate('replace_number_v1', [parent], profile(2, 6, 2), rng, 0))
        self.assertEqual(rng.calls, 3)
        fixed = record('fixed', [[[1, 2, 3, 4, 5], [1, 2]]])
        for operator in ('replace_number_v1', 'swap_numbers_v1', 'replace_grid_v1'):
            self.assertIsNone(construct_candidate(operator, [fixed], profile(1, 5, 2), random.Random(0), 0))
        self.assertEqual(parent['grids'], grids)

    def test_crossover_rejects_hard_overlap_violation_instead_of_repairing(self):
        left = [[[1, 2, 3, 4, 5], [1, 2]], [[6, 7, 8, 9, 10], [3, 4]]]
        right = [[[1, 2, 3, 6, 7], [1, 2]], [[4, 5, 8, 9, 10], [3, 4]]]
        physical = profile(2, 10, 4, max_overlap=0)
        parents = [record('left', left), record('right', right)]
        self.assertTrue(all(not validate_grids(p['grids'], physical) for p in parents))
        for seed in range(8):
            self.assertIsNone(construct_candidate('grid_crossover_v1', parents, physical, random.Random(seed), seed))
        self.assertEqual([p['grids'] for p in parents], [left, right])

    def test_crossover_rejects_identical_contents_and_single_grid_parent_case(self):
        same = [record('a', PARENT_A), record('alias-a', PARENT_A)]
        self.assertIsNone(construct_candidate('grid_crossover_v1', same, profile(), random.Random(0), 0))
        one = [record('a', [[[1, 2, 3, 4, 5], [1, 2]]]),
               record('b', [[[1, 2, 3, 4, 5], [1, 3]]])]
        self.assertIsNone(construct_candidate('grid_crossover_v1', one, profile(1, 5, 3), random.Random(0), 0))

    def test_selection_uses_exact_pareto_layers_and_ignores_mc_and_cached_metrics(self):
        concentrated = record('concentrated', [[[1, 2, 3, 4, 5], [1, 2]], [[1, 2, 3, 4, 6], [3, 4]]])
        intermediate = record('intermediate', [[[1, 2, 3, 4, 5], [1, 2]], [[4, 5, 6, 7, 8], [3, 4]]])
        spread = record('spread', [[[1, 2, 3, 4, 5], [1, 2]], [[6, 7, 8, 9, 10], [3, 4]]])
        concentrated.update(simulation={'probability': 1}, metric_values={'portfolio.distinct_pairs@v1': 1000000})
        spread.update(simulation={'probability': 0}, metric_values={'portfolio.distinct_pairs@v1': -1})
        candidates = [concentrated, spread, intermediate]
        snapshot = deepcopy(candidates)
        self.assertEqual([p['id'] for p in select_survivors(candidates, profile(2), 2)], ['spread', 'intermediate'])
        concentrated['simulation']['probability'], spread['simulation']['probability'] = 0, 1
        self.assertEqual([p['id'] for p in select_survivors(candidates, profile(2), 2)], ['spread', 'intermediate'])
        concentrated['simulation']['probability'], spread['simulation']['probability'] = 1, 0
        self.assertEqual(candidates, snapshot)

    def test_selection_deduplicates_contents_and_breaks_ties_stably_by_sha_and_id(self):
        a = record('a', [[[1, 2, 3, 4, 5], [1, 2]], [[6, 7, 8, 9, 10], [3, 4]]])
        b = record('b', [[[1, 3, 5, 7, 9], [1, 2]], [[2, 4, 6, 8, 10], [3, 4]]])
        alias = deepcopy(a)
        alias['id'] = 'z-alias'
        expected = [p['id'] for p in sorted((a, b), key=lambda p: (p['content_sha256'], p['id']))]
        for ordering in itertools.permutations((a, b, alias)):
            selected = select_survivors(list(ordering), profile(2), 5)
            self.assertEqual([p['id'] for p in selected], expected)
            self.assertEqual(len({p['content_sha256'] for p in selected}), 2)
        self.assertEqual(select_survivors([], profile(), 5), [])

    def test_invalid_api_inputs_or_corrupt_parent_hashes_raise(self):
        parent = record('a', PARENT_A)
        for operator, parents, rng, attempt in (
                ('unknown', [parent], random.Random(0), 0),
                ('replace_number_v1', [], random.Random(0), 0),
                ('grid_crossover_v1', [parent], random.Random(0), 0),
                ('replace_number_v1', [parent], 0, 0),
                ('replace_number_v1', [parent], random.Random(0), True),
                ('replace_number_v1', [parent], random.Random(0), .5)):
            with self.assertRaises(ValueError):
                construct_candidate(operator, parents, profile(), rng, attempt)
        broken = deepcopy(parent)
        broken['content_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'hash'):
            construct_candidate('replace_number_v1', [broken], profile(), random.Random(0), 0)
        for size in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                select_survivors([parent], profile(), size)


if __name__ == '__main__':
    unittest.main()
