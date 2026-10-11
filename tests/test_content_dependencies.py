"""Bounded documentary-gate regressions; no deployment, LLM or remote request.

Version 1.0 · 2026-10-10. HTTP responses below are explicit test fixtures,
never evidence attached to the real site's registry.
"""
from copy import deepcopy
from datetime import datetime, timezone
from contextlib import redirect_stdout
from hashlib import sha256
import html
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from content_dependencies import (DependencyError, article_node, attach_publications,
                                  deployment_report, digest, empty_registry, notion_node,
                                  page_node, plan_batch, publication_report, require_article,
                                  require_publication, update_nodes, validate_registry,
                                  verify_live_prerequisites)


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DocumentaryDependenciesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.assets = self.base / 'dist'
        self.assets.mkdir()
        # Independent expected chain: overlap -> grid pair -> grid -> number/star.
        self.records = [
            {'id': 'numero', 'label': 'Numéro', 'definition': 'Une valeur du domaine autorisé.', 'requires': [], 'related': ['grille']},
            {'id': 'etoile', 'label': 'Étoile', 'definition': 'Une valeur du second domaine.', 'requires': []},
            {'id': 'grille', 'label': 'Grille', 'definition': 'Un ensemble de numéros et d’étoiles.', 'requires': ['numero', 'etoile']},
            {'id': 'paire-grilles', 'label': 'Paire de grilles', 'definition': 'Deux grilles distinctes considérées ensemble.', 'requires': ['grille']},
            {'id': 'recouvrement', 'label': 'Recouvrement', 'definition': 'Les éléments communs aux deux grilles.', 'requires': ['paire-grilles']},
        ]
        self.nodes = [notion_node(record) for record in self.records]
        self.page_body = b'<h1>Atlas de test</h1>'
        self.page = page_node('page:atlas', 'portefeuilles/index.html', sha256(self.page_body).hexdigest(), ['recouvrement'])
        self.registry = update_nodes(empty_registry(), self.nodes + [self.page], ['page:atlas'])

    def references(self, nodes=None):
        return [{'id': node['id'], 'version': node['version']} for node in (nodes or self.nodes)]

    def observed(self, registry=None, nodes=None, body=None, **overrides):
        registry = deepcopy(registry or self.registry)
        nodes = nodes or [n for n in registry['nodes'] if n['kind'] == 'notion']
        if body is None:
            body = ('<!doctype html>' + ''.join(
                '<article id="{id}" data-notion-id="{id}" data-notion-version="{version}" data-notion-sha256="{content_sha256}"><h2>{label}</h2><p>{definition}</p></article>'.format(
                    **node, label=html.escape(node['content']['label']), definition=html.escape(node['content']['definition']))
                for node in nodes)).encode()
        response = self.base / 'evidence/glossary.html'
        response.parent.mkdir(exist_ok=True)
        response.write_bytes(body)
        observation = {'id': 'fixture-observation', 'environment': 'production', 'anonymous': True,
                       'url': 'https://aleaquant.org/comprendre/glossaire/', 'http_status': 200,
                       'checked_at': datetime.now(timezone.utc).isoformat(),
                       'deployment_id': 'fixture-only-not-a-real-deployment',
                       'asset_sha256': sha256(body).hexdigest(), 'response_path': 'evidence/glossary.html'}
        observation.update(overrides)
        return attach_publications(registry, observation, self.references(nodes), self.base)

    def approved_article(self):
        pack = {'evidence': []}
        draft = {'title': 'Test', 'body': 'Test de transport', 'claims': [{'text': 'Test'}],
                 'research_pack_sha256': digest(pack)}
        content_sha = digest(draft)
        return {'schema': 'aleaquant-article-v1', 'status': 'HUMAN_APPROVED', 'article_id': 'test-1',
                'draft': draft, 'draft_sha256': content_sha, 'research_pack': pack,
                'human_decision': {'approved': True, 'reviewer': 'Témoin', 'draft_sha256': content_sha}}

    def write_registry(self, registry):
        path = self.base / 'configs/content-dependencies.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(registry, ensure_ascii=False))
        return path

    def test_local_draft_and_declared_published_are_not_publication_proof(self):
        for state in ('draft', 'local', 'published'):
            with self.subTest(state=state):
                registry = deepcopy(self.registry)
                for node in registry['nodes']:
                    if node['kind'] == 'notion':
                        node['state'] = state
                report = publication_report(registry, 'page:atlas', '1.0', base_dir=self.base)
                self.assertEqual(report['status'], 'blocked')
                self.assertEqual({b['id'] for b in report['blockers']},
                                 {'recouvrement', 'paire-grilles', 'grille', 'numero', 'etoile'})
                self.assertEqual(report['published_prerequisites'], [])

    def test_transitive_versioned_closure_and_related_backlink(self):
        published = self.observed()
        report = require_publication(published, 'page:atlas', '1.0', self.page['content_sha256'], self.base)
        self.assertEqual({p['node_id'] for p in report['published_prerequisites']},
                         {'recouvrement', 'paire-grilles', 'grille', 'numero', 'etoile'})
        self.assertEqual(report['status'], 'ready')
        # A public complex notion does not cover a missing root version.
        root = next(n for n in published['nodes'] if n['id'] == 'numero')
        root['state'] = 'local'
        report = publication_report(published, 'page:atlas', '1.0', base_dir=self.base)
        self.assertEqual([b['id'] for b in report['blockers']], ['numero'])

    def test_missing_subject_notions_and_required_version_fail_closed(self):
        for subject, version in (('page:unknown', '1.0'), ('page:atlas', '2.0')):
            self.assertEqual(publication_report(self.registry, subject, version)['status'], 'blocked')
        record = deepcopy(self.records[-1])
        bad = notion_node(record, versions={'paire-grilles': '2.0'})
        registry = update_nodes(self.registry, [bad])
        report = publication_report(registry, 'page:atlas', '1.0', base_dir=self.base)
        self.assertTrue(any(b['id'] == 'paire-grilles' and b['version'] == '2.0' for b in report['blockers']))

    def test_cycle_rejected_related_cycles_allowed(self):
        self.assertIs(validate_registry(self.registry), self.registry)
        record = deepcopy(self.records[0])
        record['requires'] = ['recouvrement']
        registry = update_nodes(self.registry, [notion_node(record)])
        with self.assertRaisesRegex(DependencyError, 'Cycle'):
            validate_registry(registry)

    def test_topological_batch_does_not_publish_and_remote_proof_is_needed(self):
        before = deepcopy(self.registry)
        plan = plan_batch(self.registry, [{'id': 'page:atlas', 'version': '1.0'}])
        order = [n['id'] for n in plan['order']]
        self.assertLess(order.index('numero'), order.index('grille'))
        self.assertLess(order.index('grille'), order.index('paire-grilles'))
        self.assertLess(order.index('paire-grilles'), order.index('recouvrement'))
        self.assertLess(order.index('recouvrement'), order.index('page:atlas'))
        self.assertFalse(plan['grants_publication'])
        self.assertEqual(self.registry, before)
        with self.assertRaises(DependencyError):
            require_publication(self.registry, 'page:atlas', '1.0', base_dir=self.base)
        self.assertEqual(require_publication(self.observed(), 'page:atlas', '1.0', base_dir=self.base)['status'], 'ready')

    def test_proof_rejects_recette_login_http_error_wrong_url_or_sha(self):
        for overrides in ({'environment': 'recette'}, {'anonymous': False}, {'http_status': 302},
                          {'url': 'https://recette.aleaquant.org/comprendre/glossaire/'},
                          {'asset_sha256': '0' * 64}):
            with self.subTest(overrides=overrides), self.assertRaises(DependencyError):
                self.observed(**overrides)
        with self.assertRaises(DependencyError):
            self.observed(body=b'<h1>Cloudflare Access login</h1>')

    def test_exact_marker_and_visible_definition_required(self):
        self.observed()
        body = (self.base / 'evidence/glossary.html').read_bytes()
        for corrupted in (body.replace(self.nodes[0]['content_sha256'].encode(), b'0' * 64),
                          body.replace('Une valeur du domaine autorisé.'.encode(), b'Definition altered.'),
                          body.replace(b'data-notion-version="1.0"', b'data-notion-version="2.0"')):
            with self.subTest(body=corrupted[:60]), self.assertRaises(DependencyError):
                self.observed(body=corrupted)

    def test_retained_response_modified_after_proof_blocks(self):
        registry = self.observed()
        (self.base / 'evidence/glossary.html').write_text('Modification locale')
        report = publication_report(registry, 'page:atlas', '1.0', base_dir=self.base)
        self.assertEqual(report['status'], 'blocked')
        self.assertTrue(all('SHA' in b['reason'] for b in report['blockers']))

    def test_published_versions_immutable_but_local_draft_can_be_revised(self):
        changed = deepcopy(self.records[0])
        changed['definition'] += ' Définition révisée.'
        self.assertEqual(update_nodes(self.registry, [notion_node(changed)])['nodes'][0]['state'], 'local')
        published = self.observed()
        with self.assertRaisesRegex(DependencyError, 'immuable'):
            update_nodes(published, [notion_node(changed)])
        revised = update_nodes(published, [notion_node(changed, version='2.0')])
        self.assertEqual(next(n for n in revised['nodes'] if n['id'] == 'numero' and n['version'] == '1.0')['state'], 'published')
        self.assertEqual(next(n for n in revised['nodes'] if n['id'] == 'numero' and n['version'] == '2.0')['state'], 'local')

    def test_strict_schema_types_and_undeclared_mutations(self):
        for mutate in (lambda r: r.update({'published': True}),
                       lambda r: r.update({'nodes': {}}),
                       lambda r: r['nodes'][0].update({'version': 1}),
                       lambda r: r['nodes'][0]['content'].update({'definition': 'Changed without new digest'}),
                       lambda r: r['nodes'][0]['target'].update({'path': '../secret.html'})):
            registry = deepcopy(self.registry)
            mutate(registry)
            with self.assertRaises(DependencyError):
                validate_registry(registry)

    def test_production_import_blocks_before_any_write_then_exact_approved_sha_passes(self):
        importer = module_at('documentary_test_importer', ROOT / 'scripts/import_article.py')
        article = self.approved_article()
        subject = article_node(article, ['recouvrement'], target_path='articles/test-1/index.html')
        registry = update_nodes(self.registry, [subject])
        self.write_registry(registry)
        source, destination = self.base / 'approved.json', self.assets / 'articles.json'
        source.write_text(json.dumps(article))
        destination.write_text('{"schema":"aleaquant-journal-v1","articles":[]}')
        before = destination.read_bytes()
        with patch.object(importer, 'ROOT', self.base):
            with self.assertRaisesRegex(DependencyError, 'bloquantes'):
                importer.import_article(source, destination)
            self.assertEqual(destination.read_bytes(), before)
            self.assertFalse(destination.with_suffix('.tmp').exists())
            self.write_registry(self.observed(registry))
            self.assertEqual(importer.import_article(source, destination), 'test-1')
        self.assertEqual(json.loads(destination.read_text())['articles'], [article])
        changed = deepcopy(article)
        changed['draft']['body'] += ' Modifié.'
        with self.assertRaisesRegex(DependencyError, 'approuvé'):
            require_article(changed, self.base / 'configs/content-dependencies.json', self.base)

    def test_subject_inventory_and_sha_required_even_with_all_notions_published(self):
        registry = self.observed()
        with self.assertRaisesRegex(DependencyError, 'non enregistré'):
            require_article(self.approved_article(), self.write_registry(registry), self.base)
        with self.assertRaisesRegex(DependencyError, 'SHA du sujet'):
            require_publication(registry, 'page:atlas', '1.0', '0' * 64, self.base)

    def test_deployment_gate_managed_page_articles_and_glossary_only_bootstrap(self):
        page_path = self.assets / self.page['target']['path']
        page_path.parent.mkdir(parents=True)
        page_path.write_bytes(self.page_body)
        self.assertEqual(deployment_report(self.registry, self.assets, self.base)['status'], 'blocked')
        registry = self.observed()
        self.assertEqual(deployment_report(registry, self.assets, self.base)['status'], 'ready')
        (self.assets / 'articles.json').write_text(json.dumps({'articles': [self.approved_article()]}))
        self.assertEqual(deployment_report(registry, self.assets, self.base)['status'], 'blocked')
        # Separate documentary-only asset lot contains no managed consumer page/article.
        glossary_only = self.base / 'glossary-only'
        (glossary_only / 'comprendre/glossaire').mkdir(parents=True)
        (glossary_only / 'comprendre/glossaire/index.html').write_bytes((self.base / 'evidence/glossary.html').read_bytes())
        self.assertEqual(deployment_report(self.registry, glossary_only, self.base)['status'], 'ready')

    def test_cli_and_standard_deploy_hook_reject_before_upload(self):
        path = self.assets / self.page['target']['path']
        path.parent.mkdir(parents=True)
        path.write_bytes(self.page_body)
        registry_path = self.write_registry(self.registry)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/check_content_dependencies.py'),
                                 '--registry', str(registry_path), '--base-dir', str(self.base),
                                 '--assets', str(self.assets)], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'blocked')
        self.assertIn('python3 scripts/check_content_dependencies.py', (ROOT / 'wrangler.jsonc').read_text())

    def test_observation_fetches_anonymously_but_does_not_deploy(self):
        command = module_at('documentary_test_cli', ROOT / 'scripts/check_content_dependencies.py')
        self.observed()
        body = (self.base / 'evidence/glossary.html').read_bytes()
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def geturl(self): return 'https://aleaquant.org/comprendre/glossaire/'
            def read(self, bound): return body
        with patch.object(command, 'urlopen', return_value=Response()) as fetch:
            result, observation = command.observe(self.registry, 'comprendre/glossaire/index.html',
                                                   'fixture-only', self.base / 'evidence/new', self.base)
        request = fetch.call_args.args[0]
        self.assertNotIn('Authorization', request.headers)
        self.assertNotIn('Cookie', request.headers)
        self.assertEqual(observation['asset_sha256'], sha256(body).hexdigest())
        self.assertEqual(require_publication(result, 'page:atlas', '1.0', base_dir=self.base)['status'], 'ready')
        self.assertEqual(self.registry['observations'], [])

    def test_live_gate_uses_one_get_per_asset_without_mutating_recorded_proof(self):
        registry = self.observed()
        before = deepcopy(registry)
        subject = require_publication(registry, 'page:atlas', '1.0', base_dir=self.base)
        report = {'status': 'ready', 'subjects': [subject, deepcopy(subject)]}
        body = (self.base / 'evidence/glossary.html').read_bytes()
        calls = []
        def fetch(url):
            calls.append(url)
            return 200, url, body
        result = verify_live_prerequisites(registry, report, fetch)
        self.assertEqual(calls, ['https://aleaquant.org/comprendre/glossaire/'])
        self.assertEqual(len(result['checked_public_assets']), 1)
        self.assertEqual(registry, before)

    def test_live_gate_refuses_404_login_modified_sha_and_incompatible_versions(self):
        registry = self.observed()
        report = require_publication(registry, 'page:atlas', '1.0', base_dir=self.base)
        body = (self.base / 'evidence/glossary.html').read_bytes()
        for response in ((404, 'https://aleaquant.org/comprendre/glossaire/', b'Not found'),
                         (200, 'https://login.example/access', body),
                         (200, 'https://aleaquant.org/comprendre/glossaire/', b'Login or changed definition')):
            with self.subTest(response=response[:2]), self.assertRaises(DependencyError):
                verify_live_prerequisites(registry, report, lambda url: response)
        def missing(url):
            raise HTTPError(url, 404, 'Not found', {}, None)
        with self.assertRaisesRegex(DependencyError, 'inaccessible'):
            verify_live_prerequisites(registry, report, missing)
        conflict = deepcopy(report)
        conflict['published_prerequisites'][0]['asset_sha256'] = '0' * 64
        with self.assertRaisesRegex(DependencyError, 'incompatibles'):
            verify_live_prerequisites(registry, conflict, lambda url: self.fail('No GET on incompatible proofs'))
        blocked = publication_report(self.registry, 'page:atlas', '1.0', base_dir=self.base)
        with self.assertRaises(DependencyError):
            verify_live_prerequisites(self.registry, blocked, lambda url: self.fail('No GET on blocked report'))

    def test_live_flag_runs_only_for_real_deploy_hook_and_wrapper_tracks_exact_assets(self):
        command = module_at('documentary_live_cli', ROOT / 'scripts/check_content_dependencies.py')
        wrapper = module_at('documentary_deploy_wrapper', ROOT / 'scripts/deploy_site.py')
        registry = self.observed()
        path = self.assets / self.page['target']['path']
        path.parent.mkdir(parents=True)
        path.write_bytes(self.page_body)
        registry_path = self.write_registry(registry)
        argv = ['--registry', str(registry_path), '--base-dir', str(self.base),
                '--assets', str(self.assets), '--live-on-deploy']
        for wrangler_command, expected_calls in (('dev', 0), ('', 0), ('deploy', 1)):
            with patch.dict(command.os.environ, {'WRANGLER_COMMAND': wrangler_command}), \
                    patch.object(command, 'verify_live_prerequisites', return_value={'status': 'ready'}) as verify, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(command.main(argv), 0)
                self.assertEqual(verify.call_count, expected_calls)
        config, report = wrapper.checked_config(self.assets, registry_path, base_dir=self.base)
        self.assertEqual(config['assets']['directory'], str(self.assets.resolve()))
        self.assertIn(str(self.assets.resolve()), config['build']['command'])
        self.assertIn('--live-on-deploy', config['build']['command'])
        self.assertEqual(report['status'], 'ready')

    def test_new_observed_version_selected_explicitly_preserves_old_proof(self):
        command = module_at('documentary_version_cli', ROOT / 'scripts/check_content_dependencies.py')
        old = self.observed()
        proof_before = deepcopy(old['publications'])
        record = deepcopy(self.records[0])
        record['definition'] += ' Nouvelle version.'
        revised = notion_node(record, version='1.1')
        registry = update_nodes(old, [revised])
        body = ('<article id="numero" data-notion-id="numero" data-notion-version="1.1" data-notion-sha256="{content_sha256}"><h2>{label}</h2><p>{definition}</p></article>'.format(
            **revised, **revised['content'])).encode()
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def geturl(self): return 'https://aleaquant.org/comprendre/glossaire/'
            def read(self, bound): return body
        with patch.object(command, 'urlopen', return_value=Response()) as fetch:
            with self.assertRaisesRegex(DependencyError, 'Plusieurs versions'):
                command.observe(registry, 'comprendre/glossaire/index.html', 'fixture-new-version',
                                self.base / 'evidence/new', self.base)
            fetch.assert_not_called()
            result, observation = command.observe(registry, 'comprendre/glossaire/index.html', 'fixture-new-version',
                                                   self.base / 'evidence/new', self.base,
                                                   [{'id': 'numero', 'version': '1.1'}])
        self.assertTrue(all(proof in result['publications'] for proof in proof_before))
        self.assertEqual(next(n for n in result['nodes'] if n['id'] == 'numero' and n['version'] == '1.1')['state'], 'published')
        self.assertEqual(next(n for n in result['nodes'] if n['id'] == 'numero' and n['version'] == '1.0')['content_sha256'], self.nodes[0]['content_sha256'])

    def test_glossary_increment_keeps_existing_consumers_ready_but_new_dependency_blocked(self):
        registry = self.observed()
        page = self.assets / self.page['target']['path']
        page.parent.mkdir(parents=True)
        page.write_bytes(self.page_body)
        glossary = self.assets / 'comprendre/glossaire/index.html'
        glossary.parent.mkdir(parents=True)
        glossary.write_bytes((self.base / 'evidence/glossary.html').read_bytes())
        self.assertEqual(deployment_report(registry, self.assets, self.base)['status'], 'ready')
        glossary.write_bytes(glossary.read_bytes() + b'<!-- HTML asset revision -->')
        self.assertEqual(deployment_report(registry, self.assets, self.base)['status'], 'ready')
        new = notion_node({'id': 'triplet', 'label': 'Triplet', 'definition': 'Trois valeurs distinctes.', 'requires': ['numero']})
        new_markup = ('<article id="triplet" data-notion-id="triplet" data-notion-version="1.0" data-notion-sha256="{content_sha256}"><h2>{label}</h2><p>{definition}</p></article>'.format(**new, **new['content'])).encode()
        glossary.write_bytes(glossary.read_bytes() + new_markup)
        registry = update_nodes(registry, [new])
        self.assertEqual(deployment_report(registry, self.assets, self.base)['status'], 'ready')
        revised_page = page_node('page:new-atlas', 'new-atlas/index.html', self.page['content_sha256'], ['triplet'])
        registry = update_nodes(registry, [revised_page], ['page:atlas', 'page:new-atlas'])
        new_page = self.assets / 'new-atlas/index.html'
        new_page.parent.mkdir()
        new_page.write_bytes(self.page_body)
        report = deployment_report(registry, self.assets, self.base)
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(next(s for s in report['subjects'] if s['subject'] == 'page:atlas')['status'], 'ready')
        self.assertTrue(any(b['id'] == 'triplet' for s in report['subjects'] if s['subject'] == 'page:new-atlas' for b in s['blockers']))
        # After a separately approved glossary delivery, refresh the public body
        # proof. Existing definitions retain their version/SHA and old evidence.
        command = module_at('documentary_increment_cli', ROOT / 'scripts/check_content_dependencies.py')
        current_body = glossary.read_bytes()
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def geturl(self): return 'https://aleaquant.org/comprendre/glossaire/'
            def read(self, bound): return current_body
        with patch.object(command, 'urlopen', return_value=Response()):
            refreshed, observation = command.observe(registry, 'comprendre/glossaire/index.html', 'fixture-increment',
                                                      self.base / 'evidence/refreshed', self.base)
        refreshed_report = deployment_report(refreshed, self.assets, self.base)
        self.assertEqual(refreshed_report['status'], 'ready')
        live = verify_live_prerequisites(refreshed, refreshed_report, lambda url: (200, url, current_body))
        self.assertEqual(len(live['checked_public_assets']), 1)
        self.assertGreater(len(refreshed['publications']), len(registry['publications']))

    def test_consumer_lot_refuses_removing_or_replacing_an_existing_required_definition(self):
        registry = self.observed()
        page = self.assets / self.page['target']['path']
        page.parent.mkdir(parents=True)
        page.write_bytes(self.page_body)
        glossary = self.assets / 'comprendre/glossaire/index.html'
        glossary.parent.mkdir(parents=True)
        body = (self.base / 'evidence/glossary.html').read_bytes()
        for changed in (body.replace(b'id="numero"', b'id="deleted-numero"'),
                        body.replace(self.nodes[0]['content_sha256'].encode(), b'0' * 64)):
            with self.subTest(body=changed[:60]):
                glossary.write_bytes(changed)
                report = deployment_report(registry, self.assets, self.base)
                self.assertEqual(report['status'], 'blocked')
                self.assertTrue(any('définition requise' in b['reason'] for s in report['subjects']
                                    if s['subject'] == 'page:atlas' for b in s.get('blockers', [])))

    def test_execute_refuses_documentary_subset_without_site_index(self):
        wrapper = module_at('documentary_subset_wrapper', ROOT / 'scripts/deploy_site.py')
        self.observed()
        registry = self.registry
        registry_path = self.write_registry(registry)
        glossary_only = self.base / 'glossary-only'
        glossary = glossary_only / 'comprendre/glossaire/index.html'
        glossary.parent.mkdir(parents=True)
        glossary.write_bytes((self.base / 'evidence/glossary.html').read_bytes())
        with patch.object(wrapper.subprocess, 'run') as deploy, patch('sys.stderr', new=io.StringIO()) as errors:
            self.assertEqual(wrapper.main(['--assets', str(glossary_only), '--registry', str(registry_path), '--execute']), 1)
            deploy.assert_not_called()
            self.assertIn('Lot incomplet', errors.getvalue())


if __name__ == '__main__':
    unittest.main()
