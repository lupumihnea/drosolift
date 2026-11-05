"""Synthetic lamps depend on actual apparatus state, never render time."""

import unittest

from world.apparatus_feedback import apparatus_feedback
from world.equipment import ExerciseState


class ApparatusFeedbackTest(unittest.TestCase):
    def state(self, kind='bench_press', q=.2, phase='lifting'):
        return ExerciseState(station_id='station-1', kind=kind, joint_position=q, phase=phase)

    def test_task_bias_changes_sides_and_actual_travel_load_change_brightness(self):
        bench = apparatus_feedback('apparatus-visual-v1', self.state(), .6)
        curl = apparatus_feedback('apparatus-visual-v1', self.state('bicep_curl'), .6)
        self.assertGreater(bench.indicator_left, bench.indicator_right)
        self.assertGreater(curl.indicator_right, curl.indicator_left)
        self.assertEqual(bench.indicator_left, curl.indicator_right)
        high = apparatus_feedback('apparatus-visual-v1', self.state(q=.8), .6)
        heavy = apparatus_feedback('apparatus-visual-v1', self.state(), 1.2)
        self.assertGreater(high.indicator_left, bench.indicator_left)
        self.assertGreater(heavy.indicator_left, bench.indicator_left)
        for value in (bench.indicator_left, bench.indicator_right, high.indicator_left, heavy.indicator_left):
            self.assertTrue(0 <= value <= 1)

    def test_zero_travel_recovery_detached_and_disabled_are_defined(self):
        resting = apparatus_feedback('apparatus-visual-v1', self.state(q=0), .6)
        recovery = apparatus_feedback('apparatus-visual-v1', self.state(q=0, phase='recovery'), .6)
        self.assertGreater(resting.indicator_left, 0)
        self.assertLess(recovery.indicator_left, resting.indicator_left)
        for feedback in (apparatus_feedback('none', self.state(), .6),
                         apparatus_feedback('apparatus-visual-v1', ExerciseState(), .6)):
            self.assertEqual((0, 0), (feedback.indicator_left, feedback.indicator_right))
        with self.assertRaises(ValueError):
            apparatus_feedback('unknown', self.state(), .6)
