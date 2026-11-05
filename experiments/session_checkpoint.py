"""Bounded JSON checkpoints for the compact gym, composed outside the domains.

This is state, not executable serialization. Restore validates the entire document
against the supplied validated circuits and model implementation before changing
anything. Server identity, command journal and durable transactions belong to the
application gateway; no persistence I/O occurs in this module.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, fields, is_dataclass, replace
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import random

from brain.learning import MushroomBodyLearning
from brain.memory import MemoryState, SynapseMemory
from brain.network import ConnectomeNetwork
from simulation.gym import GymSimulation
from simulation.signals import (ApparatusFeedback, BodyState, LearningSnapshot,
                                MotorDrive, NeuralSnapshot, SensoryFrame, TelemetryFrame)
from world.apparatus_feedback import FEEDBACK_PROFILES
from world.equipment import ExerciseState
from world.food import Food
from world.gym import TrainingState


FORMAT = 'drosolift-session-checkpoint'
VERSION = 1
MAX_BYTES = 8 * 1024 * 1024
MAX_COUNTER = 2 ** 53 - 1
_MODEL_FILES = (
    'experiments/experiment_002.py', 'brain/network.py', 'brain/neuron.py',
    'brain/gym.py', 'brain/sensory.py', 'brain/learning.py', 'brain/memory.py',
    'brain/readout.py', 'simulation/gym.py', 'simulation/signals.py',
    'simulation/gym_signals.py', 'world/fly.py', 'world/sensors.py',
    'world/environment.py', 'world/food.py', 'world/gym.py',
    'world/equipment.py', 'world/apparatus_feedback.py',
)


class CheckpointValidationError(ValueError):
    """The JSON state is malformed or does not belong to this exact model."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckpointValidationError(message)


def _record(value: object, keys: object) -> dict:
    _require(type(value) is dict and set(value) == set(keys), 'Unexpected checkpoint fields')
    return value


def _list(value: object, maximum: int, length: int | None = None) -> list:
    _require(type(value) is list and len(value) <= maximum
             and (length is None or len(value) == length), 'Invalid checkpoint array')
    return value


def _number(value: object, low: float = 0, high: float = 1) -> float:
    _require(type(value) in (int, float) and math.isfinite(value)
             and low <= value <= high, 'Checkpoint number is nonfinite or out of bounds')
    return value


def _integer(value: object, low: int = 0, high: int = MAX_COUNTER) -> int:
    _require(type(value) is int and low <= value <= high, 'Invalid checkpoint integer')
    return value


def _boolean(value: object) -> bool:
    _require(type(value) is bool, 'Invalid checkpoint boolean')
    return value


def _text(value: object, maximum: int = 128) -> str:
    _require(type(value) is str and 0 < len(value) <= maximum, 'Invalid checkpoint string')
    return value


def _safe_json(value: object) -> None:
    # Restrict the input tree before encoding; bounded depth also rejects cycles.
    budget = [0]

    def visit(item: object, depth: int = 0) -> None:
        budget[0] += 1
        _require(depth <= 24 and budget[0] <= 250_000, 'Checkpoint is too complex')
        if item is None or type(item) is bool:
            return
        if type(item) in (int, float):
            _number(item, -MAX_COUNTER, MAX_COUNTER)
        elif type(item) is str:
            _require(len(item) <= 1024, 'Checkpoint string is too long')
        elif type(item) is list:
            _require(len(item) <= 20_000, 'Checkpoint array is too long')
            for child in item:
                visit(child, depth + 1)
        elif type(item) is dict:
            _require(len(item) <= 20_000 and all(type(k) is str for k in item),
                     'Checkpoint object keys must be strings')
            for key, child in item.items():
                visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            raise CheckpointValidationError('Checkpoint must contain JSON primitives only')

    visit(value)
    _require(len(json.dumps(value, allow_nan=False, separators=(',', ':')).encode('utf-8')) <= MAX_BYTES,
             'Checkpoint exceeds the bounded JSON size')


