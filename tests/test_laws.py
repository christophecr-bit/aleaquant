"""Lois exactes par régime.

Trois garanties : la loi générique d'EuroMillions est celle déjà publiée ; la
construction par tranches reprenables donne exactement la même loi que la construction
d'un seul tenant ; et chaque loi enregistrée totalise C(n,k).
"""
import json
import shutil
import sys
import tempfile
import unittest
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from laws import (construire_reprenable, enumerable,  # noqa: E402
                  lois_par_enumeration)

LOIS = ROOT / 'dist' / 'data' / 'laws'


class LoiPublieeTests(unittest.TestCase):
    def test_euromillions_identique_a_la_loi_publiee(self):
        """La loi générique 5/50 doit être la loi déjà en production, champ par champ."""
        mien = json.loads((LOIS / 'regime-5-50.json').read_text(encoding='utf-8'))
        ref = json.loads((ROOT / 'dist' / 'data' / 'exact_laws.json').read_text(encoding='utf-8'))
        self.assertEqual(mien['total'], ref['main_total'])
        for champ, loi in ref['main'].items():
            self.assertEqual(mien['laws'][champ], loi, champ)


class TotauxTests(unittest.TestCase):
    def test_chaque_loi_totalise_c_n_k(self):
        """Preuve arithmétique : un total faux signale une énumération incomplète."""
        fichiers = sorted(LOIS.glob('regime-*.json'))
        self.assertGreaterEqual(len(fichiers), 8)
        for f in fichiers:
            d = json.loads(f.read_text(encoding='utf-8'))
            attendu = comb(d['domain'], d['picks'])
            self.assertEqual(d['total'], attendu, f.name)
            for champ, loi in d['laws'].items():
                self.assertEqual(sum(loi.values()), attendu, f'{f.name}/{champ}')


class ReprenableTests(unittest.TestCase):
    def test_tranches_egales_a_l_enumeration_directe(self):
        """La méthode qui a produit le Loto 6/49 doit être prouvée équivalente."""
        dossier = Path(tempfile.mkdtemp())
        try:
            fini = False
            while not fini:
                fini, _ = construire_reprenable(4, 20, dossier, budget_s=0)
            par_tranches = json.loads((dossier / 'regime-4-20.json').read_text(encoding='utf-8'))
            direct, total = lois_par_enumeration(4, 20)
            self.assertEqual(par_tranches['total'], total)
            self.assertEqual(par_tranches['laws'], direct)
        finally:
            shutil.rmtree(dossier)

    def test_reprise_apres_interruption(self):
        """Une interruption à mi-chemin ne doit ni perdre ni dupliquer de tranche."""
        dossier = Path(tempfile.mkdtemp())
        try:
            fini, message = construire_reprenable(3, 15, dossier, budget_s=0)
            self.assertFalse(fini)
            self.assertIn('reprendre', message)
            while not fini:
                fini, _ = construire_reprenable(3, 15, dossier, budget_s=0)
            d = json.loads((dossier / 'regime-3-15.json').read_text(encoding='utf-8'))
            self.assertEqual(d['total'], comb(15, 3))
            self.assertFalse((dossier / '.partiel-3-15').exists())   # nettoyé après fusion
        finally:
            shutil.rmtree(dossier)


class FaisabiliteTests(unittest.TestCase):
    def test_plafond(self):
        self.assertTrue(enumerable(6, 49))
        self.assertFalse(enumerable(16, 56))
        self.assertFalse(enumerable(20, 70))
        with self.assertRaises(ValueError):
            lois_par_enumeration(16, 56)


if __name__ == '__main__':
    unittest.main()
