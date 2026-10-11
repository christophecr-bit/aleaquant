"""Strict operational profiles and independent bounded conditional proofs."""
import copy
from decimal import Decimal
from itertools import combinations, product
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / 'configs' / 'portfolios' / 'milestone-v1.json'
sys.path.insert(0, str(ROOT / 'engine'))

from portfolio_contract import load_profiles, resolve_pool, schema_document, validate_grids, validate_profile  # noqa: E402
from portfolio_import import TOTAL, content_hash  # noqa: E402
from portfolio_proof import proof_for  # noqa: E402


def replace_at(document, path, value):
    cursor = document
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = value


def guarantee(numbers=5, stars=2, required_numbers=5, required_stars=2):
    return {'pool_good_numbers': numbers, 'pool_good_stars': stars,
            'condition_mode': 'exactly', 'required_numbers': required_numbers,
            'required_stars': required_stars, 'threshold_mode': 'at_least'}


class PortfolioContractProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registered = load_profiles(REGISTER)
        cls.random_base = next(p for p in cls.registered if p['id'] == 'random_complete_45_v1')

    def miniature(self, numbers=None, stars=None, count=1):
        config = copy.deepcopy(self.random_base)
        numbers = [1, 2, 3, 4, 5] if numbers is None else numbers
        stars = [1, 2] if stars is None else stars
        config['pool'].update(method='explicit', numbers=list(numbers), stars=list(stars),
                              number_count=len(numbers), star_count=len(stars))
        config['constraints'].update(grid_count=count, budget_max_eur=2.5 * count,
                                     conditional_guarantee=None)
        return config

    def test_registered_profiles_validate_without_changing_sources(self):
        before = REGISTER.read_bytes()
        for config in self.registered:
            with self.subTest(profile=config['id']):
                self.assertIsNone(validate_profile(config))
        self.assertEqual(REGISTER.read_bytes(), before)

    def invalid_profiles(self):
        values = [
            (('unexpected',), True), (('version',), True),
            (('schema_version',), '0.1'), (('family',), 'UNKNOWN'),
            (('game', 'options'), ['etoile_plus']), (('game', 'options'), None),
            (('game', 'rule_id'), 'euromillions-50-11-v1'),
            (('game', 'number_domain'), [50, 1]), (('game', 'star_domain'), [1, 11]),
            (('game', 'unit_price_eur'), 3.0), (('game', 'numbers_per_grid'), 4),
            (('pool', 'number_count'), True), (('pool', 'star_count'), 2.0),
            (('pool', 'seed'), '42'), (('pool', 'numbers'), [1, 1, 3, 4, 5]),
            (('constraints', 'grid_count'), True), (('constraints', 'grid_count'), 1.0),
            (('constraints', 'unique_grids'), False),
            (('constraints', 'max_pairwise_overlap', 'numbers'), 5.0),
            (('objectives', 'unknown_metric'), 1),
            (('objectives', 'balance_numbers'), float('nan')),
            (('search', 'method'), 'genetic'), (('search', 'population_size'), 2),
            (('search', 'operators'), ['mutation']),
            (('search', 'max_attempts'), 1000.0),
            (('search', 'max_seconds'), float('inf')),
            (('evaluation', 'draws'), True),
            (('evaluation', 'seed'), 10**1000),
            (('evaluation', 'metrics'), ['jackpot']),
            (('certificate',), {'fulfilled': True}),
            (('lineage',), {'inherited_certificate': 'old'}),
        ]
        cases = []
        for path, value in values:
            config = self.miniature()
            replace_at(config, path, value)
            cases.append((path, config))
        return cases

    def prototype(self):
        config = copy.deepcopy(next(p for p in self.registered if p['id'] == 'balanced_50_v1'))
        config['objectives']['minimize_overlap']['stars'] = 0
        config['search'].update(method='prototype_greedy', candidate_count=1,
                                candidates_per_step=1200, max_attempts=24000, max_seconds=60)
        return config

    def invalid_prototype_profiles(self):
        values = [(('objectives', 'concentration'), 1),
                  (('objectives', 'minimize_overlap', 'stars'), .1),
                  (('search', 'candidate_count'), 2),
                  (('search', 'candidates_per_step'), 1199),
                  (('search', 'max_attempts'), 23999),
                  (('search', 'max_seconds'), 61),
                  (('search', 'shared_core'), [1, 2, 3]),
                  (('search', 'seed'), self.prototype()['pool']['seed'])]
        cases = []
        for path, value in values:
            config = self.prototype()
            replace_at(config, path, value)
            cases.append((path, config))
        return cases

    def test_unknown_fields_unsupported_features_and_wrong_types_are_rejected(self):
        for path, config in self.invalid_profiles():
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    validate_profile(config)

    def test_rejections_remain_active_under_python_optimization(self):
        # JSON carries the test inputs; validation uses exceptions, never assert.
        cases = [config for _, config in self.invalid_profiles()
                 if math.isfinite(config['search']['max_seconds'])
                 and math.isfinite(config['objectives']['balance_numbers'])]
        cases.extend(config for _, config in self.invalid_prototype_profiles())
        script = '''import json, sys
sys.path.insert(0, 'engine')
from portfolio_contract import validate_profile
for index, profile in enumerate(json.load(sys.stdin)):
    try:
        validate_profile(profile)
    except ValueError:
        continue
    raise SystemExit('Invalid profile accepted: ' + str(index))
print('strict validation active')
'''
        result = subprocess.run([sys.executable, '-O', '-c', script],
                                input=json.dumps(cases), text=True, capture_output=True,
                                cwd=ROOT, check=True, timeout=15)
        self.assertEqual(result.stdout.strip(), 'strict validation active')

    def test_prototype_mode_is_explicit_and_unsupported_score_or_search_features_refused(self):
        self.assertIsNone(validate_profile(self.prototype()))
        for path, config in self.invalid_prototype_profiles():
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_profile(config)
        schema = json.loads((ROOT / 'engine/portfolio_profile_v1.schema.json').read_text())
        self.assertEqual(schema, schema_document())
        self.assertIn('prototype_greedy', schema['properties']['search']['properties']['method']['enum'])

    def test_17_50_budget_is_exact_and_used_cost_can_be_below_maximum(self):
        config = self.miniature(numbers=[1, 2, 3, 4, 5, 6], stars=[1, 2, 3], count=7)
        grids = [[list(main), list(stars)] for main, stars in
                 product(combinations(config['pool']['numbers'], 5),
                         combinations(config['pool']['stars'], 2))][:7]
        self.assertIsNone(validate_profile(config))
        self.assertEqual(validate_grids(grids, config), [])
        used = Decimal(len(grids)) * Decimal(str(config['game']['unit_price_eur']))
        self.assertEqual(used, Decimal('17.50'))
        config['constraints']['budget_max_eur'] = 20
        self.assertIsNone(validate_profile(config))
        self.assertEqual(validate_grids(grids, config), [])
        self.assertLess(used, Decimal(str(config['constraints']['budget_max_eur'])))
        for budget in (17.49, 17.501):
            config['constraints']['budget_max_eur'] = budget
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                validate_profile(config)

    def test_sampled_pools_have_explicit_seed_and_do_not_touch_global_rng(self):
        config = self.miniature()
        config['pool'].update(method='seeded_sample', numbers=[], stars=[],
                              number_count=9, star_count=4, seed=20261009)
        before, state = copy.deepcopy(config), random.getstate()
        self.assertIsNone(validate_profile(config))
        first = resolve_pool(config)
        self.assertEqual(first, resolve_pool(config))
        self.assertEqual([len(values) for values in first], [9, 4])
        self.assertTrue(set(first[0]) <= set(range(1, 51)))
        self.assertTrue(set(first[1]) <= set(range(1, 13)))
        self.assertEqual([len(set(values)) for values in first], [9, 4])
        self.assertEqual(config, before)
        self.assertEqual(random.getstate(), state)
        config['pool']['numbers'] = [1]
        with self.assertRaises(ValueError):
            validate_profile(config)

    def test_capacity_complete_enumeration_and_impossible_pairwise_caps(self):
        complete = copy.deepcopy(next(p for p in self.registered if p['id'] == 'complete_45_v1'))
        self.assertIsNone(validate_profile(complete))
        complete['constraints']['grid_count'] -= 1
        with self.assertRaises(ValueError):
            validate_profile(complete)
        insufficient = self.miniature(count=2)
        with self.assertRaises(ValueError):
            validate_profile(insufficient)
        impossible_main = self.miniature(numbers=[1, 2, 3, 4, 5, 6], stars=[1, 2, 3], count=2)
        impossible_main['constraints']['max_pairwise_overlap']['numbers'] = 3
        with self.assertRaises(ValueError):
            validate_profile(impossible_main)
        impossible_stars = self.miniature(numbers=list(range(1, 11)), stars=[1, 2, 3], count=2)
        impossible_stars['constraints']['max_pairwise_overlap']['stars'] = 0
        with self.assertRaises(ValueError):
            validate_profile(impossible_stars)

    def test_grid_validation_covers_domain_uniqueness_pool_and_size(self):
        config = self.miniature()
        good = [[[1, 2, 3, 4, 5], [1, 2]]]
        self.assertEqual(validate_grids(good, config), [])
        bad = [[], [[[1, 2, 3, 4, 6], [1, 2]]],
               [[[1, 2, 3, 4, True], [1, 2]]],
               [[[1, 2, 3, 4, 4], [1, 2]]],
               [[[1, 2, 3, 4, 5], [1, 1]]], good + copy.deepcopy(good)]
        for grids in bad:
            with self.subTest(grids=grids):
                self.assertTrue(validate_grids(grids, config))

    def test_singleton_exact_pool_guarantee_has_one_case_and_joint_5_plus_2(self):
        config = self.miniature()
        config['constraints']['conditional_guarantee'] = guarantee()
        self.assertIsNone(validate_profile(config))
        grids = [[[1, 2, 3, 4, 5], [1, 2]]]
        proof = proof_for(grids, config)
        self.assertEqual(proof['method'], 'exhaustive_enumeration')
        self.assertEqual(proof['verification'], 'independent_recalculation')
        self.assertEqual(proof['cases'], 1)
        self.assertEqual(proof['condition_probability'], 1 / TOTAL)
        self.assertEqual(proof['minimum_best_numbers_by_required_stars'], {'0': 5, '1': 5, '2': 5})
        self.assertTrue(proof['fulfilled'])
        self.assertEqual(proof['content_sha256'], content_hash(grids))

    def test_guarantee_requires_numbers_and_stars_on_the_same_grid(self):
        config = self.miniature(numbers=list(range(1, 11)), stars=[1, 2, 3, 4], count=2)
        config['constraints']['conditional_guarantee'] = guarantee()
        grids = [[[1, 2, 3, 4, 5], [3, 4]], [[6, 7, 8, 9, 10], [1, 2]]]
        self.assertIsNone(validate_profile(config))
        proof = proof_for(grids, config)
        # Draw 1..5 + stars 1,2 gives separate maxima of 5 and 2, never joint 5+2.
        draw = (set(range(1, 6)), {1, 2})
        hits = [(len(draw[0] & set(g[0])), len(draw[1] & set(g[1]))) for g in grids]
        self.assertEqual(hits, [(5, 0), (0, 2)])
        self.assertFalse(any(n >= 5 and s >= 2 for n, s in hits))
        self.assertFalse(proof['fulfilled'])
        self.assertLess(proof['minimum_best_numbers_by_required_stars']['2'], 5)

    def test_generic_proof_means_exactly_good_pool_values_including_outside_draws(self):
        config = self.miniature()
        config['constraints']['conditional_guarantee'] = guarantee(numbers=4, required_numbers=4)
        grids = [[[1, 2, 3, 4, 5], [1, 2]]]
        self.assertIsNone(validate_profile(config))
        proof = proof_for(grids, config)
        self.assertEqual(proof['cases'], 225)  # C(5,4) * C(45,1)
        self.assertEqual(proof['condition_probability'], 225 / TOTAL)
        self.assertEqual(proof['hypotheses']['condition_mode'], 'exactly')
        self.assertEqual(proof['minimum_best_numbers_by_required_stars']['2'], 4)
        self.assertTrue(proof['fulfilled'])
        config['constraints']['conditional_guarantee']['required_numbers'] = 5
        self.assertFalse(proof_for(grids, config)['fulfilled'])

    def test_proofs_bind_current_content_and_never_depend_on_monte_carlo(self):
        config = self.miniature(numbers=[1, 2, 3, 4, 5, 6])
        config['constraints']['conditional_guarantee'] = guarantee(required_numbers=4)
        first_grids = [[[1, 2, 3, 4, 5], [1, 2]]]
        next_grids = [[[1, 2, 3, 4, 6], [1, 2]]]
        first = proof_for(first_grids, config)
        second = proof_for(next_grids, config)
        self.assertNotEqual(first['content_sha256'], second['content_sha256'])
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(second['content_sha256'], content_hash(next_grids))
        changed_mc = copy.deepcopy(config)
        changed_mc['evaluation'].update(draws=1, seed=917)
        self.assertEqual(proof_for(first_grids, changed_mc), first)

    def test_requested_certificate_over_case_or_work_budget_is_refused(self):
        for good_numbers in (4, 5):
            config = self.miniature(numbers=list(range(1, 50)), stars=list(range(1, 13)))
            config['constraints']['conditional_guarantee'] = guarantee(numbers=good_numbers)
            with self.subTest(pool_good_numbers=good_numbers), self.assertRaises(ValueError):
                validate_profile(config)
        work_limited = self.miniature(numbers=list(range(1, 13)), stars=list(range(1, 7)), count=200)
        work_limited['constraints']['conditional_guarantee'] = guarantee(required_numbers=1, required_stars=0)
        self.assertEqual(math.comb(12, 5) * math.comb(6, 2), 11880)
        with self.assertRaises(ValueError):
            validate_profile(work_limited)
        tiny_limit = self.miniature(numbers=[1, 2, 3, 4, 5, 6])
        tiny_limit['constraints']['conditional_guarantee'] = guarantee(required_numbers=4)
        tiny_limit['evaluation']['max_certificate_cases'] = 1
        with self.assertRaises(ValueError):
            validate_profile(tiny_limit)

    def test_unconstrained_over_budget_proof_is_not_checked_without_fulfillment(self):
        config = self.miniature(numbers=list(range(1, 50)), stars=list(range(1, 13)))
        self.assertIsNone(validate_profile(config))
        proof = proof_for([[[1, 2, 3, 4, 5], [1, 2]]], config)
        self.assertEqual(proof['method'], 'not_checked')
        self.assertEqual(proof['reason'], 'certificate_budget_exceeded')
        self.assertIsNone(proof['requested'])
        self.assertIsNone(proof['fulfilled'])
        self.assertNotIn('minimum_best_numbers_by_required_stars', proof)

    def test_impossible_or_unsupported_guarantee_hypotheses_are_rejected(self):
        config = self.miniature(numbers=list(range(1, 50)), stars=list(range(1, 13)))
        config['constraints']['conditional_guarantee'] = guarantee(numbers=0)
        with self.assertRaises(ValueError):
            validate_profile(config)
        for field, value in (('condition_mode', 'at_least'), ('threshold_mode', 'exactly'),
                             ('required_stars', True), ('unknown', 1)):
            config = self.miniature()
            config['constraints']['conditional_guarantee'] = guarantee()
            config['constraints']['conditional_guarantee'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_profile(config)

    def test_generic_proof_rejects_a_grid_outside_its_declared_pool(self):
        config = self.miniature()
        config['constraints']['conditional_guarantee'] = guarantee(numbers=4, required_numbers=4)
        with self.assertRaises(ValueError):
            proof_for([[[1, 2, 3, 4, 6], [1, 2]]], config)


if __name__ == '__main__':
    unittest.main()
