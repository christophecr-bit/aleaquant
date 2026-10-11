"""Jalon opérationnel complet sur de petits profils, sans données MC du ZIP."""
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))

import portfolio_pipeline as pipeline  # noqa: E402
from portfolio_import import content_hash, digest  # noqa: E402


def miniature_bundle():
    template = json.loads((ROOT / 'configs/portfolios/milestone-v1.json').read_text())['profiles'][0]
    profiles = []
    for identifier, family, method, seed, start, stars in [
        ('coverage_mini', 'COVERAGE', 'enumerate', 101, 1, [1, 2]),
        ('random_same', 'RANDOM', 'random', 201, 1, [1, 2]),
        ('random_other', 'RANDOM', 'random', 301, 11, [3, 4]),
    ]:
        profile = copy.deepcopy(template)
        profile.update(id=identifier, family=family)
        profile['pool'].update(method='explicit', numbers=list(range(start, start + 6)),
                               stars=stars, number_count=6, star_count=2, seed=91)
        profile['constraints'].update(grid_count=6, budget_max_eur=15,
                                      conditional_guarantee=None)
        profile['search'].update(method=method, seed=seed, candidate_count=1,
                                 candidates_per_step=64, max_attempts=1000, max_seconds=2)
        profile['evaluation'].update(draws=65, seed=901, batch_size=16,
                                     max_seconds=5, max_certificate_cases=100)
        profiles.append(profile)
    return {'schema_version': '1.0', 'profiles': profiles}


class PortfolioPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.site = self.directory / 'site'
        (self.site / 'dist').mkdir(parents=True)
        (self.site / 'dist/metrics.json').write_bytes((ROOT / 'dist/metrics.json').read_bytes())
        self.config = self.directory / 'profiles.json'
        self.bundle = miniature_bundle()
        self.config.write_text(json.dumps(self.bundle))
        self.run_dir = self.directory / 'run'
        self.root_patch = patch.object(pipeline, 'ROOT', self.site)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def generate(self):
        with redirect_stdout(io.StringIO()):
            return pipeline.generate(self.config, self.run_dir)

    def evaluate(self, **options):
        with redirect_stdout(io.StringIO()):
            return pipeline.evaluate(self.run_dir, **options)

    def test_generation_evaluation_and_projection_deduplicate_the_same_content(self):
        generation = self.generate()
        self.assertEqual(len(generation['records']), 3)
        self.assertEqual(len({p['content_sha256'] for p in generation['records']}), 2)
        self.assertIsNone(generation['inputs']['references_sha256'])
        self.assertTrue(all(p['origin'] == 'local_pipeline' for p in generation['records']))
        result = self.evaluate()
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['completed_draws'], 65)
        self.assertEqual(len(result['results']), 2)
        dataset = pipeline.project(self.run_dir)
        self.assertEqual(dataset['origin'], 'local_pipeline')
        self.assertEqual(dataset['contract_version'], '1.0')
        self.assertEqual(len(dataset['profiles']), 3)
        for profile in dataset['profiles']:
            with self.subTest(profile=profile['id']):
                self.assertEqual(profile['content_sha256'], content_hash(profile['grids']))
                self.assertEqual(profile['config_sha256'], digest(profile['constraint_profile']))
                self.assertEqual(profile['certificate']['content_sha256'], profile['content_sha256'])
                proof = copy.deepcopy(profile['certificate'])
                proof_id = proof.pop('id')
                self.assertEqual(proof_id, 'proof:' + digest(proof))
                self.assertEqual(profile['evaluation']['content_sha256'], profile['content_sha256'])
                self.assertTrue(profile['evaluation']['replayed'])
                self.assertFalse(profile['evaluation']['reproduces_archive'])
                self.assertEqual(profile['simulation']['draws'], 65)
                self.assertEqual(profile['simulation']['seed'], 901)
                self.assertEqual(profile['budget_actual_eur'], 15)
                self.assertTrue(profile['evaluation']['id'].startswith('evaluation:'))
                self.assertTrue(profile['generation_run']['id'].startswith('generation-candidate:'))
        aliases = [p for p in dataset['profiles'] if p['id'].startswith(('coverage_mini', 'random_same'))]
        self.assertEqual(aliases[0]['evaluation']['id'], aliases[1]['evaluation']['id'])
        self.assertEqual(aliases[0]['simulation'], aliases[1]['simulation'])
        nodes = dataset['graph']['nodes']
        self.assertEqual(sum(n['type'] == 'portfolio' for n in nodes), 2)
        self.assertEqual(sum(n['type'] == 'evaluation_run' for n in nodes), 2)
        self.assertEqual(sum(n['type'] == 'profile' for n in nodes), 3)
        pipeline.validate_graph(dataset['graph'])

    def test_two_comparison_protocols_include_random_at_the_same_budget(self):
        generation = self.generate()
        comparison = pipeline.comparisons(generation['records'])
        self.assertEqual(set(comparison), {'same_pool', 'different_pools'})
        self.assertEqual(len(comparison['same_pool']), 2)
        self.assertEqual(len(comparison['different_pools']), 1)
        for group in comparison['same_pool'] + comparison['different_pools']:
            self.assertEqual(group['budget_eur'], 15)
            self.assertEqual(group['grid_count'], 6)
            self.assertTrue(group['random_reference_available'])
            self.assertEqual(group['criteria'], pipeline.CRITERIA)
        all_pools = comparison['different_pools'][0]
        self.assertIsNone(all_pools['pool_id'])
        self.assertEqual(all_pools['distinct_content_count'], 2)
        self.assertEqual(len(all_pools['profile_ids']), 3)

    def test_monte_carlo_probability_does_not_rank_the_geometric_pareto_front(self):
        keys = [c['metric_id'] for c in pipeline.CRITERIA]
        superior = {'id': 'geometry', 'content_sha256': 'a' * 64,
                    'metric_values': dict(zip(keys, [30, 30, 1.0, 1]))}
        inferior = {'id': 'lucky_simulation', 'content_sha256': 'b' * 64,
                    'metric_values': dict(zip(keys, [20, 20, 2.0, 2]))}
        superior['metric_values']['portfolio.any_prize_probability@v1'] = 0.01
        inferior['metric_values']['portfolio.any_prize_probability@v1'] = 0.99
        self.assertEqual(pipeline.pareto_ids([superior, inferior]), ['geometry'])
        alias = copy.deepcopy(superior)
        alias['id'] = 'same_content_other_profile'
        self.assertEqual(set(pipeline.pareto_ids([superior, alias, inferior])),
                         {'geometry', 'same_content_other_profile'})
        tradeoff = copy.deepcopy(inferior)
        tradeoff['metric_values'][keys[1]] = 40
        self.assertEqual(set(pipeline.pareto_ids([superior, tradeoff])),
                         {'geometry', 'lucky_simulation'})

    def test_graph_rejects_cycles_missing_nodes_and_duplicate_ids(self):
        nodes = [{'id': 'a', 'type': 'profile'}, {'id': 'b', 'type': 'portfolio'}]
        for graph in [
            {'nodes': nodes, 'edges': [{'source': 'a', 'target': 'b'}, {'source': 'b', 'target': 'a'}]},
            {'nodes': nodes, 'edges': [{'source': 'a', 'target': 'missing'}]},
            {'nodes': nodes + nodes[:1], 'edges': []},
        ]:
            with self.subTest(graph=graph), self.assertRaises(ValueError):
                pipeline.validate_graph(graph)

    def test_immutable_writes_and_signed_payloads_refuse_tampering(self):
        path = self.directory / 'immutable.json'
        pipeline.write(path, {'version': 1}, immutable=True)
        before = path.read_bytes()
        pipeline.write(path, {'version': 1}, immutable=True)
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(ValueError):
            pipeline.write(path, {'version': 2}, immutable=True)
        self.assertEqual(path.read_bytes(), before)
        signed = self.directory / 'signed.json'
        pipeline.write(signed, pipeline.signed({'record': 1}))
        self.assertEqual(pipeline.read_signed(signed), {'record': 1})
        altered = pipeline.read(signed)
        altered['payload']['record'] = 2
        signed.write_text(json.dumps(altered))
        with self.assertRaises(ValueError):
            pipeline.read_signed(signed)

    def test_generation_resumes_after_the_last_completed_profile(self):
        original = pipeline.generate_candidates
        called = []
        def interrupt_second(profile):
            called.append(profile['id'])
            if len(called) == 2:
                raise RuntimeError('test interruption between profiles')
            return original(profile)
        with patch.object(pipeline, 'generate_candidates', side_effect=interrupt_second):
            with self.assertRaises(RuntimeError):
                self.generate()
        partial = pipeline.read_signed(self.run_dir / 'generation-checkpoint.json')
        self.assertEqual(partial['completed_profiles'], ['coverage_mini'])
        self.assertEqual(len(partial['records']), 1)
        resumed_calls = []
        def resume(profile):
            resumed_calls.append(profile['id'])
            return original(profile)
        with patch.object(pipeline, 'generate_candidates', side_effect=resume):
            complete = self.generate()
            again = self.generate()
        self.assertEqual(resumed_calls, ['random_same', 'random_other'])
        self.assertEqual(complete['created_at'], partial['created_at'])
        self.assertEqual(len(complete['records']), 3)
        self.assertEqual(again['status'], 'generated')

    def test_evaluation_seed_cannot_reuse_generation_or_pool_seed(self):
        generation = self.generate()
        forbidden = {p['generation']['seed'] for p in generation['records']}
        forbidden.update(p['generation']['pool_seed'] for p in generation['records'])
        for seed in forbidden:
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                self.evaluate(seed=seed)
        self.assertFalse((self.run_dir / 'latest-evaluation.json').exists())

    def test_incomplete_evaluation_cannot_be_projected_and_can_be_resumed(self):
        self.generate()
        interrupted = self.evaluate(stop_after_batches=1)
        self.assertEqual(interrupted['status'], 'interrupted')
        self.assertEqual(interrupted['completed_draws'], 16)
        self.assertFalse((self.run_dir / 'latest-evaluation.json').exists())
        with self.assertRaises((ValueError, OSError)):
            pipeline.project(self.run_dir)
        result = self.evaluate()
        self.assertEqual(result['completed_draws'], 65)
        self.assertEqual(len(pipeline.project(self.run_dir)['profiles']), 3)

    def test_record_content_and_proof_links_are_revalidated(self):
        record = self.generate()['records'][0]
        modified = copy.deepcopy(record)
        modified['grids'][0][0][-1] = 50
        with self.assertRaises(ValueError):
            pipeline.check_record(modified)
        modified = copy.deepcopy(record)
        modified['certificate']['content_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            pipeline.check_record(modified)

    def test_cli_commands_and_publish_exports_remain_inside_the_temporary_site(self):
        output = self.directory / 'catalogue.json'
        commands = [
            ['validate', '--config', str(self.config)],
            ['generate', '--config', str(self.config), '--run-dir', str(self.run_dir)],
            ['evaluate', '--run-dir', str(self.run_dir)],
            ['compare', '--run-dir', str(self.run_dir)],
            ['export', '--run-dir', str(self.run_dir), '--output', str(output)],
        ]
        with redirect_stdout(io.StringIO()):
            for args in commands:
                self.assertEqual(pipeline.main(args), 0, args)
        dataset = pipeline.read(output)
        self.assertEqual(dataset['origin'], 'local_pipeline')
        self.assertEqual(len(dataset['profiles']), 3)
        self.assertTrue((self.run_dir / 'comparison.json').exists())
        self.assertEqual(len(list((self.run_dir / 'exports').glob('*.json'))), 3)
        for csv in (self.run_dir / 'exports').glob('*.csv'):
            self.assertEqual(len(csv.read_text().splitlines()), 7)
        archives = list((self.site / 'dist/data/portfolio_runs').glob('*/catalogue.json'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(pipeline.read(archives[0]), dataset)
        before = archives[0].read_bytes()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(pipeline.main(commands[-1]), 0)
        self.assertEqual(archives[0].read_bytes(), before)

    def test_real_cli_validation_runs_under_python_optimization(self):
        command = [sys.executable, '-O', str(ROOT / 'engine/portfolio_pipeline.py'),
                   'validate', '--config', str(self.config)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['profiles'], 3)
        altered = copy.deepcopy(self.bundle)
        altered['profiles'][0]['constraints']['grid_count'] = True
        self.config.write_text(json.dumps(altered))
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
