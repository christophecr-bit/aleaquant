"""Échantillonnage rétrospectif séparé par jeu et règle, sans toucher aux archives."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from order_position_history import historical_report, rule_main_regime, sample_moments


class OrderPositionHistoryTests(unittest.TestCase):
    def test_rule_formats_and_sample_denominator(self):
        legacy = {'game': {'draw': [{'component': 'main', 'count': 5}],
                           'components': [{'name': 'main', 'low': 1, 'high': 50,
                                           'replacement': False}]}}
        self.assertEqual(rule_main_regime(legacy), (5, 50))
        self.assertEqual(rule_main_regime({'picks': {'main': 16},
                                           'domains': {'main': 56}}), (16, 56))
        mean, covariance = sample_moments([(2, 3, 4), (4, 5, 6)])
        self.assertEqual(tuple(map(str, mean)), ('3', '4', '5'))
        self.assertEqual(covariance[0][2], 2)

    def test_latest_revisions_windows_and_games_stay_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'draws.sqlite3'
            conn = sqlite3.connect(path)
            conn.executescript('''CREATE TABLE rules(id TEXT PRIMARY KEY, body TEXT);
                CREATE TABLE revisions(game TEXT, draw_id TEXT, revision INTEGER,
                    body TEXT, sha TEXT, PRIMARY KEY(game, draw_id, revision));''')
            rules = {
                'em': {'rule_id': 'em', 'game_id': 'euromillions',
                       'picks': {'main': 5}, 'domains': {'main': 50}},
                'lo': {'rule_id': 'lo', 'game_id': 'loto',
                       'picks': {'main': 5}, 'domains': {'main': 49}},
            }
            for rule_id, rule in rules.items():
                conn.execute('INSERT INTO rules VALUES(?, ?)', (rule_id, json.dumps(rule)))

            def insert(game, draw_id, revision, date, values, rule_id):
                body = {'game_id': game, 'draw_id': draw_id, 'occurred_on': date,
                        'rule_id': rule_id, 'values': [['main', values]]}
                conn.execute('INSERT INTO revisions VALUES(?, ?, ?, ?, ?)',
                             (game, draw_id, revision, json.dumps(body),
                              f'{game}-{draw_id}-r{revision}'))

            insert('euromillions', 'E1', 1, '2026-01-01', [1, 2, 3, 4, 5], 'em')
            insert('euromillions', 'E1', 2, '2026-01-01', [2, 3, 4, 5, 6], 'em')
            insert('euromillions', 'E2', 1, '2026-02-01', [4, 5, 6, 7, 8], 'em')
            insert('loto', 'L1', 1, '2026-01-02', [1, 3, 5, 7, 9], 'lo')
            insert('loto', 'L2', 1, '2026-02-02', [2, 4, 6, 8, 10], 'lo')
            conn.commit()
            conn.close()

            result = historical_report(path)
            groups = {g['game_id']: g for g in result['groups']}
            self.assertEqual({key: g['draw_count'] for key, g in groups.items()},
                             {'euromillions': 2, 'loto': 2})
            self.assertEqual(groups['euromillions']['mean'][0], '3')
            self.assertEqual(groups['euromillions']['covariance'][0][0], '2')
            self.assertEqual(groups['euromillions']['span_variance'], '0')
            self.assertNotEqual(groups['euromillions']['revisions_sha256'],
                                groups['loto']['revisions_sha256'])
            early = historical_report(path, end_date='2026-01-02')
            self.assertEqual([g['draw_count'] for g in early['groups']], [1, 1])
            self.assertTrue(all(g['covariance'] is None for g in early['groups']))
            with self.assertRaises(ValueError):
                historical_report(path, end_date='2026-13-01')


if __name__ == '__main__':
    unittest.main()
