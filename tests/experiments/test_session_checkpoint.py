"""A restart must preserve future model behavior, not merely displayed counters."""

import copy
import json
from pathlib import Path
import unittest

from brain.gym_circuit import load_gym_circuits
from experiments.experiment_002 import create_gym
from experiments.session_checkpoint import CheckpointValidationError, restore, snapshot


ROOT = Path(__file__).resolve().parents[2]


class SessionCheckpointTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuits = load_gym_circuits(ROOT)

    def make(self, **options):
        return create_gym(*self.circuits, seed=7, **options)

    def roundtrip(self, original):
        document = json.loads(json.dumps(snapshot(original), allow_nan=False))
        restored = self.make()
        restore(restored, document)
        self.assertEqual(original.snapshot(), restored.snapshot())
        self.assertEqual(snapshot(original), snapshot(restored))
        return restored

    def assert_future(self, original, restored, count=240):
        for index in range(count):
            dt = (.03, .1, .17)[index % 3]
            self.assertEqual(original.step(dt), restored.step(dt), f'trajectory diverged at {index}')
            self.assertEqual(original.feedback_state(), restored.feedback_state())
            self.assertEqual(original.equipment.take_load_events(), restored.equipment.take_load_events())
            self.assertEqual(original.equipment.take_exercise_events(), restored.equipment.take_exercise_events())
        self.assertEqual(snapshot(original), snapshot(restored))

    def test_both_exercises_learning_food_rng_and_pending_commands_continue_exactly(self):
        original = self.make(population=2, feedback='apparatus-visual-v1')
        for _ in range(117):
            original.step(.1)
        for _ in range(40):
            if original.flies[0].exercise.joint_position > 0:
                break
            original.step(.1)
        self.assertEqual(['bench_press', 'bicep_curl'], [fly.exercise.kind for fly in original.flies])
        self.assertGreater(original.flies[0].exercise.joint_position, 0)
        original.equipment.request_load('station-1', 1.1, 'pending-load')
        original.request_exercise('fly-1', 'bicep_curl', 'pending-exercise')
        original.request_exercise('fly-2', 'bicep_curl', 'already-effective')
        restored = self.roundtrip(original)
        self.assert_future(original, restored, 400)
        self.assertGreater(original.flies[0].training.total_work, 0)
        self.assertGreater(original.flies[1].training.sets, 0)
        self.assertGreater(original.flies[1].brain.gym_learning.memory.reward_events, 0)

    def test_inactive_bank_pending_population_and_default_no_learning_continue(self):
        original = self.make(population=3, learning_enabled=False)
        for _ in range(35):
            original.step(.1)
        original.request_population(1)
        restored = self.roundtrip(original)
        self.assert_future(original, restored, 30)
        original.request_population(3)
        restored.request_population(3)
        self.assert_future(original, restored)
        self.assertEqual(0, original.bank[0].brain.gym_learning.memory.reward_events)

    def test_fresh_checkpoint_and_cached_gaussian_rng_are_json_roundtrippable(self):
        original = self.make()
        original.environment.food_spawner.rng.gauss(0, 1)
        restored = self.roundtrip(original)
        self.assertEqual(original.environment.food_spawner.rng.gauss(0, 1),
                         restored.environment.food_spawner.rng.gauss(0, 1))
        self.assert_future(original, restored, 20)

    def test_removed_individual_keeps_queued_apparatus_until_reactivation(self):
        original = self.make(population=2)
        original.step(.1)
        original.request_exercise('fly-2', 'bench_press', 'inactive-pending')
        original.request_population(1)
        original.step(.1)
        self.assertIn('fly-2', original.equipment._pending_exercises)
        restored = self.roundtrip(original)
        original.request_population(2)
        restored.request_population(2)
        self.assert_future(original, restored, 60)

    def test_corrupt_or_incompatible_state_is_rejected_without_partial_mutation(self):
        source = self.make(population=2)
        source.step(.1)
        valid = snapshot(source)
        target = self.make()
        before = snapshot(target)
        mutations = [
            lambda d: d.update(version=999),
            lambda d: d['metadata'].update(runtime_sha256='0' * 64),
            lambda d: d['state'].update(population=True),
            lambda d: d['state'].update(elapsed=float('nan')),
            lambda d: d['state']['flies'][-1]['training'].update(fitness=4),
            lambda d: d['state']['flies'][-1].update(feedback_profile='unknown'),
            lambda d: d['state']['flies'][0]['network_activity'][0].__setitem__(0, 123),
            lambda d: d['state']['flies'][0]['gym_learning']['eligibility'][0].__setitem__(1, -1),
            lambda d: d['state']['equipment']['occupants'].append(['station-1', 'fly-2']),
            lambda d: d['state']['environment']['spawner']['rng'][1].__setitem__(624, 625),
            lambda d: d['state']['flies'][-1]['food_learning']['memory']['synapses'][0].update(multiplier=2),
        ]
        for mutate in mutations:
            damaged = copy.deepcopy(valid)
            mutate(damaged)
            with self.assertRaises(CheckpointValidationError):
                restore(target, damaged)
            self.assertEqual(before, snapshot(target))

    def test_configuration_and_source_bindings_reject_silent_model_changes(self):
        source, target = self.make(), self.make()
        target.bank[0].brain.network._leak = .25
        with self.assertRaises(CheckpointValidationError):
            restore(target, snapshot(source))
