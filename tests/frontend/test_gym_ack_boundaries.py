"""Every command applied at a shared resting boundary must acknowledge once."""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from brain.gym_circuit import load_gym_circuits
from experiments.experiment_002 import create_gym
from frontend.gym_server import GymObservatoryServer
from frontend.server import ObservatoryConfig


ROOT = Path(__file__).resolve().parents[2]


class ObservedSocket:
    closed = False

    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(deepcopy(message))


class RestingBoundaryAcknowledgementTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuits = load_gym_circuits(ROOT)

    def setup_server(self):
        gym = create_gym(*self.circuits, population=2, seed=7)
        server = GymObservatoryServer(gym, ObservatoryConfig('compact', 'male-cns:v1.0', 10, ROOT / 'frontend/web/dist'))
        first, second = ObservedSocket(), ObservedSocket()
        server._clients.update((first, second))
        server._control_clients.update((first, second))
        for _ in range(50):
            gym.step(.1)
            if all(fly.exercise.joint_position > 0 for fly in gym.flies):
                break
        self.assertTrue(all(fly.exercise.joint_position > 0 for fly in gym.flies))
        return gym, server, first, second

    def until_bottom(self, gym, fly):
        repetitions = fly.exercise.repetitions
        for _ in range(2000):
            # A single actual physics substep can end at bottom before the next
            # clock boundary applies the pending change.
            gym.step(.01)
            if fly.exercise.joint_position == 0 and fly.exercise.repetitions > repetitions:
                return
        self.fail('The actual loaded joint did not complete a return')

    def assert_applied_once(self, socket, command_id):
        applied = [message for message in socket.messages if message.get('type') == 'command_ack'
                   and message.get('command_id') == command_id and message.get('status') == 'applied']
        self.assertEqual(1, len(applied), f'Missing or duplicate applied acknowledgement for {command_id}')

    async def test_immediate_exercise_request_acknowledges_another_queued_fly_at_the_same_boundary(self):
        gym, server, first, second = self.setup_server()
        await server._handle_command(first, json.dumps({'type': 'set_exercise', 'command_id': 'earlier',
                                                        'fly_id': 'fly-2', 'kind': 'bench_press'}))
        self.assertEqual('pending', first.messages[0]['status'])
        self.until_bottom(gym, gym.flies[1])
        await server._handle_command(second, json.dumps({'type': 'set_exercise', 'command_id': 'current',
                                                         'fly_id': 'fly-1', 'kind': 'bench_press'}))
        self.assertEqual('bench_press', gym.flies[1].exercise.kind)
        self.assert_applied_once(first, 'earlier')
        self.assert_applied_once(second, 'current')

    async def test_immediate_load_request_acknowledges_another_queued_station_at_the_same_boundary(self):
        gym, server, first, second = self.setup_server()
        await server._handle_command(first, json.dumps({'type': 'set_load', 'command_id': 'earlier',
                                                        'station_id': 'station-1', 'load': .8}))
        self.assertEqual('pending', first.messages[0]['status'])
        self.until_bottom(gym, gym.flies[0])
        await server._handle_command(second, json.dumps({'type': 'set_load', 'command_id': 'current',
                                                         'station_id': 'station-3', 'load': .9}))
        self.assertEqual(.8, gym.equipment.stations[0].load)
        self.assert_applied_once(first, 'earlier')
        self.assert_applied_once(second, 'current')
