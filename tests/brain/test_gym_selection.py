"""Bounded raw-data selection preserves order, duplicates and exact filters."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pyarrow as pa
import pyarrow.feather as feather

from brain.gym_selection import Edge, WeightScanner


class WeightScannerTest(unittest.TestCase):
    def test_batched_selector_matches_hydrated_source_rows_without_full_hydration(self):
        rows = [(1, 8, 9), (1, 9, 12), (2, 8, 20), (7, 3, 30),
                (1, 9, 12), (4, 2, 10), (7, 2, 4)]
        table = pa.table({name: [row[index] for row in rows]
                          for index, name in enumerate(('body_pre', 'body_post', 'weight'))})
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'weights.feather'
            feather.write_feather(table, path, chunksize=2)
            with patch('pyarrow.feather.read_table', side_effect=AssertionError('full hydration')):
                scanner = WeightScanner(path)
                for filters in ({'pre_ids': {1}}, {'post_ids': {8}},
                                {'pre_ids': {1, 4}, 'post_ids': {9, 2}},
                                {'pre_ids': {1}, 'minimum_weight': 0},
                                {'pre_ids': set()}, {'post_ids': set()}):
                    expected = [Edge(*row) for row in rows
                                if row[2] >= filters.get('minimum_weight', 10)
                                and ('pre_ids' not in filters or row[0] in filters['pre_ids'])
                                and ('post_ids' not in filters or row[1] in filters['post_ids'])]
                    self.assertEqual(expected, scanner.select(**filters))
                with self.assertRaises(ValueError):
                    scanner.select()
            self.assertTrue(scanner.table.equals(table))
