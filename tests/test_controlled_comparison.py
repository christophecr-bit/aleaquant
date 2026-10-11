"""Pure qualification/analysis adversaries; counters are fixtures, no MC draws."""
from copy import deepcopy
from itertools import combinations, product
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))

from controlled.comparison import benchmark, qualify_controls  # noqa: E402
import portfolio_evaluation as mc  # noqa: E402
from portfolio_import import content_hash, digest  # noqa: E402
from portfolio_pipeline import make_record  # noqa: E402
from portfolio_proof import proof_for  # noqa: E402
from portfolio_search import generate_candidates  # noqa: E402

GENERATION_SIGNATURE = digest({'fixture': 'fresh-controlled-generation'})
COMPARE = {'method': 'monte_carlo', 'draws': 100, 'seed': 901, 'batch_size': 16,
           'max_seconds': 5, 'metrics': list(mc.EVENTS)}
CONFIRM = dict(COMPARE, seed=902)


def physical_profile(seed, weight=0, random_control=False, full_domain=False):
    p = deepcopy(json.loads((ROOT / 'configs/studies/minimize-overlap-20x15x5-v1.json').read_text())['base_profile'])
    numbers, stars = (list(range(1, 51)), list(range(1, 13))) if full_domain else (list(range(1, 10)), [1, 2, 3, 4])
    p.update(id='fixture_' + str(seed), family='RANDOM' if random_control else 'BALANCED')
    p['pool'].update(numbers=numbers, stars=stars, number_count=len(numbers), star_count=len(stars), seed=91)
    p['constraints'].update(grid_count=3, budget_max_eur=7.5, conditional_guarantee=None)
    p['search'].update(seed=seed, candidate_count=1, method='random' if random_control else 'prototype_greedy',
                       candidates_per_step=1 if random_control else 1200, max_attempts=3600, max_seconds=5)
    p['evaluation'] = dict(COMPARE, max_certificate_cases=1000)
    p['objectives']['minimize_overlap']['numbers'] = weight
    if random_control:
        for name in p['objectives']:
            if name != 'minimize_overlap':
                p['objectives'][name] = 0
        p['objectives']['minimize_overlap'].update(numbers=0, stars=0)
    return p


def attach_counter_fixture(records, protocol, role):
    """Use the shared result encoder on explicit valid integer counters only."""
    prepared = {r['content_sha256']: r['grids'] for r in records}
    metadata = {'schema': mc.CHECKPOINT_SCHEMA, 'engine_version': mc.ENGINE_VERSION,
                'source_sha256': mc._source_hash(), 'environment': mc._environment(),
                'protocol': protocol, 'portfolio_hashes': sorted(prepared)}
    counts = {}
    for index, fingerprint in enumerate(sorted(prepared)):
        any_count, multiple = 25 + index % 20, 5 + index % 10
        counts[fingerprint] = {'any_prize': any_count, 'multiple_prizes': multiple,
                               'at_least_3_numbers': 4 + index % 8, 'at_least_4_numbers': index % 3,
                               'winning_grids_sum': any_count + multiple + 1}
    payload = {**metadata, 'signature': digest(metadata), 'status': 'complete', 'completed_draws': protocol['draws'],
               'batch_count': 7, 'counts': counts, 'draw_stream_sha256': digest({'fixture_stream': role})}
    results = mc._result(payload, prepared)['results']
    for record in records:
        sim = results[record['content_sha256']]
        evaluation = {'id': 'evaluation:' + sim['evaluation_sha256'], 'method': 'monte_carlo', 'role': role,
                      'replayed': True, 'common_draws': True, 'protocol': protocol,
                      'source_generation_signature': GENERATION_SIGNATURE,
                      **{key: sim[key] for key in ('content_sha256', 'draws', 'seed', 'engine_version',
                                                 'source_sha256', 'environment', 'draw_stream_sha256')}}
        if role == 'comparison':
            record.update(evaluation=evaluation, simulation=sim)
        else:
            evaluation['independent_of_comparison'] = True
            record['confirmation'] = {'evaluation': evaluation, 'simulation': sim}


