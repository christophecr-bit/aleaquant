"""Les anciens tirages Loto partagent parfois une date, jamais leur identifiant.

Ce test exerce le build de pages sur de vrais faits des deux formules, sans écrire
dans dist/. Une régression sur l'URL ou la comparabilité serait visible au lecteur.
"""
import importlib.util
from hashlib import sha256
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
import build_pages  # noqa: E402

SOURCE_FACTS = ROOT / 'dist' / 'data' / 'facts'


class LotoPagesTests(unittest.TestCase):
    def test_mini_histogrammes_par_tirage_et_par_regime(self):
        """Chaque formule conserve ses lois exactes et le repère du tirage."""
        for draw_id in ('EM-26078', 'EM-2011053', 'LO-20260928', 'LO-19920328-1'):
            with self.subTest(draw_id=draw_id):
                facts = json.loads((SOURCE_FACTS / f'{draw_id}.json').read_text())
                render = build_pages.page_html if draw_id.startswith('EM-') else build_pages.loto_page_html
                page = render(facts, None, None)
                self.assertGreaterEqual(page.count('class="metric-spark"'), 5)
                self.assertIn('Trait orange : valeur du tirage', page)
                self.assertIn('La rareté indiquée au-dessus porte sur la classe exacte', page)
                self.assertIn('stroke="#eb6834"', page)

        em = json.loads((SOURCE_FACTS / 'EM-26078.json').read_text())
        sum_fact = next(f for f in em['facts'] if f.get('metric') == 'main.sum')
        wrong = build_pages.read_regime_law(str(ROOT / 'dist/data/laws/regime-5-49.json'))
        self.assertEqual(build_pages.metric_spark(sum_fact, {'main': wrong}), '')

    def test_article_approuve_associe_uniquement_au_bon_tirage(self):
        with tempfile.TemporaryDirectory() as dossier:
            dist = Path(dossier) / 'dist'
            data = dist / 'data'
            facts_dir = data / 'facts'
            facts_dir.mkdir(parents=True)
            for did in ('EM-2011053', 'LO-19920328-1', 'LO-19920328-2'):
                shutil.copy2(SOURCE_FACTS / f'{did}.json', facts_dir / f'{did}.json')
            (data / 'draws.json').write_text(json.dumps({'rows': [
                ['EM-2011053', '2011-09-06', 'euromillions-50-11-v1']
            ]}))
            article = {
                'schema': 'aleaquant-article-v1',
                'kind': 'draw_report', 'status': 'HUMAN_APPROVED',
                'article_id': 'tirage-LO-19920328-1',
                'research_pack': {
                    'draw_id': 'LO-19920328-1',
                    'facts_sha256': sha256((facts_dir / 'LO-19920328-1.json').read_bytes()).hexdigest(),
                },
                'draft': {'title': 'Un regard sur ce tirage',
                          'body': 'Premier paragraphe.\n\n<script>alerte</script>', 'claims': []},
            }
            article['draft']['research_pack_sha256'] = build_pages.content_sha256(article['research_pack'])
            article['draft_sha256'] = build_pages.content_sha256(article['draft'])
            article['human_decision'] = {'approved': True, 'reviewer': 'Test',
                                         'draft_sha256': article['draft_sha256']}
            (dist / 'articles.json').write_text(json.dumps({'articles': [article, {
                **article, 'status': 'READY_FOR_HUMAN',
                'article_id': 'tirage-LO-19920328-2',
                'research_pack': {'draw_id': 'LO-19920328-2'},
            }]}))
            original_data, original_dist = build_pages.DATA, build_pages.DIST
            build_pages.DATA, build_pages.DIST = data, dist
            try:
                build_pages.build()
                first_path = dist / 'tirages/loto/LO-19920328-1/index.html'
                first = first_path.read_text()
                self.assertIn('Un regard sur ce tirage', first)
                self.assertIn('Premier paragraphe.', first)
                self.assertIn('&lt;script&gt;alerte&lt;/script&gt;', first)
                self.assertNotIn('<script>alerte</script>', first)
                self.assertNotIn('Un regard sur ce tirage',
                                 (dist / 'tirages/loto/LO-19920328-2/index.html').read_text())
                self.assertNotIn('Un regard sur ce tirage',
                                 (dist / 'tirages/euromillions/2011-09-06/index.html').read_text())
                article['draft']['title'] = 'Titre revu'
                article['draft_sha256'] = build_pages.content_sha256(article['draft'])
                article['human_decision']['draft_sha256'] = article['draft_sha256']
                (dist / 'articles.json').write_text(json.dumps({'articles': [article]}))
                self.assertEqual(build_pages.refresh_draw_page('LO-19920328-1'), first_path)
                self.assertIn('Titre revu', first_path.read_text())
                article['draft']['title'] = 'Titre changé sans nouvelle approbation'
                (dist / 'articles.json').write_text(json.dumps({'articles': [article]}))
                build_pages.refresh_draw_page('LO-19920328-1')
                self.assertNotIn('Titre changé sans nouvelle approbation', first_path.read_text())
                self.assertNotIn('id="article-title"', first_path.read_text())
            finally:
                build_pages.DATA, build_pages.DIST = original_data, original_dist

    def test_sessions_et_regimes_restent_distincts(self):
        with tempfile.TemporaryDirectory() as dossier:
            dist = Path(dossier) / 'dist'
            data = dist / 'data'
            facts_dir = data / 'facts'
            facts_dir.mkdir(parents=True)
            loto_ids = ('LO-19920328-1', 'LO-19920328-2', 'LO-20081006',
                        'LO-20260928')
            for did in loto_ids + ('EM-2011053',):
                shutil.copy2(SOURCE_FACTS / f'{did}.json', facts_dir / f'{did}.json')
            # Le pilote EuroMillions lit draws.json ; une ligne suffit ici.
            (data / 'draws.json').write_text(json.dumps({
                'rows': [['EM-2011053', '2011-09-06', 'euromillions-50-11-v1']]
            }), encoding='utf-8')
            original_data, original_dist = build_pages.DATA, build_pages.DIST
            build_pages.DATA, build_pages.DIST = data, dist
            try:
                build_pages.build()
            finally:
                build_pages.DATA, build_pages.DIST = original_data, original_dist

            loto = dist / 'tirages' / 'loto'
            first = (loto / 'LO-19920328-1' / 'index.html').read_text()
            second = (loto / 'LO-19920328-2' / 'index.html').read_text()
            self.assertIn('1er tirage', first)
            self.assertIn('2e tirage', second)
            self.assertIn('href="../LO-19920328-2/"', first)
            self.assertIn('Numéro complémentaire', first)
            self.assertIn('tiré, mais non coché sur la grille', first)
            self.assertIn('1 sur 13\u202f983\u202f816', first)
            self.assertNotIn('étoiles', first)
            self.assertIn('1 sur 13\u202f983\u202f816', second)

            reforme = (loto / 'LO-20081006' / 'index.html').read_text()
            self.assertIn('Numéro Chance', reforme)
            self.assertIn('1 sur 19\u202f068\u202f840', reforme)
            self.assertIn('0 tirages antérieurs comparables', reforme)
            self.assertIn('même formule 5/49', reforme)
            self.assertNotIn('Numéro complémentaire', reforme)

            sitemap = (dist / 'sitemap.xml').read_text()
            for did in loto_ids:
                self.assertEqual(sitemap.count(f'/tirages/loto/{did}/'), 1)
            self.assertIn('/tirages/euromillions/2011-09-06/', sitemap)
            index = (loto / 'index.html').read_text()
            self.assertIn('LO-19920328-1/', index)
            self.assertIn('LO-19920328-2/', index)
            self.assertEqual(index.count('data-date="1992-03-28"'), 2)
            self.assertIn('id="loto-date"', index)
            self.assertIn('loto-index.js', index)
            hub = (dist / 'tirages' / 'index.html').read_text()
            self.assertIn('href="/tirages/euromillions/"', hub)
            self.assertIn('href="/tirages/loto/"', hub)
            self.assertIn('Keno est en préparation', hub)
            self.assertIn('href="/tirages/">Tirages', first)
            self.assertIn('/tirages/</loc>', sitemap)


if __name__ == '__main__':
    unittest.main()
