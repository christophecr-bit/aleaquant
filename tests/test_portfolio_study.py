"""Small real paired studies; no production export or 40-construction run."""
from contextlib import redirect_stdout
import copy
from hashlib import sha256
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
REGISTERED = ROOT / 'configs/studies/minimize-overlap-20x15x5-v1.json'
sys.path.insert(0, str(ROOT / 'engine'))

import portfolio_pipeline as pipeline  # noqa: E402
import portfolio_study as runner  # noqa: E402
from portfolio_contract import validate_grids  # noqa: E402
from portfolio_import import content_hash, digest  # noqa: E402
from portfolio_study_analysis import analyze_study  # noqa: E402
from portfolio_study_contract import load_study, study_id, template_profiles, validate_study  # noqa: E402


def miniature_study(grid_count=3):
    study = json.loads(REGISTERED.read_text())
    study.update(id='small_overlap_study', title='Petite étude appariée',
                 question='Effet géométrique de deux poids sur deux graines communes ?')
    profile = study['base_profile']
    profile['pool'].update(method='explicit', numbers=list(range(1, 10)), stars=[1, 2, 3, 4],
                           number_count=9, star_count=4, seed=91)
    profile['constraints'].update(grid_count=grid_count, budget_max_eur=2.5 * grid_count,
                                  conditional_guarantee=None)
    profile['search'].update(seed=601, candidate_count=1, candidates_per_step=1200,
                             max_attempts=1200 * grid_count, max_seconds=5)
    profile['evaluation'].update(draws=65, seed=901, batch_size=16,
                                 max_seconds=5, max_certificate_cases=1000)
    study['vary']['values'] = [0, 1.4]
    study['generation'].update(seeds=[601, 602], repetitions=2)
    study['bounds'].update(max_constructions=4, max_run_seconds=5)
    study['confirmation']['max_finalists'] = 2
    study['confirmation']['evaluation'] = copy.deepcopy(profile['evaluation'])
    study['confirmation']['evaluation']['seed'] = 902
    study['references'] = []
    return study


def replace_at(document, path, value):
    cursor = document
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = value


class PortfolioStudyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.site = self.directory / 'site'
        (self.site / 'dist/data').mkdir(parents=True)
        (self.site / 'dist/metrics.json').write_bytes((ROOT / 'dist/metrics.json').read_bytes())
        # The initializer reads the reference catalogue, but this study includes
        # no references and cannot pass any imported counters to its evaluator.
        pipeline.write(self.site / 'dist/data/portfolio_pipeline.json',
                       {'profiles': [], 'source': {'archive_sha256': 'a' * 64}})
        self.study = miniature_study()
        validate_study(self.study)
        self.config = self.directory / 'study.json'
        self.config.write_text(json.dumps(self.study))
        self.run_dir = self.directory / 'run-a'
        self.output = self.site / 'dist/data/portfolio_study.json'
        for module in (pipeline, runner):
            root_patch = patch.object(module, 'ROOT', self.site)
            root_patch.start()
            self.addCleanup(root_patch.stop)

    def run_study(self, run_dir=None, study=None, **options):
        with redirect_stdout(io.StringIO()):
            return runner.run(study or self.study, run_dir or self.run_dir,
                              output=self.output, **options)

    def assert_no_publication(self):
        self.assertFalse(self.output.exists())
        self.assertFalse((self.site / 'dist/data/portfolio_studies.json').exists())
        self.assertFalse((self.site / 'dist/data/portfolio_study_runs').exists())

    def test_registered_study_and_cli_validation_describe_the_plan_without_running_it(self):
        registered = load_study(REGISTERED)
        self.assertEqual(registered['vary']['values'], [0, .35, .7, 1.4])
        self.assertEqual(len(registered['generation']['seeds']), 10)
        self.assertEqual(registered['base_profile']['constraints']['grid_count'], 20)
        self.assertEqual([registered['base_profile']['pool'][key]
                          for key in ('number_count', 'star_count')], [15, 5])
        for path, constructions in ((REGISTERED, 40), (self.config, 4)):
            with self.subTest(config=path):
                result = subprocess.run([sys.executable, str(ROOT / 'engine/portfolio_study.py'),
                                         'validate', '--study-config', str(path)],
                                        capture_output=True, text=True, check=True, timeout=15)
                event = json.loads(result.stdout.strip())
                self.assertEqual(event['status'], 'valid')
                self.assertEqual(event['constructions'], constructions)
        self.assertFalse(self.run_dir.exists())
        self.assert_no_publication()

    def test_strict_contract_rejects_unknown_axis_budget_seeds_shapes_and_bounds(self):
        invalid = [
            (('unknown',), True), (('version',), True),
            (('vary', 'parameter'), 'objectives.minimize_overlap.stars'),
            (('vary', 'values'), [1.4, 0]), (('vary', 'values'), [0, 0]),
            (('vary', 'values'), [.35, .7]), (('vary', 'values'), [False, 1.4]),
            (('generation', 'seeds'), [601, 601]),
            (('generation', 'seeds'), [601, True]),
            (('generation', 'repetitions'), 3),
            (('bounds', 'max_constructions'), 3),
            (('bounds', 'max_run_seconds'), 0),
            (('bounds', 'max_run_seconds'), 601),
            (('base_profile', 'constraints', 'budget_max_eur'), 7.49),
            (('base_profile', 'pool', 'method'), 'seeded_sample'),
            (('base_profile', 'search', 'method'), 'greedy'),
            (('base_profile', 'search', 'candidate_count'), 2),
            (('base_profile', 'evaluation', 'seed'), 602),
            (('confirmation', 'evaluation', 'seed'), 901),
            (('confirmation', 'evaluation', 'seed'), 602),
            (('confirmation', 'evaluation', 'seed'), 91),
            (('confirmation', 'max_finalists'), 1),
            (('confirmation', 'selection'), 'monte_carlo_ranking'),
            (('comparison', 'method'), 'different_pools'),
            (('comparison', 'metrics'), ['unknown_metric']),
            (('comparison', 'metrics'), ['portfolio.distinct_pairs@v1'] * 4),
        ]
        for path, value in invalid:
            study = copy.deepcopy(self.study)
            replace_at(study, path, value)
            with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                validate_study(study)
        duplicate_reference = {'id': 'same', 'content_sha256': 'a' * 64}
        study = copy.deepcopy(self.study)
        study['references'] = [duplicate_reference, copy.deepcopy(duplicate_reference)]
        with self.assertRaises(ValueError):
            validate_study(study)
        # A six-cell rectangle exceeds the declared four-construction budget.
        study = copy.deepcopy(self.study)
        study['vary']['values'] = [0, .7, 1.4]
        study['confirmation']['max_finalists'] = 3
        with self.assertRaises(ValueError):
            validate_study(study)

    def test_declared_batch_work_is_bounded_for_both_mc_roles(self):
        for role in ('comparison', 'confirmation'):
            study = copy.deepcopy(self.study)
            study['base_profile']['constraints'].update(grid_count=200, budget_max_eur=500)
            study['base_profile']['search']['max_attempts'] = 240000
            if role == 'comparison':
                study['base_profile']['evaluation']['batch_size'] = 10000
            else:
                study['confirmation']['evaluation']['batch_size'] = 10000
            with self.subTest(role=role), self.assertRaises(ValueError):
                validate_study(study)

    def test_cli_rejects_invalid_study_under_python_optimization(self):
        bad = copy.deepcopy(self.study)
        bad['vary']['parameter'] = 'simulation.any_prize'
        self.config.write_text(json.dumps(bad))
        result = subprocess.run([sys.executable, '-O', str(ROOT / 'engine/portfolio_study.py'),
                                 'validate', '--study-config', str(self.config)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Étude refusée', result.stderr)
        self.assert_no_publication()

    def test_real_study_resumes_construction_and_each_mc_role_before_publication(self):
        interrupted = self.run_study(stop_after_constructions=2)
        self.assertEqual(interrupted['status'], 'generating')
        self.assertEqual(interrupted['completed_constructions'], 2)
        partial = pipeline.read_signed(self.run_dir / 'generation-checkpoint.json')
        original_records = copy.deepcopy(partial['records'])
        self.assertEqual(len(original_records), 2)
        self.assert_no_publication()

        interrupted = self.run_study(stop_after_comparison_batches=1)
        self.assertEqual(interrupted['status'], 'comparison_interrupted')
        self.assertEqual(interrupted['completed_draws'], 16)
        generation = pipeline.read_signed(self.run_dir / 'generation.json')
        self.assertEqual(generation['records'][:2], original_records)
        self.assertEqual(len(generation['records']), 4)
        self.assertFalse((self.run_dir / 'latest-evaluation.json').exists())
        self.assert_no_publication()

        interrupted = self.run_study(stop_after_confirmation_batches=1)
        self.assertEqual(interrupted['status'], 'confirmation_interrupted')
        self.assertEqual(interrupted['completed_draws'], 16)
        comparison_pointer = pipeline.read(self.run_dir / 'latest-evaluation.json')
        comparison = pipeline.read_signed(self.run_dir / comparison_pointer['path'])
        self.assertEqual(comparison['completed_draws'], 65)
        self.assertEqual(comparison['protocol']['seed'], 901)
        confirmation_dir = next((self.run_dir / 'evaluations').glob('confirmation-*'))
        confirmation_checkpoint = pipeline.read(confirmation_dir / 'checkpoint.json')
        self.assertEqual(confirmation_checkpoint['payload']['completed_draws'], 16)
        self.assertFalse((confirmation_dir / 'confirmation.json').exists())
        self.assert_no_publication()
        with redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
            runner.projection(self.study, self.run_dir, pipeline.read_signed(self.run_dir / 'study-run.json'))

        complete = self.run_study()
        self.assertEqual(complete['status'], 'complete')
        dataset = pipeline.read(self.output)
        self.assertEqual(dataset['origin'], 'local_study')
        self.assertEqual(dataset['analysis']['record_count'], 4)
        self.assertEqual(dataset['study']['repetitions'], 2)
        self.assertEqual(dataset['study_definition'], self.study)
        self.assertEqual(dataset['study_run']['inputs']['references'], [])
        self.assertEqual({(p['study_factor']['weight'], p['study_factor']['seed'])
                          for p in dataset['profiles']}, {(w, s) for w in (0, 1.4) for s in (601, 602)})
        for record in dataset['profiles']:
            self.assertEqual(record['grid_count'], 3)
            self.assertEqual(record['generation']['method'], 'prototype_greedy')
            self.assertEqual(record['generation']['seed'], record['study_factor']['seed'])
            self.assertEqual(validate_grids(record['grids'], record['constraint_profile']), [])
            self.assertEqual(record['content_sha256'], content_hash(record['grids']))
            self.assertEqual(record['config_sha256'], digest(record['profile_object']))
            self.assertEqual(record['certificate']['content_sha256'], record['content_sha256'])
        self.assert_roles_and_graph(dataset)

    def assert_roles_and_graph(self, dataset):
        finalists = set(dataset['analysis']['finalist_ids'])
        self.assertTrue(finalists)
        self.assertLessEqual(len(finalists), 2)
        self.assertLess(len(finalists), len(dataset['profiles']))
        comparison_streams, confirmation_streams = set(), set()
        for record in dataset['profiles']:
            evaluation = record['evaluation']
            self.assertEqual(evaluation['role'], 'comparison')
            self.assertEqual(evaluation['seed'], 901)
            self.assertEqual(record['simulation']['draws'], 65)
            self.assertEqual(record['simulation']['seed'], 901)
            comparison_streams.add(evaluation['draw_stream_sha256'])
            self.assertEqual(record['is_finalist'], record['id'] in finalists)
            if record['is_finalist']:
                confirmation = record['confirmation']
                self.assertEqual(confirmation['evaluation']['role'], 'confirmation')
                self.assertTrue(confirmation['evaluation']['independent_of_comparison'])
                self.assertEqual(confirmation['simulation']['draws'], 65)
                self.assertEqual(confirmation['simulation']['seed'], 902)
                confirmation_streams.add(confirmation['evaluation']['draw_stream_sha256'])
            else:
                self.assertNotIn('confirmation', record)
        self.assertEqual(len(comparison_streams), 1)
        self.assertEqual(len(confirmation_streams), 1)
        self.assertFalse(comparison_streams & confirmation_streams)
        self.assertEqual(dataset['analysis']['confirmation']['status'], 'complete')
        self.assertEqual(dataset['analysis']['finalist_selection']['selection_basis'], 'exact_geometry_only')
        graph = dataset['graph']
        pipeline.validate_graph(graph)
        nodes = graph['nodes']
        self.assertEqual(sum(n['type'] == 'profile' for n in nodes), 2)
        self.assertEqual(sum(n['type'] == 'generation_run' for n in nodes), 4)
        self.assertEqual(sum(n['type'] == 'study' for n in nodes), 1)
        self.assertEqual(sum(n['type'] == 'study_run' for n in nodes), 1)
        self.assertFalse(any(n['type'] == 'reference' for n in nodes))
        self.assertEqual(sum(e['type'] == 'uses_profile_version' for e in graph['edges']), 2)
        self.assertEqual(sum(e['type'] == 'generated_in_study' for e in graph['edges']), 4)
        self.assertTrue(any(e['type'] == 'confirmed_by' for e in graph['edges']))

    def test_analysis_refuses_a_nonrectangular_or_duplicated_construction_plan(self):
        with redirect_stdout(io.StringIO()):
            execution = runner.initialize(self.study, self.run_dir)
            generation = runner.generation(self.study, self.run_dir, execution)
        records = generation['records']
        self.assertEqual(len(records), 4)
        self.assertEqual(len(template_profiles(self.study)), 2)
        for bad in (records[:-1], records + [copy.deepcopy(records[0])]):
            with self.subTest(records=len(bad)), self.assertRaises(ValueError):
                analyze_study(bad, max_finalists=2)
        self.assert_no_publication()

    def test_two_executions_of_same_definition_get_distinct_ids_and_immutable_archives(self):
        study = miniature_study(grid_count=2)
        validate_study(study)
        first = self.run_study(study=study)
        self.assertEqual(first['status'], 'complete')
        first_dataset = pipeline.read(self.output)
        first_identity = pipeline.read_signed(self.run_dir / 'study-run.json')
        first_archive = self.site / 'dist/data/portfolio_study_runs' / first['run_id'].split(':')[1] / 'catalogue.json'
        first_bytes = first_archive.read_bytes()
        first_digest = sha256(first_bytes).hexdigest()
        second_dir = self.directory / 'run-b'
        second = self.run_study(run_dir=second_dir, study=study)
        second_identity = pipeline.read_signed(second_dir / 'study-run.json')
        self.assertEqual(first_identity['study_id'], study_id(study))
        self.assertEqual(first_identity['study_id'], second_identity['study_id'])
        self.assertNotEqual(first_identity['id'], second_identity['id'])
        self.assertNotEqual(first['run_id'], second['run_id'])
        self.assertEqual(first_bytes, first_archive.read_bytes())
        self.assertEqual(sha256(first_archive.read_bytes()).hexdigest(), first_digest)
        index = pipeline.read(self.site / 'dist/data/portfolio_studies.json')
        self.assertEqual(len(index['studies']), 2)
        second_dataset = pipeline.read(self.output)
        self.assertEqual([(p['study_factor'], p['content_sha256']) for p in first_dataset['profiles']],
                         [(p['study_factor'], p['content_sha256']) for p in second_dataset['profiles']])
        # Repeating a completed execution preserves its identity and immutable bytes.
        self.assertEqual(self.run_study(study=study)['run_id'], first['run_id'])
        self.assertEqual(first_archive.read_bytes(), first_bytes)
        with self.assertRaises(ValueError):
            pipeline.write(first_archive, {'tampered': True}, immutable=True)
        self.assertEqual(first_archive.read_bytes(), first_bytes)

    def test_modified_definition_and_tampered_checkpoint_refuse_resume(self):
        self.run_study(stop_after_constructions=2)
        changed = copy.deepcopy(self.study)
        changed['question'] += ' Nouvelle définition.'
        with self.assertRaises(ValueError):
            self.run_study(study=changed)
        checkpoint = self.run_dir / 'generation-checkpoint.json'
        payload = pipeline.read(checkpoint)
        payload['payload']['records'][0]['grids'][0][0][0] = 50
        checkpoint.write_text(json.dumps(payload))
        altered = checkpoint.read_bytes()
        with self.assertRaises(ValueError):
            self.run_study()
        self.assertEqual(checkpoint.read_bytes(), altered)
        self.assert_no_publication()

    def test_small_run_uses_the_cli_entry_point_with_temporary_publication_root(self):
        with redirect_stdout(io.StringIO()):
            code = runner.main(['run', '--study-config', str(self.config),
                                '--run-dir', str(self.run_dir), '--output', str(self.output)])
        self.assertEqual(code, 0)
        self.assertEqual(pipeline.read(self.output)['origin'], 'local_study')
        self.assertEqual(len(pipeline.read(self.output)['profiles']), 4)


if __name__ == '__main__':
    unittest.main()