def fixtures():
    grid_space = [[[list(nums), list(stars)]][0]
                  for nums, stars in product(combinations(range(1, 10), 5), combinations(range(1, 5), 2))]
    main, controls = [], []
    for wi, weight in enumerate((0, .35, .7, 1.4)):
        for index, seed in enumerate(range(600, 610)):
            p = physical_profile(seed, weight)
            offset = wi * 30 + index * 2
            grids = [deepcopy(grid_space[offset + shift]) for shift in (0, 1, 3)]
            candidate = {'grids': grids, 'seed': seed, 'method': 'prototype_greedy', 'candidate_index': 0, 'score': 0}
            r = make_record(p, candidate, proof_for(grids, p), 'fixture-main-generation')
            r.update(id=f'main_w{wi}_s{seed}', study_factor={'weight': weight, 'seed': seed}, is_finalist=False)
            main.append(r)
    for role in ('same_pool', 'full_domain'):
        for seed in range(600, 610):
            p = physical_profile(seed, random_control=True, full_domain=role == 'full_domain')
            candidate = generate_candidates(p)['candidates'][0]
            r = make_record(p, candidate, proof_for(candidate['grids'], p), 'fixture-control-generation')
            r.update(id=f'control_{role}_{seed}', reference_benchmark={'role': role, 'generation_seed': seed,
                                                                    'selection_eligible': False},
                     is_starting_parent=False, is_survivor=False, is_finalist=False)
            controls.append(r)
    attach_counter_fixture(main + controls, COMPARE, 'comparison')
    finalists = [main[i] for i in (0, 11, 22, 24, 33)]
    for record in finalists:
        record['is_finalist'] = True
    attach_counter_fixture(finalists + controls, CONFIRM, 'confirmation')
    return main, controls


class ControlledComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main, cls.controls = fixtures()

    def qualification(self, main=None, controls=None, **options):
        return qualify_controls(self.main if main is None else main, self.controls if controls is None else controls,
                                'ablation', require_full_domain=True, expected_protocol=COMPARE,
                                expected_generation_signature=GENERATION_SIGNATURE, **options)

    def test_valid_controls_are_qualified_before_mc_and_for_each_complete_role(self):
        before = self.qualification(require_evaluation=False)
        self.assertEqual(before['status'], 'qualified')
        result = self.qualification()
        self.assertEqual(result['status'], 'qualified')
        self.assertEqual([c['reference_count'] for c in result['cohorts']], [10, 10])
        confirmation = qualify_controls(self.main, self.controls, 'ablation', role='confirmation',
                                        require_full_domain=True, expected_protocol=CONFIRM,
                                        expected_generation_signature=GENERATION_SIGNATURE)
        self.assertEqual(confirmation['status'], 'qualified')
        self.assertNotEqual(result['evaluation']['draw_stream_sha256'], confirmation['evaluation']['draw_stream_sha256'])

    def test_missing_and_optional_roles_have_explicit_statuses(self):
        self.assertEqual(self.qualification(controls=[])['status'], 'missing')
        short = self.qualification(controls=self.controls[1:])
        self.assertEqual(short['status'], 'missing')
        self.assertEqual(short['cohorts'][0]['reference_count'], 9)
        same = self.controls[:10]
        optional = qualify_controls(self.main, same, 'ablation', require_evaluation=False)
        self.assertEqual(optional['status'], 'qualified')
        self.assertEqual(optional['cohorts'][1]['status'], 'not_requested')
        self.assertEqual(self.qualification(controls=same, require_evaluation=False)['status'], 'missing')

    def test_methods_profiles_costs_rules_pools_and_selection_cannot_be_relabelled(self):
        mutations = [
            lambda r: r['generation'].update(method='prototype_greedy'),
            lambda r: r['constraint_profile']['objectives'].update(balance_numbers=1),
            lambda r: r.update(family='BALANCED'),
            lambda r: r['reference_benchmark'].update(role='another_pool'),
            lambda r: r['reference_benchmark'].update(selection_eligible=True),
            lambda r: r['lineage'].update(parent_ids=['portfolio:' + self.main[0]['content_sha256']]),
            lambda r: r.update(is_survivor=True),
            lambda r: r.update(budget_actual_eur=8),
            lambda r: r.update(grid_count=4),
            lambda r: r.update(rule_id='another-rule-v1'),
            lambda r: r['constraint_profile']['pool'].update(method='seeded_sample'),
            lambda r: r['reference_benchmark'].update(generation_seed=610),
            lambda r: r['constraint_profile']['game'].update(options=['etoile_plus']),
            lambda r: r.update(config_sha256='0' * 64),
        ]
        for mutate in mutations:
            controls = deepcopy(self.controls)
            mutate(controls[0])
            with self.subTest(mutate=mutate):
                result = self.qualification(controls=controls, require_evaluation=False)
                self.assertEqual(result['status'], 'refused')
                self.assertTrue(result['reasons'])
        controls = deepcopy(self.controls)
        controls[0]['constraint_profile']['pool'].update(numbers=list(range(1, 11)), number_count=10)
        controls[0]['pool_numbers'] = list(range(1, 11))
        self.assertEqual(self.qualification(controls=controls, require_evaluation=False)['status'], 'refused')

    def test_weight_zero_greedy_is_never_a_random_control(self):
        fake = deepcopy(self.main[0])
        fake.update(id='forged_random', family='RANDOM', is_finalist=False,
                    reference_benchmark={'role': 'same_pool', 'generation_seed': 600, 'selection_eligible': False})
        fake['reference_benchmark']['qualified'] = True
        controls = [fake] + deepcopy(self.controls[1:])
        self.assertEqual(self.qualification(controls=controls, require_evaluation=False)['status'], 'refused')

    def test_mc_protocol_source_environment_stream_content_and_counts_must_match(self):
        mutations = [
            lambda r: r['evaluation']['protocol'].update(batch_size=8),
            lambda r: r['evaluation'].update(seed=2701009),
            lambda r: r['simulation'].update(draws=99),
            lambda r: r['simulation'].update(source_sha256='0' * 64),
            lambda r: r['evaluation'].update(engine_version='archive-v0'),
            lambda r: r['simulation']['environment'].update(numpy='another-version'),
            lambda r: r['simulation'].update(draw_stream_sha256='0' * 64),
            lambda r: r['simulation'].update(content_sha256=self.main[0]['content_sha256']),
            lambda r: r['evaluation'].update(source_generation_signature='0' * 64),
            lambda r: r['simulation']['metrics']['any_prize'].update(probability=.99),
            lambda r: r['simulation']['metrics']['any_prize'].update(ci95_wilson=[0, 1]),
        ]
        for mutate in mutations:
            controls = deepcopy(self.controls)
            mutate(controls[0])
            with self.subTest(mutate=mutate):
                result = self.qualification(controls=controls)
                self.assertEqual(result['status'], 'refused')
                self.assertTrue(result['reasons'])

    def test_a_same_seed_old_mc_ensemble_is_refused_even_when_stream_and_source_match(self):
        controls = deepcopy(self.controls)
        # These results have exactly the same protocol, engine and stream but
        # came from an evaluation containing only controls, without MAIN.
        attach_counter_fixture(controls, COMPARE, 'comparison')
        result = self.qualification(controls=controls)
        self.assertEqual(result['status'], 'refused')
        self.assertIn('ensemble', result['reasons'][0]['message'])

    def test_full_domain_controls_with_other_declared_seeds_remain_unpaired(self):
        main, controls = deepcopy(self.main), deepcopy(self.controls[:10])
        for seed in range(800, 810):
            p = physical_profile(seed, random_control=True, full_domain=True)
            candidate = generate_candidates(p)['candidates'][0]
            r = make_record(p, candidate, proof_for(candidate['grids'], p), 'fixture-control-generation')
            r.update(id=f'control_full_domain_{seed}', reference_benchmark={
                'role': 'full_domain', 'generation_seed': seed, 'selection_eligible': False},
                is_starting_parent=False, is_survivor=False, is_finalist=False)
            controls.append(r)
        attach_counter_fixture(main + controls, COMPARE, 'comparison')
        attach_counter_fixture([r for r in main if r['is_finalist']] + controls, CONFIRM, 'confirmation')
        result = benchmark(main, controls, 'ablation', require_full_domain=True,
                           expected_protocol=COMPARE, expected_confirmation_protocol=CONFIRM,
                           expected_generation_signature=GENERATION_SIGNATURE)
        self.assertTrue(result['same_pool']['paired'])
        self.assertFalse(result['full_domain']['pool_effect']['paired'])
        self.assertEqual(result['full_domain']['pool_effect']['rows'], [])
        self.assertTrue(result['full_domain']['pool_effect']['mean_differences'])

    def test_confirmation_of_every_control_is_required_and_must_use_new_draws(self):
        controls = deepcopy(self.controls)
        del controls[0]['confirmation']
        missing = qualify_controls(self.main, controls, 'ablation', role='confirmation',
                                   require_full_domain=True, expected_protocol=CONFIRM)
        self.assertEqual(missing['status'], 'missing')
        with self.assertRaises(ValueError):
            benchmark(self.main, controls, 'ablation', require_full_domain=True)
        controls = deepcopy(self.controls)
        controls[0]['confirmation']['evaluation']['draw_stream_sha256'] = controls[0]['evaluation']['draw_stream_sha256']
        self.assertEqual(qualify_controls(self.main, controls, 'ablation', role='confirmation',
                                         require_full_domain=True, expected_protocol=CONFIRM)['status'], 'refused')

    def test_ablation_differences_are_main_minus_random_paired_on_each_seed(self):
        main, controls = deepcopy(self.main), deepcopy(self.controls)
        for record in main + controls:
            record['metric_values'] = {'portfolio.distinct_pairs@v1': -12345}
        snapshot = json.dumps([main, controls], sort_keys=True)
        result = benchmark(main, controls, 'ablation', require_full_domain=True,
                           expected_protocol=COMPARE, expected_confirmation_protocol=CONFIRM,
                           expected_generation_signature=GENERATION_SIGNATURE)
        self.assertEqual(result['status'], 'qualified')
        self.assertTrue(result['same_pool']['paired'])
        self.assertEqual(len(result['same_pool']['paired_differences']), 4)
        by_id = {r['id']: r for r in main + controls}
        for group in result['same_pool']['paired_differences']:
            self.assertEqual(group['n'], 10)
            self.assertEqual([row['seed'] for row in group['rows']], list(range(600, 610)))
            expected = []
            for row in group['rows']:
                left, right = by_id[row['main_id']], by_id[row['random_id']]
                probability = left['simulation']['metrics']['any_prize']['probability'] - right['simulation']['metrics']['any_prize']['probability']
                self.assertAlmostEqual(row['metrics']['portfolio.any_prize_probability@v1'], probability)
                expected.append(probability)
                self.assertEqual(len(row['metrics']['portfolio.number_frequencies@v1']), 50)
                self.assertEqual(sum(row['metrics']['portfolio.number_frequencies@v1']), 0)
            summary = group['summary']['portfolio.any_prize_probability@v1']
            self.assertAlmostEqual(summary['mean'], sum(expected) / 10)
            self.assertEqual(summary['min'], min(expected)); self.assertEqual(summary['max'], max(expected))
        self.assertTrue(result['full_domain']['pool_effect']['paired'])
        self.assertEqual(result['full_domain']['pool_effect']['orientation'], 'same_pool_random_minus_full_domain_random')
        self.assertTrue(any('covariance' in text for text in result['limitations']))
        self.assertEqual(json.dumps([main, controls], sort_keys=True), snapshot)
        self.assertEqual(json.loads(json.dumps(result)), result)

    def test_evolution_groups_are_descriptive_without_artificial_main_seed_pairing(self):
        main, controls = deepcopy(self.main[:6]), deepcopy(self.controls)
        for index, record in enumerate(main):
            record.pop('study_factor')
            record.update(is_starting_parent=index < 2, is_finalist=index in (2, 4))
            record['generation'].update(seed=700 + index, generation_index=0 if index < 2 else 1 if index < 4 else 2)
            record.pop('confirmation', None)
        attach_counter_fixture(main + controls, COMPARE, 'comparison')
        attach_counter_fixture([r for r in main if r['is_finalist']] + controls, CONFIRM, 'confirmation')
        result = benchmark(main, controls, 'evolution', require_full_domain=True,
                           expected_protocol=COMPARE, expected_confirmation_protocol=CONFIRM,
                           expected_generation_signature=GENERATION_SIGNATURE)
        self.assertFalse(result['same_pool']['paired'])
        self.assertEqual(result['same_pool']['paired_differences'], [])
        self.assertEqual([g['generation_index'] for g in result['same_pool']['main_groups']], [0, 1, 2])
        self.assertEqual([g['n'] for g in result['same_pool']['main_groups']], [2, 2, 2])


if __name__ == '__main__':
    unittest.main()
