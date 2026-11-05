"""Observable controls, retries and exact clock boundaries through real sockets."""

import asyncio
import json
from pathlib import Path
import tempfile
import unittest

from aiohttp.test_utils import TestClient, TestServer

from brain.gym_circuit import load_gym_circuits
from experiments.experiment_002 import create_gym
from frontend.gym_server import create_gym_app
from frontend.gym_controls import parse_gym_control_command
from frontend.server import ObservatoryConfig
from frontend.telemetry import TelemetryProtocolError


ROOT = Path(__file__).resolve().parents[2]


class GymControlProtocolTest(unittest.TestCase):
    def test_exercise_command_rejects_unknown_kind_identity_and_extra_fields(self):
        valid = {'type': 'set_exercise', 'fly_id': 'fly-1', 'kind': 'bicep_curl', 'command_id': 'exercise:1'}
        self.assertEqual('exercise', parse_gym_control_command(json.dumps(valid)).kind)
        for changes in ({'kind': 'squat'}, {'kind': True}, {'fly_id': 'fly-11'},
                        {'fly_id': None}, {'command_id': None}, {'extra': 1}):
            with self.assertRaises(TelemetryProtocolError):
                parse_gym_control_command(json.dumps(valid | changes))

    def test_load_command_rejects_coercion_nonfinite_and_unbounded_values(self):
        valid = {'type': 'set_load', 'station_id': 'station-1', 'command_id': 'test:1', 'load': .8}
        self.assertEqual(.8, parse_gym_control_command(json.dumps(valid)).value)
        for value in (True, '1', None, 0, 3.1, float('nan'), float('inf')):
            with self.assertRaises(TelemetryProtocolError):
                parse_gym_control_command(json.dumps(dict(valid, load=value)))
        for identity in ('', 'bad id', None, 123, 'x' * 81):
            with self.assertRaises(TelemetryProtocolError):
                parse_gym_control_command(json.dumps(dict(valid, command_id=identity)))
        with self.assertRaises(TelemetryProtocolError):
            parse_gym_control_command(json.dumps(dict(valid, extra=1)))


class GymControlsTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuits = load_gym_circuits(ROOT)

    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        path = Path(self.temporary.name)
        (path / 'index.html').write_text('<main>gym</main>')
        self.gym = create_gym(*self.circuits, seed=7)
        self.client = TestClient(TestServer(create_gym_app(simulation=self.gym,
            config=ObservatoryConfig('compact', 'male-cns:v1.0', 30, path))))
        await self.client.start_server()
        self.socket = await self.client.ws_connect('/ws?controls=1')

    async def asyncTearDown(self):
        await self.client.close()
        self.temporary.cleanup()

    async def receive(self, kind, socket=None):
        for _ in range(1000):
            message = await (socket or self.socket).receive_json(timeout=2)
            if message['type'] == kind:
                return message
        self.fail(f'Missing {kind}')

    async def pause(self):
        await self.socket.send_json({'type': 'set_running', 'running': False,
                                     'command_id': 'pause-1'})
        return await self.receive('command_ack')

    async def test_initial_metadata_retains_seed_clock_and_official_provenance(self):
        state = await self.receive('control_state')
        metadata = state['metadata']
        self.assertEqual(7, metadata['seed'])
        self.assertAlmostEqual(1 / 30, metadata['dt'])
        self.assertEqual('male-cns:v1.0', metadata['source']['dataset'])
        self.assertEqual(state['run_id'], metadata['run_id'])
        self.assertEqual(91, metadata['model_scope']['simulated_neurons'])
        self.assertEqual(64, len(metadata['circuit_sha256']['data/circuits/gym-v1-runtime.json']))

    async def test_pause_ack_and_reconnect_preserve_exact_state(self):
        await self.receive('control_state')
        ack = await self.pause()
        before = self.gym.snapshot()
        self.assertEqual(('applied', before.step), (ack['status'], ack['effective_step']))
        await asyncio.sleep(.1)
        self.assertEqual(before, self.gym.snapshot())
        observer = await self.client.ws_connect('/ws?controls=1')
        state = await self.receive('control_state', observer)
        frame = await self.receive('gym_frame', observer)
        self.assertEqual(ack['run_id'], state['run_id'])
        self.assertEqual(before.step, state['step'])
        self.assertEqual(before.step, frame['step'])
        self.assertEqual(before.flies[0].exercise.joint_position,
                         frame['flies'][0]['exercise']['joint_position'])
        await observer.close()

    async def test_load_is_deferred_to_full_return_and_retry_is_applied_once(self):
        await self.receive('control_state')
        frame = await self.receive('gym_frame')
        while frame['flies'][0]['exercise']['joint_position'] == 0:
            frame = await self.receive('gym_frame')
        await self.pause()
        self.assertGreater(self.gym.flies[0].exercise.joint_position, 0)
        command = {'type': 'set_load', 'command_id': 'load-1',
                   'station_id': 'station-1', 'load': .9}
        await self.socket.send_json(command)
        pending = await self.receive('command_ack')
        self.assertEqual(('pending', None), (pending['status'], pending['effective_step']))
        self.assertEqual(.6, self.gym.equipment.stations[0].load)
        await self.socket.send_json(command)
        self.assertEqual(pending, await self.receive('command_ack'))
        await self.socket.send_json({'type': 'set_running', 'running': True})
        applied = await self.receive('command_ack')
        self.assertEqual('load-1', applied['command_id'])
        self.assertEqual('applied', applied['status'])
        self.assertGreaterEqual(self.gym.flies[0].exercise.repetitions, 1)
        self.assertEqual(.9, self.gym.equipment.stations[0].load)
        await self.socket.send_json(command)
        self.assertEqual(applied, await self.receive('command_ack'))
        await self.socket.send_json(dict(command, load=1.0))
        self.assertEqual('command_id_conflict', (await self.receive('error'))['code'])
        self.assertEqual(.9, self.gym.equipment.stations[0].load)

    async def test_invalid_loads_do_not_mutate_state(self):
        await self.receive('control_state')
        await self.pause()
        before = self.gym.snapshot()
        for index, value in enumerate([True, '1', None, 0, -.1, 3.1,
                                       float('nan'), float('inf')]):
            await self.socket.send_str(json.dumps({'type': 'set_load',
                'command_id': f'invalid-{index}', 'station_id': 'station-1', 'load': value}))
            self.assertEqual('invalid_command', (await self.receive('error'))['code'])
        self.assertEqual(.6, self.gym.equipment.stations[0].load)
        self.assertEqual(before, self.gym.snapshot())

    async def test_extensions_do_not_reach_legacy_observers(self):
        await self.receive('control_state')
        await self.pause()
        legacy = await self.client.ws_connect('/ws')
        await self.receive('gym_frame', legacy)
        await self.socket.send_json({'type': 'set_load', 'command_id': 'load-legacy',
                                     'station_id': 'station-2', 'load': .7})
        ack = await self.receive('command_ack')
        self.assertEqual('applied', ack['status'])
        with self.assertRaises(asyncio.TimeoutError):
            await legacy.receive_json(timeout=.08)
        await legacy.close()

    async def test_exercise_setup_waits_while_paused_then_retries_and_reconnects_consistently(self):
        await self.receive('control_state')
        frame = await self.receive('gym_frame')
        while frame['flies'][0]['exercise']['joint_position'] == 0:
            frame = await self.receive('gym_frame')
        await self.pause()
        before = self.gym.snapshot()
        command = {'type': 'set_exercise', 'command_id': 'exercise-1',
                   'fly_id': 'fly-1', 'kind': 'bicep_curl'}
        await self.socket.send_json(command)
        pending = await self.receive('command_ack')
        self.assertEqual(('set_exercise', 'pending', None),
                         (pending['command'], pending['status'], pending['effective_step']))
        await asyncio.sleep(.08)
        self.assertEqual(before, self.gym.snapshot())
        await self.socket.send_json(command)
        self.assertEqual(pending, await self.receive('command_ack'))
        await self.socket.send_json({'type': 'set_running', 'running': True})
        applied = await self.receive('command_ack')
        self.assertEqual(('exercise-1', 'applied'), (applied['command_id'], applied['status']))
        self.assertGreaterEqual(self.gym.flies[0].exercise.repetitions, before.flies[0].exercise.repetitions + 1)
        await self.socket.send_json({'type': 'set_running', 'running': False, 'command_id': 'pause-after-setup'})
        await self.receive('command_ack')
        selected = self.gym.snapshot().flies[0]
        self.assertEqual(('station-2', 'bicep_curl'), (selected.exercise.station_id, selected.exercise.kind))
        self.assertEqual((-3.2, -2), (selected.frame.body.x, selected.frame.body.y))
        observer = await self.client.ws_connect('/ws?controls=1')
        state = await self.receive('control_state', observer)
        self.assertEqual('bicep_curl', state['exercises'][0]['kind'])
        self.assertIsNone(state['exercises'][0]['pending_kind'])
        await observer.send_json(command)
        self.assertEqual(applied, await self.receive('command_ack', observer))
        await observer.close()
