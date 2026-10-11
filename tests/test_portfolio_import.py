"""Import borné du prototype : contrats, preuves conjointes et provenance.

Les fixtures sont lues comme données. Aucun script de l'archive n'est exécuté,
et aucun tirage Monte-Carlo n'est rejoué dans cette suite.
"""

import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'prototypes' / 'portfolio-pipeline' / 'source-20261009'
METRICS = ROOT / 'dist' / 'metrics.json'
sys.path.insert(0, str(ROOT / 'engine'))

from portfolio_import import (  # noqa: E402
    certify, content_hash, import_archive, validate_config,
)
from portfolio_geometry import portfolio_geometry  # noqa: E402


def replace_at(document, path, value):
    cursor = document
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value


def monte_carlo_event(count, draws):
    """Make a coherent individual event to test relations between events."""
    z = 1.95996398454
    p = count / draws
    denominator = 1 + z ** 2 / draws
    midpoint = (p + z ** 2 / (2 * draws)) / denominator
    radius = z * math.sqrt(p * (1 - p) / draws + z ** 2 / (4 * draws ** 2)) / denominator
    return {'count': count, 'probability': p,
            'ci95_wilson': [midpoint - radius, midpoint + radius]}


class PortfolioImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temporary = tempfile.TemporaryDirectory()
        cls.directory = Path(cls._temporary.name)
        cls.config = json.loads((SOURCE / 'profiles.json').read_text())
        cls.results = json.loads((SOURCE / 'results.json').read_text())
        cls.atlas = json.loads((SOURCE / 'atlas.json').read_text())
        cls.archive = cls.directory / 'original.zip'
        cls._write_archive(cls.archive)
        cls.dataset = import_archive(cls.archive, METRICS)

    @classmethod
    def tearDownClass(cls):
        cls._temporary.cleanup()

    @classmethod
    def _write_archive(cls, path, mutation=None):
        documents = {
            'profiles.json': copy.deepcopy(cls.config),
            'results.json': copy.deepcopy(cls.results),
            'atlas.json': copy.deepcopy(cls.atlas),
        }
        # Preserve agreement between the three archive views when mutating
        # a business value, rather than only testing a stale duplicated view.
        documents['results.json']['config'] = documents['profiles.json']
        for node, profile in zip(documents['atlas.json']['nodes'],
                                 documents['results.json']['profiles']):
            node['data'] = profile
        if mutation:
            mutation(documents)
        with zipfile.ZipFile(path, 'w') as archive:
            for source in sorted(SOURCE.iterdir()):
                if source.name == 'archive.sha256' or not source.is_file():
                    continue
                data = (json.dumps(documents[source.name], ensure_ascii=False).encode()
                        if source.name in documents else source.read_bytes())
                archive.writestr(source.name, data)
        return path

    def assert_archive_rejected(self, mutation):
        path = self.directory / 'mutated.zip'
        self._write_archive(path, mutation)
        with self.assertRaises(ValueError):
            import_archive(path, METRICS)

    def test_config_accepts_the_versioned_fixture(self):
        self.assertIsNone(validate_config(copy.deepcopy(self.config)))

    def test_config_rejects_unsupported_fields_versions_and_types(self):
        bad_values = [
            (('schema_version',), '99'),
            (('game',), 'loto'),
            (('unit_price_eur',), 2.6),
            (('pool_seed',), True),
            (('evaluation', 'draws'), True),
            (('evaluation', 'draws'), 500000.0),
            (('evaluation', 'draws'), 0),
            (('evaluation', 'seed'), True),
            (('profiles', 0, 'family'), 'Other'),
            (('profiles', 0, 'constraints', 'grid_count'), True),
            (('profiles', 0, 'constraints', 'grid_count'), 18.0),
            (('profiles', 0, 'constraints', 'grid_count'), 0),
            (('profiles', 0, 'constraints', 'pool_number_count'), True),
            (('profiles', 0, 'constraints', 'pool_number_count'), 4),
            (('profiles', 0, 'constraints', 'pool_star_count'), 13),
            (('profiles', 0, 'constraints', 'unique_grids'), False),
            (('profiles', 0, 'constraints', 'budget_max_eur'), 44.9),
            (('profiles', 0, 'constraints', 'budget_max_eur'), float('inf')),
            (('profiles', 0, 'constraints', 'budget_max_eur'), 10 ** 1000),
            (('profiles', 0, 'objectives', 'minimize_overlap'), float('nan')),
            (('profiles', 0, 'objectives', 'minimize_overlap'), 10 ** 1000),
            (('profiles', 0, 'objectives', 'minimize_overlap'), True),
            (('profiles', 0, 'search', 'candidates_per_step'), 0),
            (('profiles', 0, 'search', 'candidates_per_step'), 1.5),
            (('profiles', 0, 'search', 'seed'), False),
            (('unknown_parameter',), 1),
            (('profiles', 0, 'constraints', 'pool_numbers'), [1, 2, 3, 4, 5]),
            (('profiles', 0, 'constraints', 'max_pairwise_overlap'), 1),
            (('profiles', 0, 'objectives', 'new_objective'), 1),
            (('profiles', 0, 'search', 'checkpoint_every'), 10),
        ]
        for path, value in bad_values:
            with self.subTest(path=path, value=value):
                config = copy.deepcopy(self.config)
                replace_at(config, path, value)
                with self.assertRaises(ValueError):
                    validate_config(config)

    def test_config_rejects_duplicate_ids_and_combination_impossibilities(self):
        duplicate = copy.deepcopy(self.config)
        duplicate['profiles'][1]['id'] = duplicate['profiles'][0]['id']
        with self.assertRaises(ValueError):
            validate_config(duplicate)

        for family, pool_numbers, pool_stars, count in [
            ('Balanced', 5, 2, 2),     # only one distinct 5+2 grid exists
            ('Complete', 6, 3, 17),    # complete means exactly 18 grids
            ('Clustered', 10, 4, 127), # shared core leaves C(7,2)*C(4,2)
        ]:
            with self.subTest(family=family):
                config = copy.deepcopy(self.config)
                spec = config['profiles'][0]
                spec['family'] = family
                spec['constraints'].update(grid_count=count,
                                           pool_number_count=pool_numbers,
                                           pool_star_count=pool_stars,
                                           budget_max_eur=count * 2.5)
                with self.assertRaises(ValueError):
                    validate_config(config)

    def test_hash_is_invariant_to_grid_number_and_star_order(self):
        grids = [
            [[1, 2, 3, 4, 5], [1, 2]],
            [[6, 7, 8, 9, 10], [3, 4]],
        ]
        reordered = [[list(reversed(numbers)), list(reversed(stars))]
                     for numbers, stars in reversed(grids)]
        digest = content_hash(grids)
        self.assertRegex(digest, r'^[0-9a-f]{64}$')
        self.assertEqual(digest, content_hash(reordered))
        changed = copy.deepcopy(grids)
        changed[0][1] = [1, 3]
        self.assertNotEqual(digest, content_hash(changed))

    def test_certification_requires_hits_on_the_same_grid(self):
        # For draw numbers 1..5 and stars 1,2, the first grid has 5+0;
        # the second has 0+2. Combining two separate maxima invents 5+2.
        grids = [
            [[1, 2, 3, 4, 5], [3, 4]],
            [[6, 7, 8, 9, 10], [1, 2]],
        ]
        certificate = certify(grids, list(range(1, 11)), [1, 2, 3, 4])
        self.assertEqual(certificate['method'], 'exhaustive_enumeration')
        self.assertEqual(certificate['cases'], 1512)
        self.assertEqual(certificate['minimum_best_numbers_by_required_stars'],
                         {'0': 3, '1': 0, '2': -1})

    def test_certification_counts_an_exactly_matched_singleton(self):
        certificate = certify([[[1, 2, 3, 4, 5], [1, 2]]],
                              [1, 2, 3, 4, 5], [1, 2])
        self.assertEqual(certificate['cases'], 1)
        self.assertEqual(certificate['minimum_best_numbers_by_required_stars'],
                         {'0': 5, '1': 5, '2': 5})
        self.assertAlmostEqual(certificate['condition_probability'],
                               1 / (math.comb(50, 5) * math.comb(12, 2)))

    def test_singleton_geometry_does_not_invent_pairwise_overlap(self):
        geometry = portfolio_geometry([[[1, 2, 3, 4, 5], [1, 2]]], 50)
        self.assertIsNone(geometry['overlap_mean'])
        self.assertIsNone(geometry['overlap_max'])
        self.assertIsNone(geometry['second']['overlap_mean'])
        self.assertIsNone(geometry['second']['overlap_max'])
        self.assertEqual(geometry['coverage'][2]['covered'], 10)
        self.assertEqual(geometry['coverage'][3]['covered'], 10)

    def test_certificate_limits_are_checked_before_enumerating(self):
        with self.assertRaises(ValueError):
            certify([[[1, 2, 3, 4, 5], [1, 2]]],
                    list(range(1, 51)), list(range(1, 13)), max_cases=10)
        with self.assertRaises(ValueError):
            import_archive(self.archive, METRICS, max_certificate_cases=10)

    def test_certificate_rejects_invalid_direct_inputs(self):
        valid = [[[1, 2, 3, 4, 5], [1, 2]]]
        for grids, numbers, stars, max_cases in [
            ([], [1, 2, 3, 4, 5], [1, 2], 100),
            (valid, [1, 2, 3, 4, 4], [1, 2], 100),
            (valid, [1, 2, 3, 4, 5], [1, 1], 100),
            (valid, [1, 2, 3, 4], [1, 2], 100),
            (valid, [1, 2, 3, 4, 5], [1, 2], True),
            (valid, [1, 2, 3, 4, 5], [1, 2], 0),
            ([[[1, 2, 3, 4, 6], [1, 2]]], [1, 2, 3, 4, 5], [1, 2], 100),
            ([[[1, 2, 3, 4, True], [1, 2]]], [1, 2, 3, 4, 5], [1, 2], 100),
            (valid + [[[5, 4, 3, 2, 1], [2, 1]]], [1, 2, 3, 4, 5], [1, 2], 100),
        ]:
            with self.subTest(grids=grids, numbers=numbers, stars=stars, max_cases=max_cases):
                with self.assertRaises(ValueError):
                    certify(grids, numbers, stars, max_cases=max_cases)

    def test_archive_has_118_grids_and_four_recalculated_certificates(self):
        profiles = self.dataset['profiles']
        self.assertEqual(len(profiles), 6)
        self.assertEqual(sum(len(p['grids']) for p in profiles), 118)
        expected = {p['id']: p for p in self.results['profiles']}
        certificates = 0
        for profile in profiles:
            with self.subTest(profile=profile['id']):
                original = expected[profile['id']]
                canonical = sorted([[sorted(g['numbers']), sorted(g['stars'])]
                                    for g in original['grids']])
                self.assertEqual(profile['grids'], canonical)
                self.assertEqual(profile['exact'], original['exact'])
                self.assertEqual(profile['simulation'], original['simulation'])
                self.assertEqual(profile['content_sha256'], content_hash(canonical))
                self.assertEqual(profile['evaluation']['content_sha256'],
                                 profile['content_sha256'])
                certificate = profile['certificate']
                if original['certificate']['method'] == 'exhaustive_enumeration':
                    certificates += 1
                    self.assertEqual(certificate['minimum_best_numbers_by_required_stars'],
                                     original['certificate']['minimum_best_numbers_by_required_stars'])
                    self.assertEqual(certificate['cases'], original['certificate']['cases'])
                    self.assertEqual(certificate['verification'], 'independent_recalculation')
                    self.assertEqual(certificate['content_sha256'], profile['content_sha256'])
                else:
                    self.assertEqual(certificate['method'], 'not_checked')
                self.assertFalse(profile['evaluation']['replayed'])
        self.assertEqual(certificates, 4)
        self.assertEqual(self.dataset['metric_source']['definitions_count'],
                         len(json.loads(METRICS.read_text())))

    def test_comparison_cohorts_preserve_budget_and_do_not_invent_random_reference(self):
        cohorts = {cohort['budget_eur']: cohort for cohort in self.dataset['cohorts']}
        self.assertEqual(set(cohorts), {45.0, 50.0, 55.0})
        expected = {
            45.0: {'complete_45', 'balanced_45'},
            50.0: {'balanced_50', 'spread_50', 'clustered_50'},
            55.0: {'spread_55'},
        }
        for budget, ids in expected.items():
            self.assertEqual(set(cohorts[budget]['profile_ids']), ids)
            self.assertFalse(cohorts[budget]['random_reference_available'])
        graph = self.dataset['graph']
        self.assertEqual(len(graph['nodes']), 18)
        self.assertEqual(len(graph['edges']), 12)
        node_ids = {node['id'] for node in graph['nodes']}
        for edge in graph['edges']:
            self.assertIn(edge['source'], node_ids)
            self.assertIn(edge['target'], node_ids)

    def test_cli_check_verifies_without_writing_output(self):
        output = self.directory / 'must-not-be-written.json'
        process = subprocess.run(
            [sys.executable, str(ROOT / 'engine' / 'portfolio_import.py'),
             '--archive', str(self.archive), '--metrics', str(METRICS),
             '--output', str(output), '--check'],
            cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertFalse(output.exists())

    def test_cli_exports_the_same_dataset_reproducibly(self):
        outputs = []
        for index in range(2):
            output = self.directory / f'export-{index}.json'
            process = subprocess.run(
                [sys.executable, str(ROOT / 'engine' / 'portfolio_import.py'),
                 '--archive', str(self.archive), '--metrics', str(METRICS),
                 '--output', str(output)],
                cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertFalse(output.with_suffix('.json.tmp').exists())
            self.assertEqual(json.loads(output.read_text()),
                             json.loads(json.dumps(self.dataset)))
            outputs.append(output.read_bytes())
        self.assertEqual(outputs[0], outputs[1])

    def test_archive_rejects_invalid_grids_duplicates_costs_and_exact_metrics(self):
        changes = [
            (('profiles', 0, 'grids', 0, 'numbers', 0), 0),
            (('profiles', 0, 'grids', 0, 'numbers', 0), True),
            (('profiles', 0, 'grids', 0, 'stars', 0), 13),
            (('profiles', 0, 'budget_eur'), 2.5),
            (('profiles', 0, 'exact', 'distinct_pairs'), 99),
            (('profiles', 0, 'certificate', 'cases'), 99),
            (('profiles', 0, 'certificate',
              'minimum_best_numbers_by_required_stars', '2'), 4),
        ]
        for path, value in changes:
            with self.subTest(path=path):
                self.assert_archive_rejected(
                    lambda documents, p=path, v=value:
                    replace_at(documents['results.json'], p, v))

        def duplicate(documents):
            grids = documents['results.json']['profiles'][0]['grids']
            grids[1] = copy.deepcopy(grids[0])
        self.assert_archive_rejected(duplicate)

    def test_archive_rejects_monte_carlo_count_probability_and_interval_corruption(self):
        for field, value in [('count', -1), ('count', True),
                             ('count', 500001), ('probability', 0.9),
                             ('ci95_wilson', [0.99, 0.01]),
                             ('ci95_wilson', [float('nan'), 0.5])]:
            with self.subTest(field=field, value=value):
                self.assert_archive_rejected(
                    lambda documents, f=field, v=value:
                    documents['results.json']['profiles'][0]['simulation']
                    ['metrics']['any_prize'].__setitem__(f, v))

    def test_archive_rejects_impossible_mean_count_of_winning_grids(self):
        simulation = self.results['profiles'][0]['simulation']
        any_prize = simulation['metrics']['any_prize']['probability']
        # Each winning draw has one win, and multiple-prize draws have at
        # least one additional win. Conversely a draw has at most m wins.
        for mean in [any_prize, 18 * any_prize + 0.1,
                     simulation['mean_winning_grids'] + 0.5 / simulation['draws']]:
            with self.subTest(mean=mean):
                self.assert_archive_rejected(
                    lambda documents, value=mean:
                    documents['results.json']['profiles'][0]['simulation']
                    .__setitem__('mean_winning_grids', value))

        def exceed_upper_bound(documents):
            profile = documents['results.json']['profiles'][3]
            sim = profile['simulation']
            any_p = sim['metrics']['any_prize']['probability']
            multiple_p = sim['metrics']['multiple_prizes']['probability']
            sim['mean_winning_grids'] = any_p + (len(profile['grids']) - 1) * multiple_p + 0.1
        self.assert_archive_rejected(exceed_upper_bound)

    def test_archive_rejects_coherent_but_impossible_nested_event_counts(self):
        for inner, outer in [('multiple_prizes', 'any_prize'),
                             ('at_least_4_numbers', 'at_least_3_numbers'),
                             ('at_least_3_numbers', 'any_prize')]:
            with self.subTest(inner=inner, outer=outer):
                def change(documents):
                    sim = documents['results.json']['profiles'][0]['simulation']
                    sim['metrics'][inner] = monte_carlo_event(
                        sim['metrics'][outer]['count'] + 1, sim['draws'])
                self.assert_archive_rejected(change)

    def test_cli_validation_still_rejects_invalid_input_under_python_optimization(self):
        path = self.directory / 'invalid-for-optimized-cli.zip'
        self._write_archive(path, lambda documents:
                            replace_at(documents['profiles.json'],
                                       ('profiles', 0, 'constraints', 'grid_count'), True))
        process = subprocess.run(
            [sys.executable, '-O', str(ROOT / 'engine' / 'portfolio_import.py'),
             '--archive', str(path), '--metrics', str(METRICS), '--check'],
            cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertNotEqual(process.returncode, 0)


if __name__ == '__main__':
    unittest.main()
