"""Étude appariée miniature : géométrie exacte et MC descriptif seulement."""
import copy
import json
import math
from pathlib import Path
from statistics import pstdev
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))

from portfolio_evaluation import EVENTS, exact_analytics  # noqa: E402
from portfolio_import import content_hash  # noqa: E402
from portfolio_study_analysis import analyze_study  # noqa: E402

PAIRS = 'portfolio.distinct_pairs@v1'
TRIPLES = 'portfolio.distinct_triples@v1'
NUMBER_SD = 'portfolio.number_frequency_sd@v1'
MAX_OVERLAP = 'portfolio.max_number_overlap@v1'
STAR_PAIRS = 'portfolio.distinct_star_pairs@v1'
NUMBER_HIST = 'portfolio.number_overlap_distribution@v1'
STAR_HIST = 'portfolio.star_overlap_distribution@v1'
NUMBER_FREQ = 'portfolio.number_frequencies@v1'
STAR_FREQ = 'portfolio.star_frequencies@v1'
ANY = 'portfolio.any_prize_probability@v1'


def miniature_records():
    cells = [
        (0, 10, [[[1, 2, 3, 4, 5], [1, 2]], [[1, 2, 3, 4, 6], [1, 3]]]),
        (0, 20, [[[1, 2, 3, 4, 5], [1, 2]], [[1, 2, 6, 7, 8], [1, 3]]]),
        (1, 10, [[[1, 2, 3, 4, 5], [1, 2]], [[6, 7, 8, 9, 10], [3, 4]]]),
        (1, 20, [[[1, 2, 3, 4, 5], [1, 2]], [[6, 7, 8, 9, 10], [1, 2]]]),
    ]
    records = []
    for weight, seed, grids in cells:
        records.append({
            'id': f'w{weight}_s{seed}', 'grids': grids, 'content_sha256': content_hash(grids),
            'pool_numbers': list(range(1, 16)), 'pool_stars': list(range(1, 6)),
            'study_factor': {'weight': weight, 'seed': seed},
            'generation': {'seed': seed, 'pool_seed': 91, 'method': 'prototype_greedy',
                           'candidates_per_step': 1200},
            'constraint_profile': {'objectives': {
                'cover_pairs': 3, 'cover_triples': 8, 'balance_numbers': .9,
                'balance_stars': .8, 'concentration': 0,
                'minimize_overlap': {'numbers': weight, 'stars': 0}}},
        })
    return records


def simulation(record, seed=2810010, any_count=40, multiple_count=10):
    """Marginales cohérentes fabriquées, aucun tirage MC exécuté."""
    counts = dict(zip(EVENTS, (any_count, multiple_count, 5, 1)))
    analytics = exact_analytics(record['grids'])
    return {'seed': seed, 'draws': 100, 'content_sha256': record['content_sha256'],
            'same_draws_for_all': True, 'independent_of_generation': True,
            'mean_winning_grids': (any_count + multiple_count) / 100,
            'theoretical_mean_winning_grids': analytics['theoretical_mean_winning_grids'],
            'jackpot_probability': analytics['jackpot_probability'],
            'metrics': {event: {'count': count, 'probability': count / 100}
                        for event, count in counts.items()}}


def row_for(rows, key, value):
    return next(row for row in rows if row[key] == value)


class PortfolioStudyAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.records = miniature_records()

    def test_scalar_means_ranges_sd_and_paired_differences_use_all_seeds(self):
        report = analyze_study(self.records)
        self.assertEqual(report['repetitions'], 2)
        self.assertEqual(report['record_count'], 4)
        baseline = row_for(report['by_factor'], 'weight', 0)
        weighted = row_for(report['by_factor'], 'weight', 1)
        self.assertEqual(baseline['metrics'][PAIRS], {
            'n': 2, 'mean': 16.5, 'min': 14, 'max': 19, 'sd': 2.5,
            'sd_method': 'population_across_generation_seeds'})
        self.assertEqual(weighted['metrics'][PAIRS]['mean'], 20)
        self.assertEqual(weighted['metrics'][PAIRS]['sd'], 0)
        delta = row_for(report['paired_differences'], 'weight_b', 1)
        self.assertEqual(delta['metrics'][PAIRS]['mean'], 3.5)
        self.assertEqual(delta['metrics'][PAIRS]['sd'], 2.5)
        self.assertEqual(delta['metrics'][TRIPLES]['mean'], 2)
        self.assertEqual(delta['metrics'][TRIPLES]['min'], 0)
        self.assertEqual(delta['metrics'][TRIPLES]['max'], 4)
        self.assertEqual([r['metrics'][PAIRS] for r in delta['by_seed']], [6, 1])
        zero = row_for(report['paired_differences'], 'weight_b', 0)
        self.assertTrue(all(m['mean'] == 0 for m in zero['metrics'].values()))
        self.assertEqual(report['monte_carlo_descriptive']['status'], 'not_evaluated')

    def test_histograms_frequencies_pool_sd_and_zero_star_combinations(self):
        report = analyze_study(self.records)
        all_rows = report['geometry_by_record']
        cluster = all_rows['w0_s10']
        spread = all_rows['w1_s10']
        self.assertEqual(cluster['metrics'][NUMBER_HIST], [0, 0, 0, 0, 1, 0])
        self.assertEqual(cluster['metrics'][STAR_HIST], [0, 1, 0])
        self.assertEqual(spread['metrics'][NUMBER_HIST], [1, 0, 0, 0, 0, 0])
        self.assertEqual(spread['metrics'][STAR_HIST], [1, 0, 0])
        self.assertEqual(spread['metrics'][NUMBER_FREQ], [1] * 10 + [0] * 40)
        self.assertEqual(spread['metrics'][STAR_FREQ], [1] * 4 + [0] * 8)
        self.assertEqual(spread['metrics'][NUMBER_SD], pstdev([1] * 10 + [0] * 40))
        self.assertEqual(spread['pool_frequency_sd']['numbers'], pstdev([1] * 10 + [0] * 5))
        self.assertNotEqual(spread['metrics'][NUMBER_SD], spread['pool_frequency_sd']['numbers'])
        self.assertEqual(spread['pool_frequencies']['numbers']['counts'], [1] * 10 + [0] * 5)
        self.assertEqual(sum(spread['pool_frequencies']['stars']['counts']), 4)
        combos = spread['star_combinations']
        self.assertEqual((combos['covered'], combos['pool_possible'], combos['domain_possible']), (2, 10, 66))
        self.assertEqual(len(combos['counts']), 10)
        self.assertEqual(sum(r['count'] for r in combos['counts']), 2)
        self.assertEqual(next(r for r in combos['counts'] if r['stars'] == [4, 5])['count'], 0)
        self.assertEqual(spread['coverage_denominators']['pairs'], {'pool': 105, 'domain': 1225})
        self.assertEqual(spread['coverage_denominators']['triples'], {'pool': 455, 'domain': 19600})
        weighted = row_for(report['by_factor'], 'weight', 1)
        self.assertEqual(weighted['vectors'][NUMBER_HIST][0]['mean'], 1)
        self.assertEqual(weighted['star_combinations']['counts'][0]['mean'], 1.5)
        delta = row_for(report['paired_differences'], 'weight_b', 1)
        self.assertEqual(delta['vectors'][NUMBER_HIST][0]['mean'], 1)
        self.assertEqual(delta['metrics'][STAR_PAIRS]['mean'], -.5)

    def test_geometric_finalists_preserve_global_front_and_weight_quota(self):
        full = analyze_study(self.records)
        self.assertEqual(len(full['finalist_ids']), 3)
        self.assertIn('w0_s20', full['finalist_ids'])
        selection = full['finalist_selection']
        self.assertEqual(selection['reasons']['w0_s20'], 'weight_quota_within_weight_front')
        self.assertEqual(set(selection['global_pareto_ids']), {'w1_s10', 'w1_s20'})
        self.assertTrue(selection['global_front_fully_selected'])
        self.assertEqual(selection['covered_weights'], [0, 1])
        self.assertEqual(selection['selection_basis'], 'exact_geometry_only')
        capped = analyze_study(self.records, max_finalists=2)
        self.assertEqual(len(capped['finalist_ids']), 2)
        self.assertFalse(capped['finalist_selection']['global_front_fully_selected'])
        self.assertEqual(set(capped['finalist_selection']['global_pareto_ids']), {'w1_s10', 'w1_s20'})
        self.assertEqual(len(selection['criteria']), 4)
        self.assertNotIn(STAR_PAIRS, [c['metric_id'] for c in selection['criteria']])

    def test_selection_is_order_invariant_and_recomputes_geometry(self):
        expected = analyze_study(self.records)
        changed = copy.deepcopy(list(reversed(self.records)))
        for record in changed:
            record['metric_values'] = {PAIRS: -1, TRIPLES: -1, NUMBER_SD: -1, MAX_OVERLAP: -1}
            record['geometry'] = {'distinct_pairs': -1}
            record['grids'].reverse()
            for grid in record['grids']:
                grid[0].reverse()
                grid[1].reverse()
        actual = analyze_study(changed)
        self.assertEqual(actual, expected)

    def test_output_is_unchanged_by_json_round_trip(self):
        for record in self.records:
            record['simulation'] = simulation(record)
        report = analyze_study(self.records)
        selected = [r for r in self.records if r['id'] in report['finalist_ids']]
        confirmation = {r['content_sha256']: simulation(r, seed=2910010) for r in selected}
        analysis = analyze_study(self.records, confirmation=confirmation)
        self.assertEqual(analysis['controls']['method_and_candidates_per_step'],
                         ['prototype_greedy', 1200])
        self.assertEqual(json.loads(json.dumps(analysis)), analysis)

    def test_alias_contents_are_deduplicated_and_still_represent_each_weight(self):
        for i in (2, 3):
            self.records[i]['grids'] = copy.deepcopy(self.records[i - 2]['grids'])
            self.records[i]['content_sha256'] = content_hash(self.records[i]['grids'])
        report = analyze_study(self.records)
        selected = report['finalist_selection']
        self.assertEqual(len(selected['content_sha256']), len(set(selected['content_sha256'])))
        self.assertEqual(selected['covered_weights'], [0, 1])
        self.assertEqual(len(selected['ids']), 1)
        self.assertTrue(selected['global_front_fully_selected'])

    def test_synthesis_reports_stability_and_degradation_across_seeds(self):
        report = analyze_study(self.records)
        effects = report['paired_effects'][0]['metrics']
        self.assertEqual(effects[PAIRS]['favorable_seeds'], 2)
        self.assertEqual(effects[TRIPLES]['unchanged_seeds'], 1)
        self.assertEqual(effects[STAR_PAIRS]['classification'], 'degraded')
        self.assertEqual(effects[STAR_PAIRS]['unfavorable_seeds'], 1)
        self.assertIn('dégradée', ' '.join(report['synthesis']))
        self.assertIn('2 graines appariées', report['synthesis'][0])
        jackpots = [r['metrics']['portfolio.jackpot_probability@v1']
                    for r in report['geometry_by_record'].values()]
        self.assertEqual(len(set(jackpots)), 1)
        self.assertAlmostEqual(jackpots[0], 2 / (math.comb(50, 5) * math.comb(12, 2)))

    def test_mc_aggregates_are_descriptive_and_never_change_finalists(self):
        exact = analyze_study(self.records)
        for i, record in enumerate(self.records):
            record['simulation'] = simulation(record, any_count=40 + i * 10)
        report = analyze_study(self.records)
        self.assertEqual(report['finalist_selection'], exact['finalist_selection'])
        mc = report['monte_carlo_descriptive']
        self.assertEqual(mc['inference'], 'descriptive_only_no_paired_draw_covariance')
        self.assertIn('Marginal Wilson', mc['warning'])
        self.assertAlmostEqual(row_for(mc['by_factor'], 'weight', 0)['metrics'][ANY]['mean'], .45)
        self.assertAlmostEqual(row_for(mc['paired_differences'], 'weight_b', 1)['metrics'][ANY]['mean'], .2)
        self.assertNotIn('ci95', row_for(mc['paired_differences'], 'weight_b', 1)['metrics'][ANY])
        self.assertIn('portfolio.mean_winning_grids@v1', mc['by_factor'][0]['metrics'])
        self.assertIn('portfolio.at_least_3_numbers_probability@v1', mc['by_factor'][0]['metrics'])
        self.assertIn('portfolio.at_least_4_numbers_probability@v1', mc['by_factor'][0]['metrics'])

    def test_common_draw_and_protocol_identities_are_preserved_and_checked(self):
        for record in self.records:
            record['simulation'] = simulation(record)
            record['simulation'].update(protocol_sha256='a' * 64, draw_stream_sha256='b' * 64,
                                        source_sha256='c' * 64)
        report = analyze_study(self.records)
        self.assertEqual(report['monte_carlo_descriptive']['draw_stream_sha256'], 'b' * 64)
        for key in ('protocol_sha256', 'draw_stream_sha256', 'source_sha256'):
            records = copy.deepcopy(self.records)
            records[0]['simulation'][key] = 'd' * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                analyze_study(records)
        records = copy.deepcopy(self.records)
        records[0]['simulation'].pop('draw_stream_sha256')
        with self.assertRaises(ValueError):
            analyze_study(records)

    def test_confirmation_is_bound_to_selected_content_and_a_new_seed(self):
        for record in self.records:
            record['simulation'] = simulation(record)
        report = analyze_study(self.records)
        selected = [r for r in self.records if r['id'] in report['finalist_ids']]
        confirmation = {r['content_sha256']: simulation(r, seed=2910010) for r in selected}
        result = analyze_study(self.records, confirmation=confirmation)
        self.assertEqual(result['confirmation']['seed'], 2910010)
        self.assertEqual(set(result['confirmation']['by_record_id']), set(report['finalist_ids']))
        self.assertEqual(result['confirmation']['inference'], 'descriptive_only')
        for bad_seed in (2810010, 10, 91):
            bad = copy.deepcopy(confirmation)
            for row in bad.values():
                row['seed'] = bad_seed
            with self.subTest(seed=bad_seed), self.assertRaises(ValueError):
                analyze_study(self.records, confirmation=bad)
        bad = dict(confirmation)
        bad.pop(next(iter(bad)))
        with self.assertRaises(ValueError):
            analyze_study(self.records, confirmation=bad)
        bad = dict(confirmation)
        bad['f' * 64] = simulation(self.records[0], seed=2910010)
        with self.assertRaises(ValueError):
            analyze_study(self.records, confirmation=bad)

    def test_mc_rejects_partial_mismatched_dependent_or_impossible_marginals(self):
        variations = [
            lambda r: r.pop('simulation'),
            lambda r: r['simulation'].update(seed=10),
            lambda r: r['simulation'].update(draws=200),
            lambda r: r['simulation'].update(content_sha256='0' * 64),
            lambda r: r['simulation'].pop('content_sha256'),
            lambda r: r['simulation'].update(independent_of_generation=False),
            lambda r: r['simulation'].update(same_draws_for_all=False),
            lambda r: r['simulation'].update(mean_winning_grids=.9),
            lambda r: r['simulation']['metrics']['any_prize'].update(probability=.41),
            lambda r: r['simulation']['metrics']['at_least_4_numbers'].update(count=6, probability=.06),
            lambda r: r['simulation']['metrics'].update(any_prize=None),
        ]
        for mutate in variations:
            records = copy.deepcopy(self.records)
            for record in records:
                record['simulation'] = simulation(record)
            mutate(records[0])
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                analyze_study(records)
        for record in self.records:
            record['simulation'] = simulation(record, seed=91)
        with self.assertRaises(ValueError):
            analyze_study(self.records)

    def test_identical_contents_on_common_draws_must_have_identical_marginals(self):
        self.records[2]['grids'] = copy.deepcopy(self.records[0]['grids'])
        self.records[2]['content_sha256'] = content_hash(self.records[2]['grids'])
        for record in self.records:
            record['simulation'] = simulation(record)
        self.records[2]['simulation'] = simulation(self.records[2], any_count=50)
        with self.assertRaisesRegex(ValueError, 'mêmes grilles'):
            analyze_study(self.records)

    def test_nonrectangular_or_confounded_plan_is_rejected(self):
        variations = [
            lambda rows: rows[0]['study_factor'].update(seed=30),
            lambda rows: rows[0].update(id=rows[1]['id']),
            lambda rows: rows[0]['generation'].update(seed=99),
            lambda rows: rows[0]['pool_numbers'].append(16),
            lambda rows: rows[0]['constraint_profile']['objectives']['minimize_overlap'].update(numbers=.3),
            lambda rows: rows[0]['constraint_profile']['objectives'].update(balance_stars=.7),
            lambda rows: rows[0]['generation'].update(candidates_per_step=100),
            lambda rows: rows[0].pop('constraint_profile'),
        ]
        for mutate in variations:
            records = copy.deepcopy(self.records)
            mutate(records)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                analyze_study(records)
        with self.assertRaises(ValueError):
            analyze_study(self.records, max_finalists=1)
        with self.assertRaises(ValueError):
            analyze_study(self.records, max_finalists=13)

    def test_invalid_geometry_factor_and_hash_are_rejected(self):
        variations = [
            lambda r: r['study_factor'].update(weight=True),
            lambda r: r['study_factor'].update(weight=float('nan')),
            lambda r: r['study_factor'].update(seed=True),
            lambda r: r.update(content_sha256='a' * 64),
            lambda r: r['grids'][0][0].__setitem__(0, 16),
            lambda r: r['grids'][0][1].__setitem__(0, 6),
            lambda r: r['grids'].__setitem__(1, copy.deepcopy(r['grids'][0])),
            lambda r: r['pool_numbers'].append(1),
            lambda r: r.pop('grids'),
            lambda r: r.update(generation=None),
            lambda r: r.update(constraint_profile={'objectives': None}),
        ]
        for mutate in variations:
            records = copy.deepcopy(self.records)
            mutate(records[0])
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                analyze_study(records)


if __name__ == '__main__':
    unittest.main()
