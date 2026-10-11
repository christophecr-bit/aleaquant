"""Short deterministic generation and hard-constraint regression checks."""
import ast
import itertools
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))

from portfolio_contract import resolve_pool, validate_grids  # noqa: E402
from portfolio_import import content_hash  # noqa: E402
from portfolio_search import generate_candidates, portfolio_score  # noqa: E402


def profile(family='RANDOM', method='random', count=4, candidates=2,
            numbers=None, stars=None):
    numbers = list(range(1, 16)) if numbers is None else numbers
    stars = list(range(1, 7)) if stars is None else stars
    weights = {'distinct_pairs': 0, 'distinct_triples': 0,
               'balance_numbers': 0, 'balance_stars': 0, 'concentration': 0,
               'minimize_overlap': {'aggregation': 'sum_squares', 'numbers': 0, 'stars': 0}}
    if family == 'BALANCED':
        weights.update(balance_numbers=1, balance_stars=1)
    elif family == 'LOW_OVERLAP':
        weights['minimize_overlap'].update(numbers=1, stars=1)
    elif family == 'COVERAGE':
        weights.update(distinct_pairs=3, distinct_triples=8)
    elif family == 'CONCENTRATED':
        weights['concentration'] = 1
    if method == 'enumerate':
        weights = {'distinct_pairs': 0, 'distinct_triples': 0,
                   'balance_numbers': 0, 'balance_stars': 0, 'concentration': 0,
                   'minimize_overlap': {'aggregation': 'sum_squares', 'numbers': 0, 'stars': 0}}
    return {
        'id': 'test_' + family.lower(), 'version': 1, 'schema_version': '1.0',
        'family': family,
        'game': {'id': 'euromillions', 'rule_id': 'euromillions-50-12-v1',
                 'number_domain': [1, 50], 'star_domain': [1, 12],
                 'numbers_per_grid': 5, 'stars_per_grid': 2,
                 'unit_price_eur': 2.5, 'options': []},
        'pool': {'method': 'explicit', 'numbers': list(numbers), 'stars': list(stars),
                 'number_count': len(numbers), 'star_count': len(stars), 'seed': 101},
        'constraints': {'grid_count': count, 'budget_max_eur': 2.5 * count,
                        'unique_grids': True,
                        'max_pairwise_overlap': {'numbers': 5, 'stars': 2},
                        'conditional_guarantee': None},
        'objectives': weights,
        'search': {'method': method, 'seed': 42, 'candidate_count': candidates,
                   'candidates_per_step': 24, 'max_attempts': 1500,
                   'max_seconds': 10, 'population_size': 1, 'operators': []},
        'evaluation': {'method': 'monte_carlo', 'draws': 20000, 'seed': 991,
                       'batch_size': 2000, 'max_seconds': 30, 'max_certificate_cases': 100000,
                       'metrics': ['any_prize', 'multiple_prizes',
                                   'at_least_3_numbers', 'at_least_4_numbers']},
    }


def prototype_profile(count=4, numbers=None, stars=None, overlap=.7, seed=42):
    stars = [1, 2, 3, 4, 5] if stars is None else stars
    config = profile('BALANCED', 'prototype_greedy', count=count, candidates=1,
                     numbers=numbers, stars=stars)
    config['objectives'].update(distinct_triples=8, distinct_pairs=3,
                                balance_numbers=.9, balance_stars=.8)
    config['objectives']['minimize_overlap'].update(numbers=overlap, stars=0)
    config['search'].update(seed=seed, candidates_per_step=1200,
                            max_attempts=count * 1200, max_seconds=60)
    return config


def prototype_oracle(config):
    """Run only the archived pure construction function, never its module body.

The AST excludes argument parsing, file writes, certificates and the 500k-draw
loop. Inputs fix one small bounded construction with explicit pools and seed.
    """
    source = ROOT / 'prototypes/portfolio-pipeline/source-20261009/build.py'
    tree = ast.parse(source.read_text())
    construction = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'add')
    numbers, stars = resolve_pool(config)
    namespace = {'it': itertools, 'math': __import__('math'), 'random': random,
                 'base': numbers, 'stars': stars, 'profiles': [],
                 'cfg': {'pool_seed': config['pool']['seed']}}
    exec(compile(ast.Module(body=[construction], type_ignores=[]), str(source), 'exec'), namespace)
    weights = config['objectives']
    specification = {
        'id': 'bounded_oracle', 'family': 'Balanced',
        'constraints': {'grid_count': config['constraints']['grid_count'],
                        'budget_max_eur': config['constraints']['budget_max_eur'],
                        'pool_number_count': len(numbers), 'pool_star_count': len(stars),
                        'unique_grids': True},
        'objectives': {'maximize_distinct_triples': weights['distinct_triples'],
                       'maximize_distinct_pairs': weights['distinct_pairs'],
                       'balance_number_frequency': weights['balance_numbers'],
                       'balance_star_frequency': weights['balance_stars'],
                       'minimize_overlap': weights['minimize_overlap']['numbers']},
        'search': {'seed': config['search']['seed'], 'candidates_per_step': 1200},
    }
    namespace['add'](specification)
    return [[grid['numbers'], grid['stars']] for grid in namespace['profiles'][0]['grids']]


