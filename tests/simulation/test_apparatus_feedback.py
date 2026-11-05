"""Real official paths receive explicitly synthetic apparatus visual samples."""

from pathlib import Path
import unittest

from brain.gym_circuit import load_gym_circuits
from experiments.experiment_002 import create_gym


ROOT = Path(__file__).resolve().parents[2]


class ApparatusSimulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuits = load_gym_circuits(ROOT)

    def gym(self, kind='bench_press', feedback='apparatus-visual-v1'):
        gym = create_gym(*self.circuits, seed=7, learning_enabled=False, feedback=feedback)
        gym.environment.food_spawner = None
        gym.request_exercise('fly-1', kind, 'initial-setup')
        gym.apply_pending_exercises()
        gym.equipment.take_exercise_events()
        return gym

    def test_actual_l1_l2_activity_matches_latched_indicator_and_task_changes_side(self):
        bench, curl = self.gym(), self.gym('bicep_curl')
        for gym in (bench, curl):
            frame = gym.step(.1).flies[0].frame
            feedback = gym.feedback_state()[0]
            circuit = gym.flies[0].brain.network.circuit
            for side in ('left', 'right'):
                for identity in circuit.sensory_inputs[f'vision_{side}']:
                    self.assertEqual(feedback[f'indicator_{side}'], frame.neural.activity_by_body[identity])
            self.assertEqual(frame.step, feedback['sample_step'])
            self.assertEqual(frame.elapsed, feedback['sample_elapsed'])
        self.assertGreater(bench.feedback_state()[0]['indicator_left'], curl.feedback_state()[0]['indicator_left'])
        self.assertGreater(curl.feedback_state()[0]['indicator_right'], bench.feedback_state()[0]['indicator_right'])

    def test_feedback_is_sampled_before_joint_advance_and_snapshot_does_not_recompute_it(self):
        gym = self.gym()
        fly = gym.flies[0]
        fly.exercise.phase = 'lifting'
        fly.exercise.recovery_remaining = 0
        before = fly.exercise.joint_position
        gym.step(.1)
        recorded = gym.feedback_state()
        self.assertGreater(fly.exercise.joint_position, before)
        fly.exercise.joint_position = .9
        self.assertEqual(recorded, gym.feedback_state())

    def test_default_none_keeps_original_visual_inputs_and_setup_is_not_distance(self):
        gym = self.gym('bicep_curl', feedback='none')
        frame = gym.step(.1).flies[0]
        self.assertEqual('none', gym.feedback_state()[0]['profile'])
        self.assertEqual((0, 0), (frame.frame.sensory.vision_left, frame.frame.sensory.vision_right))
        self.assertEqual(0, frame.training.distance)
        self.assertEqual(-3.2, frame.frame.body.x)