def _plain(value: object) -> object:
    # Validated shared circuits contain read-only mapping proxies. Reading their
    # fields directly avoids deepcopy/pickle, and retains their exact contents.
    if is_dataclass(value):
        return {field.name: _plain(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(_plain(value), sort_keys=True, separators=(',', ':'),
                                   allow_nan=False).encode('utf-8')).hexdigest()


@lru_cache(maxsize=1)
def _implementation_sha256() -> str:
    root = Path(__file__).resolve().parents[1]
    # Relative names plus bytes bind both the algorithm and its composition;
    # archives and mutable run data are deliberately excluded.
    return _digest({name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                    for name in _MODEL_FILES})


def _metadata(sim: GymSimulation) -> dict:
    _require(1 <= len(sim.bank) <= 10, 'Unsupported gym bank')
    for fly in sim.bank:
        _require(type(fly.brain.network) is ConnectomeNetwork,
                 'Checkpoint supports the compact network only')
    first = sim.bank[0]
    env, floor = sim.environment, sim.equipment
    circuits = {}

    def circuit_sha(circuit):
        if id(circuit) not in circuits:
            circuits[id(circuit)] = _digest(circuit)
        return circuits[id(circuit)]

    configuration = {
        'world': [env.width, env.height, env.odor_length_scale],
        'food_spawn': asdict(env.food_spawner.config) if env.food_spawner else None,
        'station': asdict(sim.station),
        'equipment': [{k: v for k, v in asdict(s).items() if k != 'load'}
                      for s in floor.stations] if floor else None,
        'continuous_training': floor._continuous_training if floor else None,
        'flies': [{
            'id': f.id, 'runtime': circuit_sha(f.brain.network.circuit),
            'leak': f.brain.network._leak,
            'body_limits': [f.body.maximum_speed, f.body.maximum_turn_rate],
            'physiology': [f.physiology.metabolism_per_second, f.physiology.digestion_efficiency],
            'sensors': asdict(f.sensors), 'readout': asdict(f.readout),
            'food': [circuit_sha(f.brain.food_learning.circuit), asdict(f.brain.food_learning.config)],
            'gym': [circuit_sha(f.brain.gym_learning.circuit), asdict(f.brain.gym_learning.config)],
        } for f in sim.bank],
    }
    return {
        'dataset': first.brain.network.circuit.dataset,
        'source_weights_sha256': first.brain.food_learning.circuit.source_weights_sha256,
        'runtime_sha256': circuit_sha(first.brain.network.circuit),
        'food_circuit_sha256': circuit_sha(first.brain.food_learning.circuit),
        'gym_circuit_sha256': circuit_sha(first.brain.gym_learning.circuit),
        'implementation_sha256': _implementation_sha256(),
        'configuration_sha256': _digest(configuration),
    }


def _pairs(mapping: dict) -> list:
    return [[key, value] for key, value in mapping.items()]


def _learner_state(learner: MushroomBodyLearning) -> dict:
    memory = asdict(learner.memory)
    memory['synapses'] = list(memory['synapses'])
    return {'memory': memory, 'eligibility': _pairs(learner._eligibility),
            'active_kcs': learner._active_kcs}


def _frame_state(frame: TelemetryFrame | None) -> dict | None:
    if frame is None:
        return None
    data = asdict(frame)
    data['trail'] = [list(point) for point in frame.trail]
    data['neural'] = {'activity': _pairs(frame.neural.activity_by_body),
                      'roles': dict(frame.neural.activity_by_role),
                      'labels': _pairs(frame.neural.labels_by_body)}
    return data


def snapshot(sim: GymSimulation) -> dict[str, object]:
    """Return a detached, bounded JSON document for one completed model boundary."""
    env, floor = sim.environment, sim.equipment
    spawner = None
    if env.food_spawner is not None:
        version, words, gaussian = env.food_spawner.rng.getstate()
        spawner = {'time_remaining': env.food_spawner._time_remaining,
                   'rng': [version, list(words), gaussian]}
    state = {
        'step': sim.step_count, 'elapsed': sim.elapsed, 'seed': sim.seed,
        'population': sim.population, 'pending_population': sim._pending_population,
        'environment': {'food': asdict(env.food) if env.food else None, 'spawner': spawner},
        'equipment': None if floor is None else {
            'loads': [[s.id, s.load] for s in floor.stations],
            'occupants': _pairs(floor._occupants),
            'pending_loads': [[station, load, command] for station, (load, command) in floor._pending_loads.items()],
            'load_events': list(floor._load_events),
            'pending_exercises': [[fly, station, command] for fly, (station, command) in floor._pending_exercises.items()],
            'exercise_events': list(floor._exercise_events),
        },
        'flies': [{
            'id': f.id, 'body': asdict(f.body.state), 'hunger': f.physiology.hunger,
            'training': asdict(f.training), 'exercise': asdict(f.exercise),
            'learning_enabled': f.brain.learning_enabled,
            'network_activity': _pairs(f.brain.network._activity),
            'food_learning': _learner_state(f.brain.food_learning),
            'gym_learning': _learner_state(f.brain.gym_learning),
            'trail': [list(point) for point in f.trail], 'latest': _frame_state(f.latest),
            'feedback_profile': f.feedback_profile, 'last_feedback': asdict(f.last_feedback),
            'feedback_step': f.feedback_step, 'feedback_elapsed': f.feedback_elapsed,
        } for f in sim.bank],
    }
    document = {'format': FORMAT, 'version': VERSION, 'metadata': _metadata(sim), 'state': state}
    _safe_json(document)
    return document


def _vector(value: object, ids: tuple[int, ...]) -> dict[int, float]:
    rows = _list(value, len(ids), len(ids))
    result = {}
    for expected, row in zip(ids, rows, strict=True):
        row = _list(row, 2, 2)
        _require(_integer(row[0], 1) == expected, 'Checkpoint has reordered or unknown official IDs')
        result[expected] = _number(row[1])
    return result


def _numeric_record(value: object, cls: type, bounds: dict) -> object:
    data = _record(value, (field.name for field in fields(cls)))
    return cls(**{key: (_integer(item, *bounds[key][1:]) if bounds[key][0] == 'int'
                        else _number(item, *bounds[key])) for key, item in data.items()})


_BODY = {'x': (-1e6, 1e6), 'y': (-1e6, 1e6), 'heading': (-1e6, 1e6)}
_FOOD = {'x': (-1e6, 1e6), 'y': (-1e6, 1e6), 'odor_strength': (0, 1e6),
         'visual_contrast': (0, 1e6), 'radius': (1e-9, 1e6)}
_TRAINING = {key: (0, 1) for key in ('set_progress', 'effort', 'fatigue', 'reward')}
_TRAINING.update(sets=('int', 0, MAX_COUNTER), fitness=(0, 1.5),
                 total_work=(0, 1e12), distance=(0, 1e12))


def _food(value: object) -> Food | None:
    return None if value is None else _numeric_record(value, Food, _FOOD)


def _trail(value: object) -> list[tuple[float, float]]:
    return [tuple(_number(axis, -1e6, 1e6) for axis in _list(point, 2, 2))
            for point in _list(value, 80)]


def _learner(value: object, target: MushroomBodyLearning) -> tuple:
    data = _record(value, ('memory', 'eligibility', 'active_kcs'))
    memory = _record(data['memory'], (f.name for f in fields(MemoryState)))
    template = target.memory
    for name in ('schema_version', 'dataset', 'weights_sha256', 'model'):
        _require(type(memory[name]) is type(getattr(template, name))
                 and memory[name] == getattr(template, name), 'Incompatible learned memory')
    expected = {(e.body_pre, e.body_post, e.weight) for e in target.circuit.plastic_edges}
    synapses = []
    for item in _list(memory['synapses'], len(expected), len(expected)):
        item = _record(item, (f.name for f in fields(SynapseMemory)))
        edge = (_integer(item['body_pre'], 1), _integer(item['body_post'], 1),
                _integer(item['baseline_weight'], 1))
        _require(edge in expected, 'Unknown or duplicate plastic edge')
        expected.remove(edge)
        synapses.append(SynapseMemory(*edge, _number(item['multiplier'])))
    saved = MemoryState(template.schema_version, template.dataset, template.weights_sha256,
                        template.model, _integer(memory['reward_events']),
                        _number(memory['total_reward'], 0, 1e12), tuple(synapses))
    return (saved, _vector(data['eligibility'], tuple(target._eligibility)),
            _integer(data['active_kcs'], 0, len(target._eligibility)))


def _exercise(value: object, station_kinds: dict[str, str]) -> ExerciseState:
    data = _record(value, (f.name for f in fields(ExerciseState)))
    station, kind = data['station_id'], data['kind']
    _require((station is None and kind is None) or
             (type(station) is str and station in station_kinds and kind == station_kinds[station]),
             'Exercise does not match a known apparatus')
    _require(type(data['phase']) is str and data['phase'] in ('free', 'lifting', 'lowering', 'recovery'),
             'Unknown exercise phase')
    result = {key: data[key] for key in ('station_id', 'kind', 'phase')}
    for key in ('repetitions', 'completed_sets', 'rep_in_set'):
        result[key] = _integer(data[key], 0, 2 if key == 'rep_in_set' else MAX_COUNTER)
    for key in ('joint_position', 'recovery_remaining', 'body_elevation'):
        result[key] = _number(data[key], 0, 1 if key == 'joint_position' else 1e6)
    for key in ('joint_velocity', 'body_pitch', 'body_roll'):
        result[key] = _number(data[key], -1e6, 1e6)
    return ExerciseState(**result)


def _frame(value: object, fly, step: int, elapsed: float, activity: dict) -> TelemetryFrame | None:
    if value is None:
        return None
    data = _record(value, (f.name for f in fields(TelemetryFrame)))
    neural = _record(data['neural'], ('activity', 'roles', 'labels'))
    rates = _vector(neural['activity'], tuple(activity))
    _require(rates == activity, 'Latest telemetry differs from recurrent network state')
    expected_roles = {role: rates[body] for role, body in fly.brain.network.circuit.motor_roles.items()}
    roles = _record(neural['roles'], expected_roles)
    _require(all(_number(roles[role]) == rate for role, rate in expected_roles.items()),
             'Motor role readings differ from official body readings')
    labels = {}
    for row in _list(neural['labels'], len(activity), len(activity)):
        row = _list(row, 2, 2)
        key = _integer(row[0], 1)
        _require(key not in labels and key in activity, 'Unknown or duplicate neural label')
        labels[key] = _text(row[1], 256)
    _require(labels == fly.brain.network._labels, 'Neural labels differ from validated runtime')
    learning = _record(data['learning'], (f.name for f in fields(LearningSnapshot)))
    learned = LearningSnapshot(*[_number(learning[key]) for key in
                                ('reward', 'association_strength', 'mean_eligibility')],
                               _integer(learning['active_kcs'], 0, len(fly.brain.food_learning._eligibility)),
                               _boolean(learning['changed']))
    return TelemetryFrame(_integer(data['step'], 0, step), _number(data['elapsed'], 0, elapsed),
        _numeric_record(data['body'], BodyState, _BODY), _food(data['food']), _number(data['hunger']),
        _numeric_record(data['sensory'], SensoryFrame, {f.name: (0, 1) for f in fields(SensoryFrame)}),
        NeuralSnapshot(rates, dict(roles), labels),
        _numeric_record(data['motor'], MotorDrive, {'forward': (0, 1), 'turn': (-1, 1)}),
        _boolean(data['ate']), tuple(_trail(data['trail'])), learned)


def _rng(value: object) -> tuple:
    data = _list(value, 3, 3)
    _require(_integer(data[0]) == 3, 'Unsupported random generator state')
    words = _list(data[1], 625, 625)
    state = (3, tuple(_integer(v, 0, 624 if i == 624 else 2 ** 32 - 1)
                      for i, v in enumerate(words)),
             None if data[2] is None else _number(data[2], -1e6, 1e6))
    random.Random(0).setstate(state)
    return state


def _equipment(value: object, sim: GymSimulation, population: int) -> dict | None:
    floor = sim.equipment
    if floor is None:
        _require(value is None, 'Unexpected apparatus state')
        return None
    data = _record(value, ('loads', 'occupants', 'pending_loads', 'load_events',
                           'pending_exercises', 'exercise_events'))
    stations = {s.id: s for s in floor.stations}
    active = {f.id for f in sim.bank[:population]}
    loads = {}
    for station, row in zip(floor.stations, _list(data['loads'], len(stations), len(stations)), strict=True):
        row = _list(row, 2, 2)
        _require(row[0] == station.id and type(row[0]) is str, 'Unknown or reordered station')
        loads[station.id] = _number(row[1], .1, 3)
    occupants = {}
    for row in _list(data['occupants'], len(stations)):
        row = _list(row, 2, 2)
        station, fly = _text(row[0]), _text(row[1])
        _require(station in stations and station not in occupants and fly in active
                 and fly not in occupants.values(), 'Invalid apparatus occupancy')
        occupants[station] = fly
    pending_loads = {}
    for row in _list(data['pending_loads'], len(stations)):
        row = _list(row, 3, 3)
        station = _text(row[0])
        _require(station in stations and station not in pending_loads, 'Invalid pending load')
        pending_loads[station] = (_number(row[1], .1, 3), _text(row[2]))
    pending_exercises, reserved = {}, set()
    # A population decrease releases grip but retains each inactive individual's
    # queued setup. It can become effective when that same fly is reactivated.
    known_flies = {fly.id for fly in sim.bank}
    for row in _list(data['pending_exercises'], len(known_flies)):
        row = _list(row, 3, 3)
        fly, station, command = (_text(item) for item in row)
        _require(fly in known_flies and fly not in pending_exercises and station in stations
                 and station not in occupants and station not in reserved, 'Invalid pending exercise')
        pending_exercises[fly] = station, command
        reserved.add(station)
    return {'loads': loads, 'occupants': occupants, 'pending_loads': pending_loads,
            'pending_exercises': pending_exercises,
            'load_events': [_text(v) for v in _list(data['load_events'], 1000)],
            'exercise_events': [_text(v) for v in _list(data['exercise_events'], 1000)]}


def restore(sim: GymSimulation, data: object) -> None:
    """Validate then restore in place, retaining shared circuit/network identities.

    Invalid input leaves the supplied simulation untouched. The gateway must call
    this at a completed boundary, before exposing a new server to its observers.
    """
    _safe_json(data)
    document = _record(data, ('format', 'version', 'metadata', 'state'))
    _require(document['format'] == FORMAT and type(document['version']) is int
             and document['version'] == VERSION, 'Unsupported session checkpoint format/version')
    _require(document['metadata'] == _metadata(sim), 'Checkpoint source or model configuration is incompatible')
    state = _record(document['state'], ('step', 'elapsed', 'seed', 'population', 'pending_population',
                                        'environment', 'equipment', 'flies'))
    step, elapsed = _integer(state['step']), _number(state['elapsed'], 0, 1e12)
    seed = None if state['seed'] is None else _integer(state['seed'], -MAX_COUNTER)
    population = _integer(state['population'], 1, len(sim.bank))
    pending = None if state['pending_population'] is None else _integer(state['pending_population'], 1, len(sim.bank))
    env = _record(state['environment'], ('food', 'spawner'))
    food = _food(env['food'])
    spawner = None
    if sim.environment.food_spawner is None:
        _require(env['spawner'] is None, 'Unexpected food generator')
    else:
        source = _record(env['spawner'], ('time_remaining', 'rng'))
        spawner = (_number(source['time_remaining'], 0, 1e6), _rng(source['rng']))
    equipment = _equipment(state['equipment'], sim, population)
    station_kinds = {s.id: s.kind for s in sim.equipment.stations} if sim.equipment else {}
    staged = []
    keys = ('id', 'body', 'hunger', 'training', 'exercise', 'learning_enabled', 'network_activity',
            'food_learning', 'gym_learning', 'trail', 'latest', 'feedback_profile', 'last_feedback',
            'feedback_step', 'feedback_elapsed')
    for fly, raw in zip(sim.bank, _list(state['flies'], len(sim.bank), len(sim.bank)), strict=True):
        raw = _record(raw, keys)
        _require(type(raw['id']) is str and raw['id'] == fly.id, 'Unknown or reordered fly identity')
        body = _numeric_record(raw['body'], BodyState, _BODY)
        training = _numeric_record(raw['training'], TrainingState, _TRAINING)
        exercise = _exercise(raw['exercise'], station_kinds)
        if equipment is not None:
            held = next((s for s, identity in equipment['occupants'].items() if identity == fly.id), None)
            _require(held == exercise.station_id and training.sets == exercise.completed_sets,
                     'Grip or completed-set state is inconsistent')
        activity = _vector(raw['network_activity'], tuple(fly.brain.network._activity))
        profile = raw['feedback_profile']
        _require(type(profile) is str and profile in FEEDBACK_PROFILES, 'Unknown apparatus feedback profile')
        feedback = _record(raw['last_feedback'], (f.name for f in fields(ApparatusFeedback)))
        _require(feedback['profile'] == profile, 'Feedback profile differs from its latched reading')
        staged.append((body, _number(raw['hunger']), training, exercise,
            _boolean(raw['learning_enabled']), activity,
            _learner(raw['food_learning'], fly.brain.food_learning),
            _learner(raw['gym_learning'], fly.brain.gym_learning), _trail(raw['trail']),
            _frame(raw['latest'], fly, step, elapsed, activity), profile,
            ApparatusFeedback(profile, _number(feedback['indicator_left']), _number(feedback['indicator_right'])),
            _integer(raw['feedback_step'], 0, step), _number(raw['feedback_elapsed'], 0, elapsed)))
    # Everything above is detached validation; below are non-throwing assignments
    # to existing domain objects, so shared source circuits remain shared.
    sim.step_count, sim.elapsed, sim.seed = step, elapsed, seed
    sim.population, sim._pending_population = population, pending
    sim.environment.food = food
    if spawner is not None:
        sim.environment.food_spawner._time_remaining = spawner[0]
        sim.environment.food_spawner.rng.setstate(spawner[1])
    if equipment is not None:
        floor = sim.equipment
        floor.stations = tuple(replace(s, load=equipment['loads'][s.id]) for s in floor.stations)
        floor._by_id = {s.id: s for s in floor.stations}
        floor._occupants = equipment['occupants']
        floor._pending_loads, floor._pending_exercises = equipment['pending_loads'], equipment['pending_exercises']
        floor._load_events, floor._exercise_events = equipment['load_events'], equipment['exercise_events']
    for fly, saved in zip(sim.bank, staged, strict=True):
        (body, hunger, fly.training, fly.exercise, enabled, activity, food_learning, gym_learning,
         fly.trail, fly.latest, fly.feedback_profile, fly.last_feedback, fly.feedback_step, fly.feedback_elapsed) = saved
        fly.body.x, fly.body.y, fly.body.heading = body.x, body.y, body.heading
        fly.physiology.hunger = hunger
        fly.brain.learning_enabled = enabled
        fly.brain.food_adapter.learning = fly.brain.food_learning if enabled else None
        fly.brain.network._activity = activity
        for learner, saved_learner in ((fly.brain.food_learning, food_learning), (fly.brain.gym_learning, gym_learning)):
            learner.memory, learner._eligibility, learner._active_kcs = saved_learner
