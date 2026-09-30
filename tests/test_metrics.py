"""Métriques génériques : équivalence avec le laboratoire, et conventions de domaine.

Le test qui compte est le premier : pour EuroMillions, le module générique doit renvoyer
EXACTEMENT ce que renvoie le laboratoire. S'il diverge, les faits déjà publiés changent et
1 985 pages en ligne deviennent fausses sans qu'on l'ait voulu.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from metrics import coupure_basse, metriques, signature, tranches  # noqa: E402

LAB = Path(__file__).resolve().parents[2] / 'loto-keno-lab-generic' / 'src'


def facts_euromillions(limite=None):
    fichiers = sorted((ROOT / 'dist' / 'data' / 'facts').glob('EM-*.json'))
    return [json.loads(f.read_text(encoding='utf-8')) for f in (fichiers[:limite] if limite else fichiers)]


class EquivalenceLaboratoireTests(unittest.TestCase):
    def setUp(self):
        if not LAB.is_dir():
            self.skipTest('laboratoire absent')
        sys.path.insert(0, str(LAB))

    def test_metriques_principales_identiques(self):
        from lottery_games.euromillions.patterns import main_pattern
        tirages = facts_euromillions()
        self.assertGreater(len(tirages), 1900, 'faits non générés')
        for d in tirages:
            ref, mien = dict(main_pattern(d['main'])), metriques(d['main'], 50)
            for cle, attendu in ref.items():
                obtenu = mien[cle]
                if isinstance(attendu, (tuple, list)):
                    self.assertEqual(tuple(attendu), tuple(obtenu), f"{d['draw_id']}/{cle}")
                else:
                    self.assertEqual(attendu, obtenu, f"{d['draw_id']}/{cle}")

    def test_metriques_etoiles_identiques(self):
        """Les étoiles portent d'autres noms de champs : l'adaptateur doit coïncider."""
        from lottery_games.euromillions.patterns import stars_pattern
        for d in facts_euromillions():
            if d['rule_id'] != 'euromillions-50-12-v1':
                continue
            ref, m = dict(stars_pattern(d['stars'])), metriques(d['stars'], 12)
            self.assertEqual(ref['gap'], m['min_gap'], d['draw_id'])
            self.assertEqual(ref['consecutive'], m['consecutive_pairs'] > 0, d['draw_id'])
            self.assertEqual(ref['terminal_coincidence'], m['terminal_pair_collisions'] > 0, d['draw_id'])
            for cle in ('odd_count', 'even_count', 'low_count', 'high_count', 'sum'):
                self.assertEqual(ref[cle], m[cle], f"{d['draw_id']}/{cle}")


class ConventionsTests(unittest.TestCase):
    def test_tranches_par_domaine(self):
        """Tranches de dix, la dernière tronquée si le domaine ne tombe pas juste."""
        self.assertEqual(tranches(50), (1, 11, 21, 31, 41))
        self.assertEqual(tranches(49), (1, 11, 21, 31, 41))
        self.assertEqual(tranches(56), (1, 11, 21, 31, 41, 51))
        self.assertEqual(tranches(70), (1, 11, 21, 31, 41, 51, 61))

    def test_coupure_basse(self):
        self.assertEqual(coupure_basse(50), 25)   # identique à l'existant
        self.assertEqual(coupure_basse(49), 25)
        self.assertEqual(coupure_basse(56), 28)
        self.assertEqual(coupure_basse(70), 35)

    def test_domaine_respecte(self):
        with self.assertRaises(ValueError):
            metriques([1, 2, 50], 49)
        with self.assertRaises(ValueError):
            metriques([0, 2, 3], 49)
        with self.assertRaises(ValueError):
            metriques([5, 5, 7], 49)

    def test_selection_d_un_seul_numero(self):
        """Le numéro chance n'a ni écart ni étendue : les champs sont ABSENTS, pas nuls.
        Un zéro se comparerait à tort à un vrai écart nul."""
        m = metriques([7], 10)
        self.assertEqual(m['sum'], 7)
        for interdit in ('min_gap', 'max_gap', 'span', 'gaps', 'longest_consecutive_run'):
            self.assertNotIn(interdit, m)

    def test_keno_20_parmi_70(self):
        m = metriques(range(1, 21), 70)
        self.assertEqual(m['span'], 19)
        self.assertEqual(m['longest_consecutive_run'], 20)
        self.assertEqual(len(m['decade_counts']), 7)

    def test_signature_independante_du_jeu(self):
        self.assertEqual(signature(metriques([1, 2, 5, 11, 40], 50)),
                         'run=2;decade_max=3;decades=3')


if __name__ == '__main__':
    unittest.main()