class PortfolioSearchTests(unittest.TestCase):
    def test_five_intentions_are_deterministic_and_keep_source_and_global_rng(self):
        for family in ('RANDOM', 'BALANCED', 'LOW_OVERLAP', 'COVERAGE', 'CONCENTRATED'):
            with self.subTest(family=family):
                config = profile(family, 'random' if family == 'RANDOM' else 'greedy')
                before = json.dumps(config, sort_keys=True)
                random_state = random.getstate()
                result = generate_candidates(config)
                self.assertEqual(result, generate_candidates(config))
                self.assertEqual(result['status'], 'complete')
                self.assertIsNone(result['stopped_reason'])
                self.assertEqual(len(result['candidates']), 2)
                self.assertEqual(json.dumps(config, sort_keys=True), before)
                self.assertEqual(random.getstate(), random_state)
                for index, candidate in enumerate(result['candidates']):
                    self.assertEqual(candidate['candidate_index'], index)
                    self.assertEqual(candidate['method'], config['search']['method'])
                    self.assertEqual(validate_grids(candidate['grids'], config), [])
                    self.assertAlmostEqual(candidate['score'], portfolio_score(candidate['grids'], config))

    def test_number_and_star_overlap_caps_hold_for_every_returned_pair(self):
        config = profile('LOW_OVERLAP', 'greedy', count=3)
        config['constraints']['max_pairwise_overlap'] = {'numbers': 3, 'stars': 0}
        result = generate_candidates(config)
        self.assertEqual(result['status'], 'complete')
        for candidate in result['candidates']:
            grids = candidate['grids']
            self.assertEqual(validate_grids(grids, config), [])
            for index, left in enumerate(grids):
                for right in grids[index + 1:]:
                    self.assertLessEqual(len(set(left[0]) & set(right[0])), 3)
                    self.assertEqual(set(left[1]) & set(right[1]), set())

    def test_search_exhaustion_does_not_export_a_prefix_as_a_candidate(self):
        # Three disjoint star pairs cannot fit a four-star pool, although each
        # individual grid and each allowed pair fits the declared domains.
        config = profile('LOW_OVERLAP', 'greedy', count=3, stars=[1, 2, 3, 4])
        config['constraints']['max_pairwise_overlap']['stars'] = 0
        config['search']['max_attempts'] = 120
        result = generate_candidates(config)
        self.assertEqual(result['status'], 'search_exhausted')
        self.assertEqual(result['stopped_reason'], 'max_attempts')
        self.assertEqual(result['candidates'], [])
        self.assertGreater(result['rejections']['hard_constraints'], 0)

    def test_seeded_pool_is_deterministic_and_reserved_seeds_are_skipped(self):
        config = profile(count=1)
        config['pool'].update(method='seeded_sample', numbers=[], stars=[], seed=44)
        config['evaluation']['seed'] = 43
        result = generate_candidates(config)
        self.assertEqual(result, generate_candidates(config))
        self.assertEqual(result['status'], 'complete')
        self.assertEqual([candidate['seed'] for candidate in result['candidates']], [42, 45])
        for candidate in result['candidates']:
            self.assertEqual(validate_grids(candidate['grids'], config), [])

    def test_exhausted_32_bit_seed_space_is_reported_explicitly(self):
        config = profile(count=1)
        config['search']['seed'] = 2**32 - 3
        # Force repeated portfolio identities to reach the seed boundary without
        # relying on a lucky sequence of duplicate random samples.
        with patch('portfolio_search.content_hash', return_value='same_portfolio'):
            result = generate_candidates(config)
        self.assertEqual(result['status'], 'search_exhausted')
        self.assertEqual(result['stopped_reason'], 'seed_space_exhausted')
        self.assertEqual(len(result['candidates']), 1)

    def test_exact_objective_score_has_independent_small_example(self):
        config = profile(count=2, numbers=list(range(1, 9)), stars=[1, 2, 3, 4])
        config['objectives'] = {
            'distinct_pairs': 3, 'distinct_triples': 7,
            'balance_numbers': 11, 'balance_stars': 13, 'concentration': 17,
            'minimize_overlap': {'aggregation': 'sum_squares', 'numbers': 19, 'stars': 23},
        }
        grids = [[[1, 2, 3, 4, 5], [1, 2]], [[4, 5, 6, 7, 8], [2, 3]]]
        # 19 pairs, 20 triples; pool dispersions 1.5 and 2; overlaps² 4 and 1.
        self.assertEqual(portfolio_score(grids, config), 123.5)
        self.assertEqual(portfolio_score(list(reversed(grids)), config), 123.5)
        config['objectives'] = profile('CONCENTRATED')['objectives']
        self.assertEqual(portfolio_score(grids, config), 4)
        config['objectives'] = profile('LOW_OVERLAP')['objectives']
        self.assertEqual(portfolio_score(grids, config), -5)

    def test_portfolio_hashes_are_unique_despite_duplicate_trials(self):
        config = profile(count=1, candidates=3, numbers=[1, 2, 3, 4, 5], stars=[1, 2, 3])
        result = generate_candidates(config)
        self.assertEqual(result['status'], 'complete')
        hashes = [content_hash(candidate['grids']) for candidate in result['candidates']]
        self.assertEqual(len(set(hashes)), 3)
        self.assertGreater(result['rejections']['duplicate_portfolio'], 0)

    def test_random_complete_small_pool_retries_duplicates_with_one_proposal_setting(self):
        config = profile('RANDOM', 'random', count=18, candidates=1,
                         numbers=[1, 2, 3, 4, 5, 6], stars=[1, 2, 3])
        config['search']['candidates_per_step'] = 1
        result = generate_candidates(config)
        self.assertEqual(result, generate_candidates(config))
        self.assertEqual(result['status'], 'complete')
        candidate = result['candidates'][0]
        self.assertEqual(candidate['method'], 'random')
        self.assertEqual(validate_grids(candidate['grids'], config), [])
        self.assertEqual(len({_grid_key(grid) for grid in candidate['grids']}), 18)
        self.assertGreater(result['rejections']['duplicate_proposal'], 0)
        self.assertLess(result['attempts'], 250)

    def test_random_keeps_a_stalled_prefix_bounded_by_global_attempts(self):
        # Two star pairs can fill a four-star pool; a third disjoint pair cannot.
        config = profile('RANDOM', 'random', count=3, stars=[1, 2, 3, 4])
        config['constraints']['max_pairwise_overlap']['stars'] = 0
        config['search'].update(candidates_per_step=1, max_attempts=120)
        updates = []
        result = generate_candidates(config, updates.append)
        self.assertEqual(result['status'], 'search_exhausted')
        self.assertEqual(result['stopped_reason'], 'max_attempts')
        self.assertEqual(result['attempts'], 120)
        self.assertEqual(result['candidates'], [])
        self.assertEqual([update['accepted_grids'] for update in updates], [1, 2])
        self.assertGreater(result['rejections']['hard_constraints'], 0)

    def test_complete_enumeration_returns_its_only_portfolio_with_finite_reason(self):
        config = profile('COVERAGE', 'enumerate', count=18, candidates=2,
                         numbers=[1, 2, 3, 4, 5, 6], stars=[1, 2, 3])
        result = generate_candidates(config)
        self.assertEqual(result['status'], 'search_exhausted')
        self.assertEqual(result['stopped_reason'], 'finite_space_exhausted')
        self.assertEqual(result['attempts'], 18)
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(validate_grids(result['candidates'][0]['grids'], config), [])
        self.assertEqual(len({_grid_key(grid) for grid in result['candidates'][0]['grids']}), 18)
        config['search']['candidate_count'] = 1
        self.assertEqual(generate_candidates(config)['status'], 'complete')

    def test_unknown_method_and_partial_enumeration_are_rejected(self):
        config = profile()
        config['search']['method'] = 'unknown'
        with self.assertRaises(ValueError):
            generate_candidates(config)
        config = profile('COVERAGE', 'enumerate', count=2,
                         numbers=[1, 2, 3, 4, 5, 6], stars=[1, 2])
        with self.assertRaises(ValueError):
            generate_candidates(config)

    def test_max_attempts_discards_incomplete_portfolios(self):
        for method in ('random', 'greedy'):
            with self.subTest(method=method):
                config = profile('RANDOM' if method == 'random' else 'BALANCED', method=method)
                config['search']['max_attempts'] = 1
                result = generate_candidates(config)
                self.assertEqual(result['status'], 'search_exhausted')
                self.assertEqual(result['stopped_reason'], 'max_attempts')
                self.assertEqual(result['attempts'], 1)
                self.assertEqual(result['candidates'], [])

    def test_deadline_reports_exhaustion_without_sleep_or_sampling(self):
        config = profile()
        clock = iter((0, 11))
        with patch('portfolio_search.time.monotonic', side_effect=lambda: next(clock, 11)):
            result = generate_candidates(config)
        self.assertEqual(result['status'], 'search_exhausted')
        self.assertEqual(result['stopped_reason'], 'max_seconds')
        self.assertEqual(result['attempts'], 0)
        self.assertEqual(result['candidates'], [])

    def test_progress_does_not_change_selection_or_reveal_partial_candidates(self):
        config = profile('BALANCED', 'greedy')
        expected = generate_candidates(config)
        updates = []
        result = generate_candidates(config, updates.append)
        self.assertEqual(result, expected)
        self.assertEqual(updates[-1]['phase'], 'candidate')
        self.assertEqual(updates[-1]['candidates'], 2)
        self.assertEqual(updates[-1]['accepted_grids'], config['constraints']['grid_count'])
        self.assertNotIn('grids', updates[-1])

    def test_prototype_mode_matches_independent_archived_constructor(self):
        for weight in (0, .35, .7, 1.4):
            with self.subTest(overlap_weight=weight):
                config = prototype_profile(overlap=weight)
                expected = prototype_oracle(config)
                result = generate_candidates(config)
                self.assertEqual(result['status'], 'complete')
                self.assertEqual(result['attempts'], 4 * 1200)
                candidate = result['candidates'][0]
                self.assertEqual(candidate['method'], 'prototype_greedy')
                self.assertEqual(candidate['seed'], config['search']['seed'])
                self.assertEqual(candidate['grids'], expected)
                self.assertEqual(validate_grids(candidate['grids'], config), [])

    def test_prototype_mode_reproduces_original_balanced_50_content(self):
        archive = json.loads((ROOT / 'prototypes/portfolio-pipeline/source-20261009/results.json').read_text())
        original = next(p for p in archive['profiles'] if p['id'] == 'balanced_50')
        config = prototype_profile(count=20, numbers=original['pool_numbers'],
                                   stars=original['pool_stars'], seed=1035)
        result = generate_candidates(config)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['attempts'], 24000)
        expected = [[grid['numbers'], grid['stars']] for grid in original['grids']]
        self.assertEqual(result['candidates'][0]['grids'], expected)

    def test_prototype_step_frequency_cost_is_not_a_variance_penalty(self):
        config = prototype_profile(count=2, numbers=list(range(1, 9)), stars=[1, 2, 3, 4])
        config['objectives'].update(distinct_pairs=0, distinct_triples=0)
        grids = [[[1, 2, 3, 4, 5], [1, 2]], [[4, 5, 6, 7, 8], [2, 3]]]
        # Current frequencies cost .9*2 + .8*1, intersections cost .7*2².
        self.assertAlmostEqual(portfolio_score(grids, config), -5.4)
        config['search']['method'] = 'greedy'
        self.assertAlmostEqual(portfolio_score(grids, config), -5.75)

    def test_prototype_retains_first_maximum_and_samples_full_window(self):
        config = prototype_profile(count=1)
        config['objectives'] = profile()['objectives']
        rng = random.Random(config['search']['seed'])
        numbers, stars = resolve_pool(config)
        first = [sorted(rng.sample(numbers, 5)), sorted(rng.sample(stars, 2))]
        result = generate_candidates(config)
        self.assertEqual(result['attempts'], 1200)
        self.assertEqual(result['candidates'][0]['grids'], [first])

    def test_prototype_deadline_does_not_publish_a_truncated_proposal_window(self):
        config = prototype_profile(count=1)
        clock = itertools.count()
        with patch('portfolio_search.time.monotonic', side_effect=lambda: next(clock)):
            result = generate_candidates(config)
        self.assertEqual(result['status'], 'search_exhausted')
        self.assertEqual(result['stopped_reason'], 'max_seconds')
        self.assertGreater(result['attempts'], 0)
        self.assertLess(result['attempts'], 1200)
        self.assertEqual(result['candidates'], [])


def _grid_key(grid):
    return tuple(grid[0]), tuple(grid[1])


if __name__ == '__main__':
    unittest.main()
