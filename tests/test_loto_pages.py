"""Les anciens tirages Loto partagent parfois une date, jamais leur identifiant.

Ce test exerce le build de pages sur de vrais faits des deux formules, sans écrire
dans dist/. Une régression sur l'URL ou la comparabilité serait visible au lecteur.
"""
import importlib.util
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
            hub = (dist / 'tirages' / 'index.html').read_text()
            self.assertIn('href="/tirages/euromillions/"', hub)
            self.assertIn('href="/tirages/loto/"', hub)
            self.assertIn('Keno est en préparation', hub)
            self.assertIn('href="/tirages/">Tirages', first)
            self.assertIn('/tirages/</loc>', sitemap)


if __name__ == '__main__':
    unittest.main()
