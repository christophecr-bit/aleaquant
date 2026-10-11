"""Verify the browser viewer against the independent Python prompter oracle.

Node evaluates the pure helpers only. No DOM, browser, source-grid write, or
simulation is needed for this bounded regression suite.
"""

import importlib.util
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / 'dist' / 'portefeuilles' / 'portfolio-viewer.js'
PROMPTER = ROOT.parent / 'loto-keno-lab-generic' / 'src' / 'lottery_ui' / 'prompter.py'
DATASET = ROOT / 'dist' / 'data' / 'portfolio_pipeline.json'

# Pass arguments through stdin: source data is never interpolated into code.
NODE_RUNNER = r'''
const fs = require('node:fs');
require(process.argv[1]);
const api = globalThis.AleaQuantPortfolioViewer;
if (!api) throw new Error('Viewer API is unavailable');
const calls = JSON.parse(fs.readFileSync(0, 'utf8'));
const results = calls.map(({method, args}) => {
  const before = JSON.stringify(args);
  try {
    const value = api[method](...args);
    return {value, mutated: JSON.stringify(args) !== before};
  } catch (error) {
    return {error: error.name, mutated: JSON.stringify(args) !== before};
  }
});
process.stdout.write(JSON.stringify(results));
'''


class PortfolioViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which('node')
        if not cls.node:
            raise unittest.SkipTest('Node is required to check the browser helpers')
        spec = importlib.util.spec_from_file_location('portfolio_viewer_prompter_oracle', PROMPTER)
        cls.oracle = importlib.util.module_from_spec(spec)
        # dataclasses resolve their annotation module while executing the source.
        sys.modules[spec.name] = cls.oracle
        spec.loader.exec_module(cls.oracle)
        cls.dataset = json.loads(DATASET.read_text())

    def run_calls(self, calls):
        result = subprocess.run(
            [self.node, '-e', NODE_RUNNER, str(VIEWER)],
            input=json.dumps(calls), text=True, capture_output=True,
            check=True, timeout=15,
        )
        return json.loads(result.stdout)

    def assert_valid(self, result, expected):
        self.assertNotIn('error', result)
        self.assertFalse(result['mutated'], 'Viewer helper mutated its inputs')
        self.assertEqual(result['value'], expected)

    def test_all_imported_grids_match_the_python_number_board(self):
        calls, expected, labels = [], [], []
        total = 0
        for profile in self.dataset['profiles']:
            self.assertEqual(profile['rule_id'], 'euromillions-50-12-v1')
            self.assertEqual(profile['grid_count'], len(profile['grids']))
            total += len(profile['grids'])
            for index, (main, stars) in enumerate(profile['grids']):
                for component, chosen, maximum, columns in (
                    ('main', main, 50, 10), ('stars', stars, 12, 6),
                ):
                    values = list(range(1, maximum + 1))
                    calls.append({'method': 'numberRows', 'args': [values, chosen, columns]})
                    rows = self.oracle.number_grid_rows(values, chosen, columns)
                    expected.append([[{'value': cell.value, 'selected': cell.selected}
                                      for cell in row] for row in rows])
                    labels.append((profile['id'], index + 1, component))
        self.assertEqual(total, 118)
        results = self.run_calls(calls)
        self.assertEqual(len(results), len(expected))
        for label, result, rows in zip(labels, results, expected):
            with self.subTest(profile=label[0], grid=label[1], component=label[2]):
                self.assert_valid(result, rows)
                cells = [cell for row in result['value'] for cell in row]
                self.assertEqual(len(cells), 50 if label[2] == 'main' else 12)
                self.assertEqual(sum(cell['selected'] for cell in cells),
                                 5 if label[2] == 'main' else 2)

    def test_groups_match_python_for_singleton_incomplete_and_large_portfolios(self):
        calls, expected = [], []
        for total in (1, 18, 20, 22, 30, 31):
            groups = (total + 5) // 6
            for index in range(groups):
                window = self.oracle.group_window(total, index)
                expected.append({'index': window.index, 'count': window.count,
                                 'start': window.start, 'stop': window.stop})
                calls.append({'method': 'groupWindow', 'args': [total, index]})
        for result, window in zip(self.run_calls(calls), expected):
            with self.subTest(window=window):
                self.assert_valid(result, window)
                self.assertGreater(window['stop'], window['start'])
                self.assertLessEqual(window['stop'] - window['start'], 6)
        # Explicit boundaries exercise groups shorter than six and the 31st grid.
        last = self.run_calls([
            {'method': 'groupWindow', 'args': [20, 3]},
            {'method': 'groupWindow', 'args': [22, 3]},
            {'method': 'groupWindow', 'args': [31, 5]},
        ])
        self.assertEqual([(r['value']['start'], r['value']['stop']) for r in last],
                         [(18, 20), (18, 22), (30, 31)])

    def test_explicit_group_sizes_match_the_python_oracle(self):
        calls, expected = [], []
        for total, size in ((1, 1), (18, 4), (31, 7)):
            for index in range((total + size - 1) // size):
                window = self.oracle.group_window(total, index, size)
                calls.append({'method': 'groupWindow', 'args': [total, index, size]})
                expected.append({'index': window.index, 'count': window.count,
                                 'start': window.start, 'stop': window.stop})
        for result, window in zip(self.run_calls(calls), expected):
            self.assert_valid(result, window)

    def test_number_board_rejects_malformed_domains_selections_and_columns(self):
        arguments = [
            [[], [], 2], [[2, 1], [], 2], [[1, 1], [], 2],
            [[1, '2'], [], 2], [[True, 2], [], 2], [[1, 2.5], [], 2],
            [None, [], 2], ['12', [], 2],
            [[1, 2], [3], 2], [[1, 2], [True], 2],
            [[1, 2], ['1'], 2], [[1, 2], [1.5], 2],
            [[1, 2], None, 2], [[1, 2], '1', 2],
        ]
        arguments += [[[1, 2], [1], columns]
                      for columns in (True, 0, -1, 1.5, '2', None)]
        calls = [{'method': 'numberRows', 'args': args} for args in arguments]
        for args, result in zip(arguments, self.run_calls(calls)):
            with self.subTest(args=args):
                self.assertIn('error', result)
                self.assertFalse(result['mutated'])

    def test_group_window_rejects_invalid_types_and_out_of_range_indices(self):
        arguments = [[total, 0] for total in (True, 0, -1, 1.5, '18', None)]
        arguments += [[18, index] for index in (True, -1, 3, 1.5, '0', None)]
        arguments += [[18, 0, size] for size in (True, 0, -1, 1.5, '6', None)]
        calls = [{'method': 'groupWindow', 'args': args} for args in arguments]
        for args, result in zip(arguments, self.run_calls(calls)):
            with self.subTest(args=args):
                self.assertIn('error', result)
                self.assertFalse(result['mutated'])

    def test_board_supports_empty_selection_without_mutating_source_order(self):
        arguments = [[[1, 2, 3], [], 2], [[1, 2, 3], [3, 1], 2],
                     [[1, 2, 3], [1, 1, 3], 2]]
        results = self.run_calls([{'method': 'numberRows', 'args': args}
                                  for args in arguments])
        for args, result in zip(arguments, results):
            rows = self.oracle.number_grid_rows(*args)
            self.assert_valid(result, [[{'value': cell.value, 'selected': cell.selected}
                                        for cell in row] for row in rows])


if __name__ == '__main__':
    unittest.main()
