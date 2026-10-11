"""Parité de l'Atlas publié et cas limites du calcul partagé de géométrie.

Version : 0.1 | Date : 2026-10-09 | Auteur : AleaQuant
Historique : extraction de build_data.py pour l'intégration du pipeline.
TODO : ajouter une cohorte de référence lors d'un nouveau format de grille.
"""
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
from portfolio_geometry import portfolio_geometry  # noqa: E402


class PortfolioGeometryTests(unittest.TestCase):
    def test_three_grids_with_known_intersections(self):
        grids = [
            [[1, 2, 3, 4, 5], [1, 2]],
            [[1, 2, 3, 6, 7], [2, 3]],
            [[1, 4, 8, 9, 10], [1, 2]],
        ]
        geometry = portfolio_geometry(grids, 10)
        self.assertEqual(geometry['grids'], 3)
        self.assertEqual(geometry['union'], 10)
        self.assertEqual(geometry['overlap_mean'], 2)
        self.assertEqual(geometry['overlap_max'], 3)
        self.assertEqual(geometry['overlap_hist'], [0, 1, 1, 1, 0, 0])
        self.assertEqual(geometry['coverage'][2],
                         {'covered': 26, 'possible': 45, 'collisions': 4})
        self.assertEqual(geometry['coverage'][3],
                         {'covered': 29, 'possible': 120, 'collisions': 1})
        self.assertAlmostEqual(geometry['occurrence_sd'], math.sqrt(0.45))
        self.assertEqual(geometry['second'], {
            'union': 3, 'overlap_mean': 4 / 3, 'overlap_max': 2,
            'distinct_combinations': 2,
        })

    def test_repeated_subset_collisions_count_pairs_of_occurrences(self):
        # Chaque paire et chaque triplet apparaît dans les trois grilles :
        # C(3,2) collisions par sous-ensemble, et non simplement 3 - 1.
        grids = [[[1, 2, 3]], [[1, 2, 3]], [[1, 2, 3]]]
        geometry = portfolio_geometry(grids, 4)
        self.assertEqual(geometry['coverage'][2],
                         {'covered': 3, 'possible': 6, 'collisions': 9})
        self.assertEqual(geometry['coverage'][3],
                         {'covered': 1, 'possible': 4, 'collisions': 3})
        self.assertEqual(geometry['overlap_hist'], [0, 0, 0, 3])
        self.assertNotIn('second', geometry)

    def test_single_grid_has_no_pairwise_overlap(self):
        geometry = portfolio_geometry([[[1, 2, 3, 4, 5], [2, 3]]], 50)
        self.assertIsNone(geometry['overlap_mean'])
        self.assertIsNone(geometry['overlap_max'])
        self.assertEqual(geometry['overlap_hist'], [0] * 6)
        self.assertEqual(geometry['coverage'][2]['covered'], 10)
        self.assertEqual(geometry['coverage'][3]['covered'], 10)
        self.assertEqual(geometry['coverage'][2]['collisions'], 0)
        self.assertEqual(geometry['coverage'][3]['collisions'], 0)
        self.assertIsNone(geometry['second']['overlap_mean'])
        self.assertIsNone(geometry['second']['overlap_max'])
        self.assertEqual(geometry['second']['union'], 2)
        self.assertEqual(geometry['second']['distinct_combinations'], 1)

    def test_empty_portfolio_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'au moins une grille'):
            portfolio_geometry([], 50)

    def test_existing_atlas_cohorts_remain_identical(self):
        atlas = json.loads((ROOT / 'dist' / 'data' / 'atlas.json').read_text())
        self.assertEqual([cohort['game'] for cohort in atlas['portfolios']],
                         ['euromillions', 'keno', 'loto'])
        self.assertEqual([len(cohort['items']) for cohort in atlas['portfolios']],
                         [35, 11, 5])
        for cohort in atlas['portfolios']:
            for item in cohort['items']:
                with self.subTest(game=cohort['game'], portfolio=item['id']):
                    calculated = portfolio_geometry(item['grids'], cohort['domain'])
                    # La sérialisation convertit les clés numériques de coverage.
                    projection = json.loads(json.dumps(calculated))
                    self.assertEqual(projection, item['geometry'])


if __name__ == '__main__':
    unittest.main()
