"""Les récurrences doivent reproduire exactement les lois énumérées sur de petits régimes."""
import unittest

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


if __name__ == '__main__':
    unittest.main()
