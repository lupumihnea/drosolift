"""Explicit apparatus setup is distinct from locomotion and earned repetitions."""

import unittest
from copy import deepcopy

from simulation.signals import MotorDrive
from world.environment import Environment
from world.equipment import EquipmentFloor, EquipmentStation, ExerciseState
from world.fly import FlyBody
from world.gym import TrainingState


class ExerciseSetupTest(unittest.TestCase):
    def setUp(self):
        self.bench = EquipmentStation('bench', 'bench_press', 0, 0, .2, .6, .7, .45)
        self.curl = EquipmentStation('curl', 'bicep_curl', 3, 2, .5, .4, .55, .45)
        self.floor = EquipmentFloor((self.bench, self.curl), continuous_training=True)
        self.body, self.exercise = FlyBody(0, 0, .2), ExerciseState()
        self.training, self.environment = TrainingState(), Environment(20, 12, None)

    def advance(self, drive=1, dt=.01):
        self.floor.advance('fly-1', self.body, MotorDrive(drive, 0), dt,
                           self.environment, self.training, self.exercise)

    def test_setup_at_rest_imposes_received_pose_without_work_or_counter_changes(self):
        self.exercise.repetitions = 2
        self.exercise.rep_in_set = 2
        self.training.total_work = .84
        self.floor.request_exercise('fly-1', 'bicep_curl', 'switch-1', self.exercise)
        self.floor.apply_racked_exercises((('fly-1', self.body, self.exercise),))
        self.assertEqual(('curl', 'bicep_curl', 'recovery'),
                         (self.exercise.station_id, self.exercise.kind, self.exercise.phase))
        self.assertEqual((3, 2, .5), (self.body.x, self.body.y, self.body.heading))
        self.assertEqual((.5, .55, 0), (self.exercise.body_elevation,
                                      self.exercise.body_pitch, self.exercise.body_roll))
        self.assertEqual((2, 2, .84, 0, 0), (self.exercise.repetitions,
            self.exercise.rep_in_set, self.training.total_work, self.training.reward, self.training.distance))
        self.assertEqual(('switch-1',), self.floor.take_exercise_events())

    def test_midstroke_request_waits_for_return_and_preserves_completed_work(self):
        self.advance(dt=.1)
        self.floor.request_exercise('fly-1', 'bicep_curl', 'switch-1', self.exercise)
        self.floor.apply_racked_exercises((('fly-1', self.body, self.exercise),))
        self.assertEqual('bench', self.exercise.station_id)
        for _ in range(2000):
            self.advance()
            if self.exercise.kind == 'bicep_curl':
                break
        self.assertEqual('bicep_curl', self.exercise.kind)
        self.assertEqual((1, 1, 0), (self.exercise.repetitions, self.exercise.rep_in_set, self.training.sets))
        self.assertAlmostEqual(.42, self.training.total_work)
        self.assertEqual(0, self.training.reward)
        self.assertEqual({'curl': 'fly-1'}, self.floor.occupants)

    def test_partial_return_and_setup_cannot_create_rep_or_reward(self):
        self.advance(dt=.1)
        reference, body, training, state = deepcopy((self.floor, self.body, self.training, self.exercise))
        self.floor.request_exercise('fly-1', 'bicep_curl', 'switch-1', self.exercise)
        for _ in range(500):
            self.advance(0)
            reference.advance('fly-1', body, MotorDrive(0, 0), .01, self.environment, training, state)
            if self.exercise.kind == 'bicep_curl':
                break
        self.assertEqual('bicep_curl', self.exercise.kind)
        self.assertEqual((0, 0, training.total_work),
                         (self.exercise.repetitions, self.training.reward, self.training.total_work))

    def test_same_exercise_is_noop_and_occupied_target_cannot_be_stolen(self):
        self.advance(dt=.1)
        q = self.exercise.joint_position
        self.floor.request_exercise('fly-1', 'bench_press', 'same-1', self.exercise)
        self.assertEqual(('same-1',), self.floor.take_exercise_events())
        self.assertEqual(q, self.exercise.joint_position)
        other = ExerciseState()
        self.floor.advance('fly-2', FlyBody(3, 2, .5), MotorDrive(1, 0), .1,
                           self.environment, TrainingState(), other)
        with self.assertRaises(ValueError):
            self.floor.request_exercise('fly-1', 'bicep_curl', 'switch-1', self.exercise)
        self.assertEqual({'bench': 'fly-1', 'curl': 'fly-2'}, self.floor.occupants)
