"""Gym observer using the existing same-origin routes and connection lifecycle."""

import asyncio
from collections.abc import Callable
from dataclasses import asdict
from collections import deque
from copy import deepcopy
import math
import sqlite3
import time
from uuid import uuid4
from aiohttp import web

from frontend.gym_controls import GymControlCommand, parse_gym_control_command
from frontend.command_journal import CommandJournal, CommandQuotaExceeded
from frontend.gym_telemetry import gym_control_state, gym_frame_message
from frontend.gym_metadata import gym_run_metadata
from frontend.server import ObservatoryConfig, ObservatoryServer, create_app
from frontend.telemetry import TelemetryProtocolError
from simulation.gym import GymSimulation
from world.equipment import ExerciseUnavailableError


class GymObservatoryServer(ObservatoryServer):
    """Apply count at the next clock boundary, including while physics is paused."""

    def __init__(self, simulation: GymSimulation, config: ObservatoryConfig,
                 persist_memory: Callable[[], None] | None = None, *,
                 run_id: str | None = None, command_journal: CommandJournal | None = None,
                 run_metadata: dict[str, object] | None = None, running: bool = True,
                 on_boundary: Callable[['GymObservatoryServer'], None] | None = None,
                 command_rate_limit: tuple[int, float] | None = None) -> None:
        if config.backend != 'compact':
            raise ValueError('Gym requires the compact backend')
        if type(running) is not bool:
            raise ValueError('Running must be a boolean')
        if command_rate_limit is not None:
            limit, window = command_rate_limit
            if type(limit) is not int or not 1 <= limit <= 100_000 or not math.isfinite(window) or not 0 < window <= 86400:
                raise ValueError('Invalid command rate limit')
        super().__init__(simulation, config, persist_memory)
        self.running = running
        self._schema = 3 if simulation.equipment is not None else 2
        self._latest_frame = gym_frame_message(simulation.snapshot(), schema=self._schema)
        self.run_id = run_id or (command_journal.run_id if command_journal is not None else str(uuid4()))
        if not isinstance(self.run_id, str) or not 1 <= len(self.run_id) <= 128:
            raise ValueError('Invalid run identity')
        if command_journal is not None and command_journal.run_id != self.run_id:
            raise ValueError('Command journal belongs to a different run')
        self._commands = command_journal if command_journal is not None else CommandJournal(
            None, session_id=self.run_id, run_id=self.run_id)
        if run_metadata is not None and run_metadata.get('run_id') != self.run_id:
            raise ValueError('Saved metadata belongs to a different run')
        self._run_metadata = deepcopy(run_metadata) if run_metadata is not None else gym_run_metadata(
            simulation, run_id=self.run_id, fps=config.fps, initial_state=self._latest_frame)
        self._control_clients: set[web.WebSocketResponse] = set()
        self.on_boundary = on_boundary
        self._command_rate_limit = command_rate_limit
        self._command_times: deque[float] = deque()
        self._storage_failed = False
        self._closed = False

    def export_observer_state(self) -> dict[str, object]:
        """Journal rows remain in SQLite; only observer/run identity enters the checkpoint."""
        return {'run_id': self.run_id, 'running': self.running,
                'run_metadata': deepcopy(self._run_metadata)}

    def _save_boundary(self) -> None:
        """Called synchronously inside the journal transaction, before any ack is sent."""
        if self.on_boundary is not None:
            self.on_boundary(self)

    def _admit_command(self) -> bool:
        if self._command_rate_limit is None:
            return True
        limit, window = self._command_rate_limit
        now = time.monotonic()
        while self._command_times and self._command_times[0] <= now - window:
            self._command_times.popleft()
        if len(self._command_times) >= limit:
            return False
        self._command_times.append(now)
        return True

    async def _rate_error(self, socket: web.WebSocketResponse) -> None:
        await socket.send_json({'type': 'error', 'code': 'rate_limited',
            'message': 'Too many new commands for this session; wait before trying a new action.'})

    def _hello_message(self) -> dict[str, object]:
        message = super()._hello_message()
        equipment = self.simulation.equipment
        message.update(schema=self._schema, experiment='gym', population=self.simulation.population,
                       station=asdict(self.simulation.station))
        if equipment is not None:
            message['equipment'] = [asdict(station) for station in equipment.stations]
        return message

    async def health(self, request: web.Request) -> web.Response:
        return web.json_response({'status': 'ready', 'schema': self._schema, 'backend': self.config.backend,
            'dataset': self.config.dataset, 'experiment': 'gym', 'population': self.simulation.population})

    async def _send_additional_initial_state(self, socket: web.WebSocketResponse,
                                             request: web.Request) -> None:
        await socket.send_json({'type': 'population', 'count': self.simulation.population})
        if request.query.get('controls') == '1' and self._schema == 3:
            self._control_clients.add(socket)
            await socket.send_json(self._control_state(include_metadata=True))

    def _control_state(self, *, include_metadata: bool = False) -> dict[str, object]:
        message = gym_control_state(self.simulation, self.run_id)
        if include_metadata:
            message['metadata'] = self._run_metadata
        return message

    def _ack(self, command: GymControlCommand, status: str) -> dict[str, object]:
        return {'type': 'command_ack', 'command_id': command.command_id,
                'command': {'load': 'set_load', 'running': 'set_running', 'exercise': 'set_exercise'}[command.kind],
                'status': status, 'effective_step': self.simulation.step_count if status == 'applied' else None,
                'run_id': self.run_id}

    async def _broadcast_control(self, message: dict[str, object]) -> None:
        for socket in tuple(self._control_clients):
            if socket.closed or socket not in self._clients:
                self._control_clients.discard(socket)
                continue
            try:
                await socket.send_json(message)
            except (ConnectionResetError, BrokenPipeError):
                self._control_clients.discard(socket)

    def _collect_load_acks(self) -> list[dict[str, object]]:
        """Capture the effective model step before any network await can yield."""
        if self.simulation.equipment is None:
            return []
        messages = []
        for command_id in self.simulation.equipment.take_load_events():
            command, previous = self._commands[command_id]
            ack = previous if previous['status'] == 'applied' else self._ack(command, 'applied')
            self._commands[command_id] = command, ack
            messages.append(ack)
        return messages

    def _collect_exercise_acks(self) -> list[dict[str, object]]:
        if self.simulation.equipment is None:
            return []
        messages = []
        for command_id in self.simulation.equipment.take_exercise_events():
            command, previous = self._commands[command_id]
            ack = previous if previous['status'] == 'applied' else self._ack(command, 'applied')
            self._commands[command_id] = command, ack
            messages.append(ack)
        return messages

    async def _handle_command(self, socket: web.WebSocketResponse, text: str) -> None:
        if self._storage_failed:
            raise RuntimeError('Session storage failed; reconnect after server recovery')
        try:
            command = parse_gym_control_command(text)
        except TelemetryProtocolError:
            if not self._admit_command():
                await self._rate_error(socket)
            else:
                await self._send_command_error(socket)
            return
        if command.command_id is not None:
            if socket not in self._control_clients:
                await self._send_command_error(socket)
                return
            try:
                previous = self._commands.get(command.command_id)
            except (sqlite3.Error, ValueError, OSError):
                self._storage_failed = True
                self.running = False
                raise
            if previous is not None:
                if previous[0] == command:
                    # Durable lookup happens before throttling/quota checks, so
                    # old retries keep their original pending/applied response.
                    await socket.send_json(previous[1])
                else:
                    await socket.send_json({'type': 'error', 'code': 'command_id_conflict',
                                            'message': 'Command identity already has a different payload.'})
                return
        if not self._admit_command():
            await self._rate_error(socket)
            return
        try:
            with self._commands.atomic():
                if command.command_id is not None:
                    self._commands.ensure_capacity(command.command_id)
                outgoing = self._apply_command(command)
                self._save_boundary()
        except CommandQuotaExceeded as error:
            await socket.send_json({'type': 'error', 'code': 'session_command_quota', 'message': str(error)})
            return
        except ExerciseUnavailableError:
            await socket.send_json({'type': 'error', 'code': 'exercise_unavailable',
                'message': 'No free station for that exercise; reduce the population first.'})
            return
        except Exception:
            # Domain validation is performed inside _apply_command before it
            # mutates. Checkpoint errors must propagate to the gateway instead.
            self._storage_failed = True
            self.running = False
            raise
        for target, message in outgoing:
            if target == 'socket':
                await socket.send_json(message)
            elif target == 'all':
                await self._broadcast(message)
            else:
                await self._broadcast_control(message)

    def _apply_command(self, command: GymControlCommand) -> list[tuple[str, dict[str, object]]]:
        """Complete model/journal changes without yielding a partially saved boundary."""
        outgoing: list[tuple[str, dict[str, object]]] = []
        if command.kind == 'population':
            self.simulation.request_population(command.value)
            return outgoing
        if command.kind == 'exercise':
            try:
                self.simulation.request_exercise(command.fly_id, command.value, command.command_id)
            except ExerciseUnavailableError:
                raise
            except ValueError:
                return [('socket', self._invalid_command_message())]
            self._commands[command.command_id] = command, self._ack(command, 'pending')
            changed = self.simulation.apply_pending_exercises()
            applied = self._collect_exercise_acks()
            if changed:
                self._latest_frame = gym_frame_message(self.simulation.snapshot(), schema=self._schema)
            outgoing.append(('socket', self._commands[command.command_id][1]))
            outgoing.extend(('control', ack) for ack in applied if ack['command_id'] != command.command_id)
            if changed:
                outgoing.append(('all', self._latest_frame))
            outgoing.append(('control', self._control_state()))
            return outgoing
        if command.kind == 'load':
            try:
                self.simulation.equipment.request_load(command.station_id, command.value, command.command_id)
            except ValueError:
                return [('socket', self._invalid_command_message())]
            self._commands[command.command_id] = command, self._ack(command, 'pending')
            self.simulation.equipment.apply_racked_loads(tuple(fly.exercise for fly in self.simulation.flies))
            applied = self._collect_load_acks()
            outgoing.append(('socket', self._commands[command.command_id][1]))
            outgoing.extend(('control', ack) for ack in applied if ack['command_id'] != command.command_id)
            outgoing.append(('control', self._control_state()))
            return outgoing
        self.running = command.value
        self._latest_frame = gym_frame_message(self.simulation.snapshot(), schema=self._schema)
        outgoing.append(('all', {'type': 'running', 'running': self.running}))
        if command.command_id is not None:
            ack = self._ack(command, 'applied')
            self._commands[command.command_id] = command, ack
            outgoing.append(('socket', ack))
        if self._schema == 3:
            outgoing.append(('control', self._control_state()))
        return outgoing

    @staticmethod
    def _invalid_command_message() -> dict[str, object]:
        return {'type': 'error', 'code': 'invalid_command',
                'message': 'Invalid gym command; check identity, exercise, load and population bounds.'}

    async def _send_command_error(self, socket: web.WebSocketResponse) -> None:
        await socket.send_json({'type': 'error', 'code': 'invalid_command',
                                'message': 'Invalid gym command; check identity, exercise, load and population bounds.'})

    def _clock_boundary(self, interval: float) -> list[tuple[str, dict[str, object]]]:
        if self._storage_failed:
            raise RuntimeError('Session storage failed; no model steps may continue')
        with self._commands.atomic():
            population_changed = self.simulation.apply_pending_population()
            exercise_changed = self.simulation.apply_pending_exercises()
            if self.simulation.equipment is not None:
                self.simulation.equipment.apply_racked_loads(tuple(fly.exercise for fly in self.simulation.flies))
            if self.running:
                self.simulation.step(interval)
            changed = self.running or population_changed or exercise_changed
            if changed:
                self._latest_frame = gym_frame_message(self.simulation.snapshot(), schema=self._schema)
            acknowledgements = self._collect_load_acks() + self._collect_exercise_acks()
            outgoing = []
            if population_changed:
                outgoing.append(('all', {'type': 'population', 'count': self.simulation.population}))
            if changed:
                outgoing.append(('all', self._latest_frame))
            outgoing.extend(('control', ack) for ack in acknowledgements)
            if self._schema == 3 and (changed or acknowledgements):
                outgoing.append(('control', self._control_state()))
            # Paused sessions still checkpoint a queued command at its exact
            # model boundary. There is no await before journal + state commit.
            self._save_boundary()
            return outgoing

    async def clock(self) -> None:
        loop = asyncio.get_running_loop()
        interval = 1.0 / self.config.fps
        deadline = loop.time() + interval
        saved_rewards = self._reward_events()
        while True:
            await asyncio.sleep(max(0.0, deadline - loop.time()))
            try:
                outgoing = self._clock_boundary(interval)
            except Exception:
                self._storage_failed = True
                self.running = False
                raise
            for target, message in outgoing:
                if target == 'all':
                    await self._broadcast(message)
                else:
                    await self._broadcast_control(message)
            rewards = self._reward_events()
            if rewards != saved_rewards and self.persist_memory is not None:
                try:
                    self.persist_memory()
                    saved_rewards = rewards
                except OSError:
                    self.running = False
                    await self._broadcast({'type': 'running', 'running': False})
                    await self._broadcast({'type': 'error', 'code': 'memory_save_failed',
                                          'message': 'Memory could not be saved; check disk space.'})
            deadline += interval
            if deadline < loop.time() - interval:
                deadline = loop.time() + interval

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            try:
                if not self._storage_failed and self.on_boundary is not None:
                    with self._commands.atomic():
                        self._save_boundary()
            except Exception:
                self._storage_failed = True
                self.running = False
                raise
            finally:
                if self._storage_failed:
                    # In-memory state may be newer than the durable checkpoint;
                    # neither the public snapshot nor legacy memory may replace it.
                    for socket in tuple(self._clients):
                        await socket.close(code=1001, message=b'session storage failed')
                    self._clients.clear()
                else:
                    await super().close()
        finally:
            self._commands.close()

    def _reward_events(self) -> int:
        return sum(fly.brain.food_learning.memory.reward_events + fly.brain.gym_learning.memory.reward_events
                   for fly in self.simulation.bank)


def create_gym_app(*, simulation: GymSimulation, config: ObservatoryConfig,
                   persist_memory: Callable[[], None] | None = None) -> web.Application:
    """Serve the composition's gym schema with the same-origin restrictions."""
    return create_app(simulation=simulation, config=config, persist_memory=persist_memory,
                      server_type=GymObservatoryServer)
