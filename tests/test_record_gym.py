"""Recording must retain exact observed IDs, clocks and physical counters."""

import csv
import io
import json
from pathlib import Path
import unittest

from brain.gym_circuit import load_gym_circuits
from experiments.record_gym import record_gym, recording_csv


ROOT = Path(__file__).resolve().parents[1]


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
        self.assertEqual(original['frames'], recorded['frames'])
