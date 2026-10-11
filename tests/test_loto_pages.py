"""AleaQuant — régressions des pages de tirage et de leurs histogrammes.

Version : 0.5 | Date : 2026-10-02 | Auteur : AleaQuant
Historique : 0.5 teste les sommes par dizaine sur EuroMillions, Loto et Keno.
Historique : 0.4 vérifie les pages Keno actives et l'exclusion du régime 20/70.
Historique : 0.3 vérifie le nom du jeu et la date dans le titre visible des fiches.
Historique : 0.2 vérifie l'alignement des mini-histogrammes avec l'accueil.
TODO : ajouter une vérification visuelle navigateur de la densité des 16 boules Keno.

Les anciens tirages Loto partagent parfois une date, jamais leur identifiant.

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
    def test_mini_histogramme_reprend_toutes_les_classes_comme_l_accueil(self):
        facts = json.loads((SOURCE_FACTS / 'EM-26078.json').read_text())
        fact = next(f for f in facts['facts'] if f.get('metric') == 'main.sum')
        laws = build_pages.card_laws(facts)
        svg = build_pages.metric_spark(fact, laws)
        expected_classes = len(laws['main']['laws']['sum'])

        self.assertEqual(svg.count('<rect '), expected_classes)
        self.assertIn('Toutes les classes de la loi exacte sont représentées', svg)
        self.assertIn('stroke="#eb6834"', svg)
        self.assertNotIn('<path ', svg)

    def test_mini_histogrammes_par_tirage_et_par_regime(self):
        """Chaque formule conserve ses lois exactes et le repère du tirage."""
        for draw_id in ('EM-26078', 'EM-2011053', 'LO-20260928', 'LO-19920328-1', 'KE-26364'):
            with self.subTest(draw_id=draw_id):
                facts = json.loads((SOURCE_FACTS / f'{draw_id}.json').read_text())
                render = (build_pages.page_html if draw_id.startswith('EM-') else
                          build_pages.loto_page_html if draw_id.startswith('LO-') else
                          build_pages.keno_page_html)
                page = render(facts, None, None)
                game = ('EuroMillions' if draw_id.startswith('EM-') else
                        'Loto' if draw_id.startswith('LO-') else 'Keno')
                date = build_pages.date_fr(facts['date'])
                date_label = (date if game in ('EuroMillions', 'Keno')
                              else build_pages.loto_draw_label(facts))
                self.assertIn(f'<h1 id="draw-title">{game} — tirage du {date_label}</h1>', page)
                self.assertIn(f'"headline": "{game} — tirage du {date_label}"', page)
                self.assertGreaterEqual(page.count('class="metric-spark"'), 5)
                self.assertIn('Trait orange : valeur du tirage', page)
                self.assertIn('La rareté indiquée au-dessus porte sur la classe exacte', page)
                self.assertIn('stroke="#eb6834"', page)
                self.assertIn('somme', page.lower())
                decade_check = {
                    'EM-26078': 'D5 : 1',
                    'LO-20260928': 'D5 : 2',
                    'KE-26364': 'D6 : 1',
                }
                if draw_id in decade_check:
                    self.assertIn(decade_check[draw_id], page)
                sum_check = {
                    'EM-26078': 'D1</span><span>2 numéros</span><strong>Σ 11',
                    'LO-20260928': 'D5</span><span>2 numéros</span><strong>Σ 92',
                    'KE-26364': 'D6</span><span>1 numéro</span><strong>Σ 53',
                }
                if draw_id in sum_check:
                    self.assertIn(sum_check[draw_id], page)
                    self.assertIn('Somme des valeurs tirées dans chaque tranche', page)
                    self.assertNotIn('Somme par dizaine<span class="chip', page)

        em = json.loads((SOURCE_FACTS / 'EM-26078.json').read_text())
        sum_fact = next(f for f in em['facts'] if f.get('metric') == 'main.sum')
        wrong = build_pages.read_regime_law(str(ROOT / 'dist/data/laws/regime-5-49.json'))
        self.assertEqual(build_pages.metric_spark(sum_fact, {'main': wrong}), '')

    def test_loto_toutes_les_mesures_scalaires_ont_un_graphe(self):
        facts = json.loads((SOURCE_FACTS / 'LO-20260928.json').read_text())
        page = build_pages.loto_page_html(facts, None, None)
        # Les deux signatures non ordonnées restent textuelles ; les 18 mesures
        # scalaires ont leur loi, notamment écart maximal et dizaines occupées.
        self.assertEqual(page.count('class="metric-spark"'), 18)
        self.assertIn('Loi exacte — écart maximal', page)
        self.assertIn('Loi exacte — dizaines occupées', page)
        self.assertNotIn('Loi exacte — écarts ordonnés', page)
        self.assertIn('height="1.00"', page)  # queue non nulle : au moins un pixel
        self.assertIn('chaque barre représente une classe de la loi exacte', page)
        self.assertNotIn('Certaines classes voisines sont regroupées', page)

    def test_keno_16_56_preserve_la_loi_exacte_et_distinct_de_la_grille_jouee(self):
        facts = json.loads((SOURCE_FACTS / 'KE-26364.json').read_text())
        page = build_pages.keno_page_html(facts, None, None)
        laws = build_pages.card_laws(facts)
        scalar_metrics = [f for f in facts['facts']
                          if f.get('category') == 'class_metric'
                          and isinstance(f.get('value'), (int, float))
                          and f.get('metric', '').split('.', 1)[-1] in laws['main']['laws']]

        self.assertIn('<h1 id="draw-title">Keno — tirage du 1 octobre 2026</h1>', page)
        self.assertIn('La probabilité affichée concerne le tirage exact de 16 numéros parmi 56', page)
        self.assertIn('elle ne donne pas la probabilité de gain d’une grille Keno jouée', page)
        self.assertIn('1 sur 41 648 951 840 265', page)
        self.assertEqual(page.count('class="metric-spark"'), len(scalar_metrics))
        self.assertIn('stroke="#eb6834"', page)
        self.assertIn('D1 : 4', page)
        self.assertIn('D6 : 1', page)
        self.assertNotIn('Keno est en préparation', page)

        old = json.loads((SOURCE_FACTS / 'KE-1993001.json').read_text())
        with self.assertRaisesRegex(ValueError, 'régime actif 16/56'):
            build_pages.keno_page_html(old, None, None)

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
            keno_ids = ('KE-26364', 'KE-1993001')
            for did in loto_ids + ('EM-2011053',) + keno_ids:
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
            self.assertIn('href="/tirages/keno/"', hub)
            self.assertIn('1 tirages analysés · formule actuelle 16/56', hub)
            self.assertNotIn('Keno est en préparation', hub)
            keno = dist / 'tirages' / 'keno'
            self.assertTrue((keno / 'KE-26364' / 'index.html').is_file())
            self.assertFalse((keno / 'KE-1993001' / 'index.html').exists())
            self.assertEqual((keno / 'index.html').read_text().count('href="KE-26364/"'), 1)
            self.assertNotIn('KE-1993001', (keno / 'index.html').read_text())
            self.assertIn('/tirages/keno/KE-26364/', sitemap)
            self.assertNotIn('/tirages/keno/KE-1993001/', sitemap)
            self.assertIn('href="/tirages/">Tirages', first)
            self.assertIn('/tirages/</loc>', sitemap)


if __name__ == '__main__':
    unittest.main()
