"""Contrôle indépendant des moments théoriques sur de petits univers exhaustifs."""
from fractions import Fraction
from itertools import combinations
from math import comb
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from order_position_covariance import report, span_moments, theoretical_moments
from laws_recurrence import _etendue


class OrderPositionCovarianceTests(unittest.TestCase):
    def test_every_matrix_entry_matches_exhaustive_small_regimes(self):
        for k, n in ((2, 5), (3, 7), (4, 9), (5, 10)):
            with self.subTest(k=k, n=n):
                draws = list(combinations(range(1, n + 1), k))
                total = len(draws)
                mean, covariance = theoretical_moments(k, n)
                empirical_mean = tuple(Fraction(sum(row[i] for row in draws), total)
                                       for i in range(k))
                empirical_covariance = tuple(tuple(
                    sum((row[i] - mean[i]) * (row[j] - mean[j]) for row in draws) / total
                    for j in range(k)) for i in range(k))
                self.assertEqual(mean, empirical_mean)
                self.assertEqual(covariance, empirical_covariance)

    def test_span_matches_independent_exact_law(self):
        for k, n in ((2, 5), (3, 9), (5, 10), (5, 50), (16, 56)):
            with self.subTest(k=k, n=n):
                mean, covariance = theoretical_moments(k, n)
                span_mean, span_variance = span_moments(mean, covariance)
                law = _etendue(k, n)
                total = comb(n, k)
                from_law = Fraction(sum(value * count for value, count in law.items()), total)
                variance_from_law = sum(
                    (value - from_law) ** 2 * count for value, count in law.items()) / total
                self.assertEqual(span_mean, from_law)
                self.assertEqual(span_variance, variance_from_law)

    def test_regime_is_required_and_theory_has_no_historical_window(self):
        with self.assertRaises(ValueError):
            theoretical_moments(1, 50)
        self.assertEqual(report('euromillions', 5, 50)['span_variance'], '510/7')
        self.assertEqual(report('loto', 5, 49)['game_id'], 'loto')
        self.assertEqual(report('keno', 16, 56)['component'], 'main')
        self.assertNotIn('history', report('euromillions', 5, 50))
        with self.assertRaises(ValueError):
            report('unknown', 5, 50)
        with self.assertRaises(ValueError):
            report('loto', 5, 50)


if __name__ == '__main__':
    unittest.main()
