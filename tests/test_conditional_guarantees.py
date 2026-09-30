"""Certificats de garanties conditionnelles sur les numéros principaux."""

import sys
import unittest
from itertools import combinations
from hashlib import sha256
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from conditional_guarantees import (  # noqa: E402
    counting_lower_bound, greedy_upper_bound, verify_wheel,
)


class ConditionalGuaranteeTests(unittest.TestCase):
    def test_certificat_et_contre_exemple(self):
        full = verify_wheel((1, 2, 3, 4), ((1, 2), (3, 4)), 2)
        self.assertEqual(full['scenarios'], 6)
        self.assertEqual(full['worst_best_hits'], 1)
        self.assertEqual(full['worst_case'], [1, 3])
        self.assertEqual(full['minimum_grids_at_least_hits']['1'], 1)

        incomplete = verify_wheel((1, 2, 3, 4), ((1, 2),), 2)
        self.assertEqual(incomplete['worst_best_hits'], 0)
        self.assertEqual(incomplete['worst_case'], [3, 4])

    def test_loto_pool_10_3_if_4_et_borne_impossible_a_25(self):
        result = greedy_upper_bound(10, 5, 4, 3)
        self.assertEqual(result['lower_bound'], 4)
        self.assertLessEqual(result['upper_bound'], 25)
        self.assertEqual(result['upper_bound'], len(result['grids']))
        self.assertEqual(result['proof']['scenarios'], 210)
        self.assertGreaterEqual(result['proof']['worst_best_hits'], 3)
        self.assertFalse(result['optimality_proven'])
        self.assertEqual(counting_lower_bound(10, 5, 4, 4), 42)

        # Vérification indépendante de l'énoncé sur chaque scénario, sans
        # reprendre le calcul interne du certificat.
        for scenario in combinations(range(1, 11), 4):
            self.assertTrue(any(len(set(grid).intersection(scenario)) >= 3
                                for grid in result['grids']))

    def test_renommage_du_pool_et_limites(self):
        original = verify_wheel((1, 2, 3, 4), ((1, 2), (3, 4)), 2)
        renamed = verify_wheel((11, 12, 13, 14), ((11, 12), (13, 14)), 2)
        self.assertEqual(original['worst_best_hits'], renamed['worst_best_hits'])
        self.assertEqual(original['minimum_grids_at_least_hits'],
                         renamed['minimum_grids_at_least_hits'])
        with self.assertRaisesRegex(ValueError, 'scénarios dépassent'):
            verify_wheel(range(1, 11), ((1, 2, 3, 4, 5),), 4, max_scenarios=100)
        with self.assertRaisesRegex(ValueError, 'grilles répétées'):
            verify_wheel((1, 2, 3), ((1, 2), (2, 1)), 2)
        with self.assertRaisesRegex(ValueError, 'recherche dépassant'):
            greedy_upper_bound(20, 5, 4, 3)

    def test_solution_exacte_archivee_est_certifiee(self):
        artifact = json.loads((Path(__file__).resolve().parents[1] / 'docs/research'
                               / 'conditional-wheel-10-5-4-3.json').read_text())
        self.assertEqual(artifact['minimum_grid_count'], 7)
        self.assertTrue(artifact['optimality_proven_by_solver'])
        self.assertEqual(artifact['solver_lower_bound'], 7)
        self.assertEqual(artifact['solver_gap'], 0)
        self.assertEqual(artifact['grids_sha256'], sha256(json.dumps(
            artifact['grids'], separators=(',', ':')).encode()).hexdigest())
        certificate = verify_wheel(range(1, 11), artifact['grids'], 4)
        self.assertEqual(certificate['worst_best_hits'], 3)
        self.assertEqual(certificate['scenarios'], 210)
        for index in range(len(artifact['grids'])):
            reduced = artifact['grids'][:index] + artifact['grids'][index + 1:]
            self.assertLess(verify_wheel(range(1, 11), reduced, 4)['worst_best_hits'], 3)


if __name__ == '__main__':
    unittest.main()
