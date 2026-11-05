"""Recording must retain exact observed IDs, clocks and physical counters."""

import csv
from copy import deepcopy
import io
import json
import math
from pathlib import Path
import unittest

from brain.gym_circuit import load_gym_circuits
from experiments.record_gym import record_gym, recording_csv


ROOT = Path(__file__).resolve().parents[1]


def assert_portable_recording(testcase: unittest.TestCase, expected: object,
                              actual: object, path: tuple[str | int, ...] = ()) -> None:
    """Allow platform rounding only for continuous neural, motor and body values.

    The Linux CI fixture comparison exposed a ~4.4e-16 motor-readout difference.
    Use abs_tol=rel_tol=1e-12 for finite continuous values, without modifying the
    recorded payload. Keys, ordered shapes, types, identities, counters and the
    authoritative model clock remain exact (including recovery's countdown).
    """
    location = '$' + ''.join(f'[{part}]' if type(part) is int else f'.{part}' for part in path)
    testcase.assertIs(type(actual), type(expected), f'{location}: JSON value type changed')
    if type(expected) is dict:
        testcase.assertEqual(expected.keys(), actual.keys(), f'{location}: JSON keys changed')
        for key in expected:
            assert_portable_recording(testcase, expected[key], actual[key], (*path, key))
    elif type(expected) is list:
        testcase.assertEqual(len(expected), len(actual), f'{location}: list length changed')
        for index, (left, right) in enumerate(zip(expected, actual, strict=True)):
            assert_portable_recording(testcase, left, right, (*path, index))
    elif type(expected) is float:
        testcase.assertTrue(math.isfinite(expected) and math.isfinite(actual),
                            f'{location}: nonfinite continuous value')
        exact_fields = {'step', 'elapsed', 'sample_step', 'sample_elapsed', 'index', 'frame_index',
                        'recovery_remaining', 'body_id', 'schema', 'sets', 'repetitions',
                        'completed_sets', 'rep_in_set', 'active_kcs'}
        continuous_domains = {'neural', 'motor', 'body', 'food', 'hunger', 'sensory', 'trail',
                              'learning', 'training', 'exercise'}
        if path and path[-1] not in exact_fields and any(part in continuous_domains for part in path):
            testcase.assertTrue(math.isclose(expected, actual, abs_tol=1e-12, rel_tol=1e-12),
                f'{location}: {expected!r} != {actual!r}; absolute error {abs(expected - actual):.17g} '
                '(abs/rel tolerance 1e-12)')
        else:
            testcase.assertEqual(expected, actual, f'{location}: exact clock/metadata changed')
    else:
        testcase.assertEqual(expected, actual, f'{location}: exact value changed')


class PortableRecordingComparisonTest(unittest.TestCase):
    def setUp(self):
        self.expected = {'schema': 3, 'step': 1, 'elapsed': .1, 'index': 0, 'flies': [
            {'id': 'fly-1', 'frame': {'ate': False, 'body': {'x': -6.4},
                'motor': {'forward': .5}, 'neural': {'active': [
                    {'body_id': 10783, 'activity': .25}, {'body_id': 10030, 'activity': 0.0}]}},
             'training': {'sets': 0}, 'exercise': {'repetitions': 2, 'recovery_remaining': .1}}]}

    def test_one_ulp_rounding_of_continuous_measurements_is_permitted(self):
        actual = deepcopy(self.expected)
        actual['flies'][0]['frame']['neural']['active'][0]['activity'] = math.nextafter(.25, math.inf)
        actual['flies'][0]['frame']['motor']['forward'] = math.nextafter(.5, math.inf)
        actual['flies'][0]['frame']['body']['x'] = math.nextafter(-6.4, math.inf)
        assert_portable_recording(self, self.expected, actual)

    def test_id_counter_schema_string_and_boolean_changes_are_rejected(self):
        variants = []
        for field, value in [('body_id', 10038), ('body_id', 10783.0)]:
            changed = deepcopy(self.expected)
            changed['flies'][0]['frame']['neural']['active'][0][field] = value
            variants.append(changed)
        for target, field, value in [
                ('exercise', 'repetitions', 3), ('exercise', 'repetitions', 2.0),
                ('training', 'sets', 1), ('frame', 'ate', 0)]:
            changed = deepcopy(self.expected)
            changed['flies'][0][target][field] = value
            variants.append(changed)
        changed = deepcopy(self.expected)
        changed['flies'][0]['id'] = 'fly-2'
        variants.append(changed)
        variants.append(dict(self.expected, schema=4))
        for actual in variants:
            with self.subTest(actual=actual), self.assertRaises(AssertionError):
                assert_portable_recording(self, self.expected, actual)

    def test_missing_extra_keys_changed_list_shape_and_order_are_rejected(self):
        missing = deepcopy(self.expected)
        del missing['flies'][0]['frame']['motor']
        extra = deepcopy(self.expected)
        extra['flies'][0]['frame']['motor']['unexpected'] = 0.0
        shorter = deepcopy(self.expected)
        shorter['flies'][0]['frame']['neural']['active'].pop()
        reordered = deepcopy(self.expected)
        reordered['flies'][0]['frame']['neural']['active'].reverse()
        for actual in (missing, extra, shorter, reordered):
            with self.subTest(actual=actual), self.assertRaises(AssertionError):
                assert_portable_recording(self, self.expected, actual)

    def test_authoritative_clocks_and_frame_indices_remain_exact(self):
        for field, value in [('elapsed', math.nextafter(.1, math.inf)), ('step', 2), ('index', 1)]:
            with self.subTest(field=field), self.assertRaises(AssertionError):
                assert_portable_recording(self, self.expected, dict(self.expected, **{field: value}))
        actual = deepcopy(self.expected)
        actual['flies'][0]['exercise']['recovery_remaining'] = math.nextafter(.1, math.inf)
        with self.assertRaises(AssertionError):
            assert_portable_recording(self, self.expected, actual)

    def test_material_activity_changes_and_nonfinite_values_are_rejected(self):
        for value in (.250001, float('nan'), float('inf'), float('-inf')):
            actual = deepcopy(self.expected)
            actual['flies'][0]['frame']['neural']['active'][0]['activity'] = value
            with self.subTest(value=value), self.assertRaises(AssertionError):
                assert_portable_recording(self, self.expected, actual)


class GymRecordingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuits = load_gym_circuits(ROOT)

    def test_roundtrip_preserves_ids_timestamps_equipment_and_repetitions(self):
        recorded = record_gym(ROOT, duration=2, dt=.1, load=.6, seed=7,
                              learning_enabled=False, circuits=self.circuits)
        replay = json.loads(json.dumps(recorded, allow_nan=False))
        self.assertEqual(recorded, replay)
        self.assertEqual(21, len(replay['frames']))
        self.assertEqual(0, replay['frames'][0]['step'])
        self.assertEqual(20, replay['frames'][-1]['step'])
        self.assertAlmostEqual(2, replay['frames'][-1]['elapsed'])
        ids = set(replay['metadata']['model_scope']['body_ids'])
        for frame in replay['frames']:
            self.assertEqual(ids, {reading['body_id'] for reading in frame['flies'][0]['frame']['neural']['active']})
        rows = list(csv.DictReader(io.StringIO(recording_csv(replay))))
        self.assertEqual(len(replay['frames']), len(rows))
        for frame, row in zip(replay['frames'], rows, strict=True):
            fly = frame['flies'][0]
            self.assertEqual(frame['step'], int(row['step']))
            self.assertEqual(frame['elapsed'], float(row['elapsed']))
            self.assertEqual(fly['exercise']['repetitions'], int(row['repetitions']))
            self.assertEqual(fly['exercise']['joint_position'], float(row['joint_position']))

    def test_fresh_seeded_runs_reproduce_observations_without_persistent_memory(self):
        options = dict(duration=1, dt=.1, load=.9, seed=7, learning_enabled=False,
                       circuits=self.circuits)
        first = record_gym(ROOT, **options)
        second = record_gym(ROOT, **options)
        self.assertNotEqual(first['metadata']['run_id'], second['metadata']['run_id'])
        self.assertEqual(first['frames'], second['frames'])

    def test_invalid_sampling_inputs_are_rejected(self):
        options = dict(duration=1, dt=.1, load=.6, seed=7, learning_enabled=False,
                       circuits=self.circuits)
        for changes in ({'dt': 0}, {'duration': float('nan')}, {'load': True},
                        {'duration': 1.05}, {'seed': True}):
            with self.assertRaises(ValueError):
                record_gym(ROOT, **(options | changes))

    def test_profile_recording_retains_actual_feedback_next_to_same_step_rates(self):
        recorded = record_gym(ROOT, duration=2, dt=.1, load=.4, seed=7,
                              learning_enabled=False, circuits=self.circuits,
                              exercise='bicep_curl', feedback='apparatus-visual-v1')
        self.assertEqual('apparatus-visual-v1', recorded['metadata']['feedback_profile'])
        self.assertEqual('bicep_curl', recorded['metadata']['exercise'])
        self.assertEqual('station-2', recorded['frames'][0]['flies'][0]['exercise']['station_id'])
        for frame, controls in zip(recorded['frames'], recorded['metadata']['control_history'], strict=True):
            self.assertEqual((frame['step'], frame['elapsed']), (controls['step'], controls['elapsed']))
            feedback = controls['feedback'][0]
            self.assertEqual(frame['step'], feedback['sample_step'])
            if frame['step']:
                self.assertEqual(feedback['indicator_right'], frame['flies'][0]['frame']['sensory']['vision_right'])

    def test_none_profile_reproduces_original_bundled_calibration_frames(self):
        original = json.loads((ROOT / 'frontend/web/public/samples/bench.json').read_text(encoding='utf-8'))
        recorded = record_gym(ROOT, duration=20, dt=.1, load=.6, seed=7,
                              learning_enabled=False, circuits=self.circuits)
        assert_portable_recording(self, original['frames'], recorded['frames'], ('frames',))
