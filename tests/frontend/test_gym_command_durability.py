"""Acknowledgements describe committed model boundaries, including after restart."""

from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from brain.gym_circuit import load_gym_circuits
from experiments.experiment_002 import create_gym
from experiments.session_checkpoint import restore, snapshot
from frontend.command_journal import CommandJournal
from frontend.gym_server import GymObservatoryServer
from frontend.server import ObservatoryConfig


ROOT = Path(__file__).resolve().parents[2]


class CapturingSocket:
    closed = False

    def __init__(self, connection):
        self.connection = connection
        self.messages = []

    async def send_json(self, message):
        if self.connection.in_transaction:
            raise AssertionError('Network delivery preceded durable commit')
        self.messages.append(deepcopy(message))

    async def close(self, **kwargs):
        self.closed = True

    @property
    def acknowledgements(self):
        return [message for message in self.messages if message['type'] == 'command_ack']


class GymCommandDurabilityTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuits = load_gym_circuits(ROOT)

    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)
        self.connection = sqlite3.connect(self.path / 'session.sqlite', isolation_level=None)
        self.servers = []
        self.gym = create_gym(*self.circuits, seed=7)

    async def asyncTearDown(self):
        for server in self.servers:
            await server.close()
        self.connection.close()
        self.directory.cleanup()

    def server(self, *, gym=None, **options):
        journal = CommandJournal(self.connection, session_id='browser-a', run_id='durable-run',
                                 hot_cache_size=2, max_commands=options.pop('max_commands', 100_000))
        server = GymObservatoryServer(gym or self.gym,
            ObservatoryConfig('compact', 'male-cns:v1.0', 30, self.path),
            command_journal=journal, running=False, **options)
        socket = CapturingSocket(self.connection)
        server._clients.add(socket)
        server._control_clients.add(socket)
        self.servers.append(server)
        return server, socket

    async def send(self, server, socket, command):
        await server._handle_command(socket, json.dumps(command))

    async def test_more_than_1024_commands_and_old_retry_after_restart_do_not_reapply(self):
        server, socket = self.server()
        first = {'type': 'set_running', 'running': False, 'command_id': 'pause-0'}
        await self.send(server, socket, first)
        original = socket.acknowledgements[-1]
        for index in range(1, 1100):
            await self.send(server, socket, dict(first, command_id=f'pause-{index}'))
        self.assertEqual(1100, len(socket.acknowledgements))
        self.assertLessEqual(server._commands.hot_cache_entries, 2)
        observer = server.export_observer_state()
        restored, peer = self.server(run_metadata=observer['run_metadata'])
        restored.running = True
        await self.send(restored, peer, first)
        self.assertEqual(original, peer.acknowledgements[-1])
        self.assertTrue(restored.running, 'A completed retry must not pause the restarted model')
        await self.send(restored, peer, dict(first, running=True))
        self.assertEqual('command_id_conflict', peer.messages[-1]['code'])

    async def test_quota_and_rate_errors_are_distinct_and_neither_blocks_old_retries(self):
        server, socket = self.server(max_commands=2, command_rate_limit=(2, 60.0))
        command = {'type': 'set_running', 'running': False, 'command_id': 'one'}
        await self.send(server, socket, command)
        first = socket.acknowledgements[-1]
        await self.send(server, socket, dict(command, command_id='two'))
        await self.send(server, socket, dict(command, command_id='three'))
        self.assertEqual('rate_limited', socket.messages[-1]['code'])
        await self.send(server, socket, command)
        self.assertEqual(first, socket.acknowledgements[-1])
        server._command_times.clear()
        await self.send(server, socket, dict(command, command_id='three'))
        self.assertEqual('session_command_quota', socket.messages[-1]['code'])
        self.assertEqual(2, len(server._commands))

    async def test_ack_and_checkpoint_commit_together_and_failure_never_acks_or_saves_on_close(self):
        self.connection.execute('CREATE TABLE checkpoints (state TEXT)')
        server, socket = self.server()
        checkpoints = []

        def save(current):
            self.assertTrue(self.connection.in_transaction)
            state = json.dumps(current.export_observer_state())
            self.connection.execute('INSERT INTO checkpoints VALUES (?)', (state,))
            checkpoints.append(state)

        server.on_boundary = save
        await self.send(server, socket, {'type': 'set_running', 'running': False, 'command_id': 'pause'})
        self.assertEqual(1, len(socket.acknowledgements))
        committed = self.connection.execute('SELECT state FROM checkpoints').fetchall()

        def fail(current):
            save(current)
            raise ValueError('checkpoint write failed')

        server.on_boundary = fail
        with self.assertRaisesRegex(ValueError, 'checkpoint write failed'):
            await self.send(server, socket, {'type': 'set_running', 'running': True, 'command_id': 'resume'})
        self.assertTrue(server._storage_failed)
        self.assertFalse(server.running)
        self.assertEqual(1, len(socket.acknowledgements))
        self.assertIsNone(server._commands.get('resume'))
        self.assertEqual(committed, self.connection.execute('SELECT state FROM checkpoints').fetchall())
        server.on_boundary = save
        before_close = len(checkpoints)
        await server.close()
        self.assertEqual(before_close, len(checkpoints), 'Failed model state must never replace its checkpoint')

    async def test_pending_load_checkpoint_restarts_then_applies_at_one_exact_step(self):
        for _ in range(1000):
            self.gym.step(.1)
            if self.gym.flies[0].exercise.joint_position > 0:
                break
        self.assertGreater(self.gym.flies[0].exercise.joint_position, 0)
        server, socket = self.server()
        saved = {}

        def save(current):
            saved['simulation'] = snapshot(current.simulation)
            saved['observer'] = current.export_observer_state()

        server.on_boundary = save
        command = {'type': 'set_load', 'station_id': 'station-1', 'load': .9, 'command_id': 'load-once'}
        await self.send(server, socket, command)
        pending = socket.acknowledgements[-1]
        self.assertEqual(('pending', None), (pending['status'], pending['effective_step']))
        restarted_gym = create_gym(*self.circuits, seed=7)
        restore(restarted_gym, saved['simulation'])
        restarted, peer = self.server(gym=restarted_gym, run_metadata=saved['observer']['run_metadata'])
        await self.send(restarted, peer, command)
        self.assertEqual(pending, peer.acknowledgements[-1])
        restarted.running = True
        applied = []
        for _ in range(1000):
            outgoing = restarted._clock_boundary(.1)
            applied.extend(message for _, message in outgoing
                           if message['type'] == 'command_ack' and message['command_id'] == 'load-once')
            if applied:
                break
        self.assertEqual(1, len(applied))
        self.assertEqual('applied', applied[0]['status'])
        self.assertEqual(restarted_gym.step_count, applied[0]['effective_step'])
        self.assertEqual(.9, restarted_gym.equipment.stations[0].load)
        for _ in range(3):
            restarted._clock_boundary(.1)
        final, final_peer = self.server(gym=restarted_gym)
        await self.send(final, final_peer, command)
        self.assertEqual(applied[0], final_peer.acknowledgements[-1])
        self.assertNotEqual(restarted_gym.step_count, applied[0]['effective_step'])
