"""Budget and outcome regressions for the open-loop bench comparison."""
import unittest
from experiments.bench_comparison import matched_periodic, run_condition

class BenchComparisonTest(unittest.TestCase):
    def test_periodic_has_identical_commanded_positive_impulse_per_cycle(self):
        neural=(.1,.2,.4,.3,.15,.2,.35,.3)
        periodic=matched_periodic(neural)
        self.assertAlmostEqual(sum(neural),sum(periodic),places=12)
        self.assertTrue(all(0 <= value <= 1 for value in periodic))
        self.assertEqual((0.0,)*4,periodic[4:])

    def test_deterministic_repeats_preserve_every_mechanics_sample(self):
        a=run_condition((.3,)*20,load=.6,dt=.1,cycles=2)
        b=run_condition((.3,)*20,load=.6,dt=.1,cycles=2)
        self.assertEqual(a,b)

    def test_zero_command_has_no_positive_work_or_completed_repetitions(self):
        result=run_condition((0.0,)*20,load=.6,dt=.1,cycles=2)
        self.assertEqual(0,result['summary']['positive_work'])
        self.assertEqual(0,result['summary']['repetitions'])

    def test_heavier_load_changes_mechanics_under_identical_frozen_drive(self):
        light=run_condition((.3,)*10,load=.4,dt=.1,cycles=1)
        heavy=run_condition((.3,)*10,load=1.2,dt=.1,cycles=1)
        self.assertGreater(light['summary']['maximum_travel'],heavy['summary']['maximum_travel'])
        self.assertEqual(light['summary']['commanded_positive_impulse'],heavy['summary']['commanded_positive_impulse'])

    def test_maximum_travel_includes_top_stop_between_saved_samples(self):
        result=run_condition((.3,)*60,load=.8,dt=.1,cycles=1)
        self.assertGreater(result['summary']['repetitions'],0)
        self.assertEqual(.7,result['summary']['maximum_travel'])
