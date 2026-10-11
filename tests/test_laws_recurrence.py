"""Les récurrences doivent reproduire exactement les lois énumérées sur de petits régimes."""
import unittest
from math import comb

from laws import lois_par_enumeration
from laws_recurrence import lois_par_recurrence


class RecurrenceLawsTest(unittest.TestCase):
    def test_exact_small_regimes(self):
        for k, n in ((2, 5), (3, 9), (4, 12), (5, 13), (6, 16)):
            with self.subTest(k=k, n=n):
                got, total, missing = lois_par_recurrence(k, n)
                expected, expected_total = lois_par_enumeration(k, n)
                self.assertEqual(total, expected_total)
                self.assertEqual(set(expected) - set(missing), set(got))
                for field, law in got.items():
                    self.assertEqual(law, expected[field], field)

    def test_sorted_gaps_exact_small_regimes(self):
        for k, n in ((2, 5), (3, 9), (4, 12), (5, 13), (6, 16)):
            with self.subTest(k=k, n=n):
                got, total, missing = lois_par_recurrence(k, n)
                expected, _ = lois_par_enumeration(k, n)
                self.assertNotIn('sorted_gaps', missing)
                self.assertEqual(got['sorted_gaps'], expected['sorted_gaps'])
                self.assertEqual(sum(got['sorted_gaps'].values()), total)

    def test_close_pairs_large_regimes_first_moment(self):
        # Chaque paire (a,b) à distance <= 5 apparaît dans C(n-2,k-2)
        # sélections ; ce contrôle ne dépend pas de la récurrence par masque.
        for k, n in ((16, 56), (20, 70)):
            with self.subTest(k=k, n=n):
                got, total, missing = lois_par_recurrence(k, n)
                law = got['clusteredness_close_pairs_5']
                self.assertNotIn('clusteredness_close_pairs_5', missing)
                self.assertEqual(sum(law.values()), total)
                expected = sum(n - d for d in range(1, 6)) * comb(n - 2, k - 2)
                self.assertEqual(sum(int(v) * count for v, count in law.items()),
                                 expected)


if __name__ == '__main__':
    unittest.main()
