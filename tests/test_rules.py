"""Régression : la probabilité de la combinaison complète doit suivre la règle en
vigueur À LA DATE du tirage, pas la règle courante.

Les étoiles d'EuroMillions ont changé deux fois (9 → 11 le 10/05/2011, 11 → 12 le
27/09/2016). Un bug a longtemps appliqué C(12,2) à tous les tirages, donnant
1 sur 139 838 160 à des tirages de 2011 dont la vraie probabilité était
1 sur 116 531 800 — 940 tirages sur 1984 étaient faux.
"""
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from common import rule_main_total, rule_star_total  # noqa: E402

ATTENDU = {
    'euromillions-50-9-v1': 76275360,    # C(50,5) x C(9,2)  — jusqu'au 06/05/2011
    'euromillions-50-11-v1': 116531800,  # C(50,5) x C(11,2) — 10/05/2011 au 23/09/2016
    'euromillions-50-12-v1': 139838160,  # C(50,5) x C(12,2) — depuis le 27/09/2016
}


class RuleTests(unittest.TestCase):
    def test_totaux_par_regle(self):
        for rule, attendu in ATTENDU.items():
            self.assertEqual(rule_main_total(rule) * rule_star_total(rule), attendu, rule)

    def test_regle_inconnue_refusee(self):
        """Une règle non reconnue doit échouer bruyamment, pas retomber sur la
        règle courante — c'est ce silence qui avait laissé passer le bug."""
        for mauvais in ('', None, 'euromillions', 'loto-49-10-v1'):
            with self.assertRaises(ValueError):
                rule_star_total(mauvais)

    def test_facts_publies_coherents(self):
        """Chaque fichier de faits publié doit porter la probabilité de sa règle."""
        folder = ROOT / 'dist' / 'data' / 'facts'
        files = sorted(folder.glob('EM-*.json'))
        self.assertGreater(len(files), 100, 'faits non générés')
        for fp in files:
            d = json.loads(fp.read_text(encoding='utf-8'))
            fact = next(f for f in d['facts'] if f['fact_id'] == 'F.grid.probability')
            self.assertEqual(fact['value']['full_combinations'], ATTENDU[d['rule_id']],
                             f"{d['draw_id']} ({d['date']}, {d['rule_id']})")

    def test_cas_du_6_septembre_2011(self):
        """Cas exact du signalement : 5/50 + 2/11, pas 2/12."""
        d = json.loads((ROOT / 'dist' / 'data' / 'facts' / 'EM-2011053.json').read_text(encoding='utf-8'))
        self.assertEqual(d['date'], '2011-09-06')
        self.assertEqual(d['rule_id'], 'euromillions-50-11-v1')
        fact = next(f for f in d['facts'] if f['fact_id'] == 'F.grid.probability')
        self.assertEqual(fact['value']['full_combinations'], 116531800)
        # le libellé sépare les milliers par une espace fine insécable (U+202F)
        normalise = re.sub(r'[\s\u00a0\u202f]+', ' ', fact['statement'])
        self.assertIn('116 531 800', normalise)
        self.assertNotIn('139 838 160', normalise)


if __name__ == '__main__':
    unittest.main()
