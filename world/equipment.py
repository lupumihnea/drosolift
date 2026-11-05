"""Loaded scalar joints and physical grip constraints, not a behavior policy.

All actuator, contact, pose and recovery constants are illustrative assumptions
documented in docs/science/equipment.md; none encode biological exercise roles.
"""

from dataclasses import dataclass, replace
import math
from typing import Literal

from simulation.signals import MotorDrive
from world.environment import Environment
from world.fly import FlyBody
from world.gym import TrainingState
from world.sensors import SensorRig


EquipmentKind = Literal['bench_press', 'bicep_curl']
ExercisePhase = Literal['free', 'lifting', 'lowering', 'recovery']
MAX_PHYSICS_STEP = .01
RECOVERY_SECONDS = 4.0
CONTINUOUS_RECOVERY_SECONDS = 2.0
ACTUATOR_FORCE = 6.0
DAMPING = 3.0
MIN_LOAD = .1
MAX_LOAD = 3.0


class ExerciseUnavailableError(ValueError):
    """No unoccupied station can satisfy this explicit apparatus setup."""


def validate_exercise_kind(value: object) -> EquipmentKind:
    if value not in ('bench_press', 'bicep_curl') or not isinstance(value, str):
        raise ValueError('Exercise must be bench_press or bicep_curl')
    return value


def validate_load(value: object) -> float:
    """Only finite JSON numbers in the declared apparatus calibration are valid."""
    if type(value) not in (float, int) or not math.isfinite(value) or not MIN_LOAD <= value <= MAX_LOAD:
        raise ValueError(f'Load must be finite within {MIN_LOAD}..{MAX_LOAD} model force units')
    return float(value)


@dataclass(frozen=True, slots=True)
class EquipmentStation:
    """Fixed body/grip anchor and vertical load travel in world model units."""

    id: str
    kind: EquipmentKind
    x: float
    y: float
    heading: float
    load: float
    travel: float
    grip_radius: float

    def __post_init__(self) -> None:
        if not self.id or self.kind not in ('bench_press', 'bicep_curl'):
            raise ValueError('Equipment needs an identity and supported kind')
        if not all(math.isfinite(v) for v in
                   (self.x, self.y, self.heading, self.load, self.travel, self.grip_radius)):
            raise ValueError('Equipment geometry must be finite')
        if min(self.load, self.travel, self.grip_radius) <= 0:
            raise ValueError('Equipment load, travel and grip radius must be positive')

    def odor_at(self, x: float, y: float) -> float:
        return 1.0 / (1.0 + ((x - self.x) ** 2 + (y - self.y) ** 2) / 9.0)


@dataclass(slots=True)
class ExerciseState:
    """Per-fly authoritative joint, stroke counts, grip and support pose."""

    station_id: str | None = None
    kind: EquipmentKind | None = None
    phase: ExercisePhase = 'free'
    joint_position: float = 0.0
    joint_velocity: float = 0.0
    repetitions: int = 0
    completed_sets: int = 0
    rep_in_set: int = 0
    recovery_remaining: float = 0.0
    body_elevation: float = 0.0
    body_pitch: float = 0.0
    body_roll: float = 0.0

    @property
    def set_progress(self) -> float:
        if self.station_id is None:
            return self.rep_in_set / 3.0
        stroke = self.joint_position / 2.0
        if self.phase == 'lowering':
            stroke = 1.0 - stroke
        return (self.rep_in_set + stroke) / 3.0


class EquipmentFloor:
    """Own exclusive station grips; only contact can constrain a body's pose."""

    def __init__(self, stations: tuple[EquipmentStation, ...], *,
                 continuous_training: bool = False) -> None:
        if not 1 <= len(stations) <= 10 or len({s.id for s in stations}) != len(stations):
            raise ValueError('Equipment requires 1..10 uniquely named stations')
        self.stations = stations
        self._by_id = {station.id: station for station in stations}
        self._occupants: dict[str, str] = {}
        self._continuous_training = continuous_training
        self._pending_loads: dict[str, tuple[float, str]] = {}
        self._load_events: list[str] = []
        self._pending_exercises: dict[str, tuple[str, str]] = {}
        self._exercise_events: list[str] = []

    def request_exercise(self, fly_id: str, kind: object, command_id: str,
                         exercise: ExerciseState) -> None:
        """Reserve imposed apparatus setup; moving joints finish their return first."""
        kind = validate_exercise_kind(kind)
        if fly_id in self._pending_exercises:
            raise ValueError('An exercise change is already pending for this fly')
        if exercise.kind == kind and self._occupants.get(exercise.station_id) == fly_id:
            self._exercise_events.append(command_id)
            return
        reserved = {station_id for station_id, _ in self._pending_exercises.values()}
        station = next((station for station in self.stations if station.kind == kind
                        and station.id not in self._occupants and station.id not in reserved), None)
        if station is None:
            raise ExerciseUnavailableError('No free station for the requested exercise')
        self._pending_exercises[fly_id] = station.id, command_id

    def exercise_state(self, fly_id: str, exercise: ExerciseState) -> dict[str, object]:
        pending = self._pending_exercises.get(fly_id)
        return {'fly_id': fly_id, 'kind': exercise.kind, 'station_id': exercise.station_id,
                'pending_kind': self._by_id[pending[0]].kind if pending else None,
                'pending_station_id': pending[0] if pending else None,
                'pending_command_id': pending[1] if pending else None}

    def take_exercise_events(self) -> tuple[str, ...]:
        events = tuple(self._exercise_events)
        self._exercise_events.clear()
        return events

    def apply_racked_exercises(self, flies: tuple[tuple[str, FlyBody, ExerciseState], ...]) -> tuple[str, ...]:
        applied = []
        for fly_id, body, exercise in flies:
            if self._apply_exercise_at_bottom(fly_id, body, exercise):
                applied.append(fly_id)
        return tuple(applied)

    def _apply_exercise_at_bottom(self, fly_id: str, body: FlyBody, exercise: ExerciseState) -> bool:
        if fly_id not in self._pending_exercises or exercise.joint_position != 0 or exercise.joint_velocity != 0:
            return False
        station_id, command_id = self._pending_exercises.pop(fly_id)
        if self._occupants.get(exercise.station_id) == fly_id:
            del self._occupants[exercise.station_id]
        station = self._by_id[station_id]
        self._occupants[station_id] = fly_id
        self._support(body, exercise, station)
        exercise.phase = 'recovery'
        exercise.recovery_remaining = CONTINUOUS_RECOVERY_SECONDS
        self._exercise_events.append(command_id)
        return True

    @staticmethod
    def _support(body: FlyBody, exercise: ExerciseState, station: EquipmentStation) -> None:
        body.x, body.y, body.heading = station.x, station.y, station.heading
        exercise.station_id, exercise.kind = station.id, station.kind
        exercise.body_elevation = 1.5 if station.kind == 'bench_press' else .5
        exercise.body_pitch = 0.0 if station.kind == 'bench_press' else .55
        exercise.body_roll = math.pi if station.kind == 'bench_press' else 0.0

    def request_load(self, station_id: str, load: object, command_id: str) -> None:
        """Queue an absolute load without altering a moving joint's current stroke."""
        value = validate_load(load)
        if station_id not in self._by_id:
            raise ValueError('Unknown equipment station')
        if station_id in self._pending_loads:
            raise ValueError('A load change is already pending for this station')
        self._pending_loads[station_id] = value, command_id

    def load_state(self) -> list[dict[str, object]]:
        """Return current and requested loads independently of legacy snapshots."""
        return [{'station_id': station.id, 'load': station.load,
                 'pending_load': self._pending_loads.get(station.id, (None, None))[0],
                 'pending_command_id': self._pending_loads.get(station.id, (None, None))[1]}
                for station in self.stations]

    def take_load_events(self) -> tuple[str, ...]:
        """Consume correlations applied in the enclosing authoritative model step."""
        events = tuple(self._load_events)
        self._load_events.clear()
        return events

    def apply_racked_loads(self, exercises: tuple[ExerciseState, ...]) -> None:
        """Allow updates at rest even when the model clock is paused."""
        by_station = {state.station_id: state for state in exercises if state.station_id is not None}
        for station_id in tuple(self._pending_loads):
            state = by_station.get(station_id)
            if state is None and station_id not in self._occupants:
                self._apply_load(station_id)
            elif state is not None:
                self._apply_load_at_bottom(state)

    def _apply_load_at_bottom(self, exercise: ExerciseState) -> None:
        if (exercise.station_id in self._pending_loads and exercise.joint_position == 0.0
                and exercise.joint_velocity == 0.0 and exercise.phase in ('lifting', 'recovery')):
            self._apply_load(exercise.station_id)

    def _apply_load(self, station_id: str) -> None:
        load, command_id = self._pending_loads.pop(station_id)
        station = replace(self._by_id[station_id], load=load)
        self._by_id[station_id] = station
        self.stations = tuple(station if item.id == station_id else item for item in self.stations)
        self._load_events.append(command_id)

    @property
    def occupants(self) -> dict[str, str]:
        return dict(self._occupants)

    def sample(self, body: FlyBody, sensors: SensorRig = SensorRig()) -> tuple[float, float]:
        """Sample the strongest physical DM2 field at each distinct antenna."""
        c, s = math.cos(body.heading), math.sin(body.heading)
        x = body.x + c * sensors.antenna_forward_offset
        y = body.y + s * sensors.antenna_forward_offset
        side = sensors.antenna_side_offset
        return (max(station.odor_at(x - s * side, y + c * side) for station in self.stations),
                max(station.odor_at(x + s * side, y - c * side) for station in self.stations))

    def release(self, fly_id: str, exercise: ExerciseState) -> None:
        """Rack a removed/released grip without counting an unfinished stroke."""
        if self._occupants.get(exercise.station_id) == fly_id:
            del self._occupants[exercise.station_id]
        exercise.station_id = None
        exercise.kind = None
        exercise.joint_position = exercise.joint_velocity = 0.0
        exercise.body_elevation = exercise.body_pitch = exercise.body_roll = 0.0
        exercise.rep_in_set = 0
        exercise.recovery_remaining = RECOVERY_SECONDS
        exercise.phase = 'recovery'

    def advance(self, fly_id: str, body: FlyBody, drive: MotorDrive, dt: float,
                environment: Environment, training: TrainingState, exercise: ExerciseState) -> None:
        """Integrate every stop crossing; time alone never creates work or reps."""
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError('Equipment timestep must be finite and positive')
        count = max(1, math.ceil(dt / MAX_PHYSICS_STEP))
        step = dt / count
        previous_sets, previous_work = training.sets, training.total_work
        for _ in range(count):
            distance = work = 0.0
            self._apply_exercise_at_bottom(fly_id, body, exercise)
            if exercise.station_id is None:
                exercise.recovery_remaining = max(0.0, exercise.recovery_remaining - step)
                if exercise.recovery_remaining < 1e-9:
                    exercise.recovery_remaining = 0.0
                exercise.phase = 'recovery' if exercise.recovery_remaining else 'free'
                if exercise.phase == 'free' and drive.forward > 0:
                    self._grip(fly_id, body, exercise)
            if exercise.station_id is not None:
                self._apply_load_at_bottom(exercise)
                station = self._by_id[exercise.station_id]
                if exercise.phase == 'recovery':
                    exercise.recovery_remaining = max(0.0, exercise.recovery_remaining - step)
                    if exercise.recovery_remaining < 1e-9:
                        exercise.recovery_remaining = 0.0
                        exercise.phase = 'lifting'
                else:
                    work = self._lift(fly_id, drive, step, station, training, exercise)
            else:
                x, y = body.x, body.y
                body.apply(MotorDrive(drive.forward * min(1.0, training.capacity), drive.turn), step)
                body.x, body.y = environment.constrain(body.x, body.y)
                distance = math.hypot(body.x - x, body.y - y)
            completed = exercise.completed_sets - training.sets
            training.advance_exercise(step, work, distance, completed, exercise.set_progress)
        training.reward = .9 if training.sets > previous_sets else 0.0
        training.effort = min(1.0, (training.total_work - previous_work) / (.6 * dt))

    def _grip(self, fly_id: str, body: FlyBody, exercise: ExerciseState) -> None:
        for station in self.stations:
            if station.id in self._occupants:
                continue
            if any(reserved == station.id for reserved, _ in self._pending_exercises.values()):
                continue
            if math.hypot(body.x - station.x, body.y - station.y) > station.grip_radius:
                continue
            # The docking support constrains only an already-contacting body.
            self._occupants[station.id] = fly_id
            self._support(body, exercise, station)
            exercise.phase = 'lifting'
            return

    def _lift(self, fly_id: str, drive: MotorDrive, dt: float, station: EquipmentStation,
              training: TrainingState, exercise: ExerciseState) -> float:
        force = ACTUATOR_FORCE * min(1.0, max(0.0, drive.forward)) * min(1.0, training.capacity)
        if exercise.phase == 'lowering':
            force = 0.0
        acceleration = (force - station.load) / (station.load * station.travel)
        acceleration -= DAMPING * exercise.joint_velocity
        exercise.joint_velocity += acceleration * dt
        previous = exercise.joint_position
        exercise.joint_position = min(1.0, max(0.0, previous + exercise.joint_velocity * dt))
        work = station.load * station.travel * max(0.0, exercise.joint_position - previous)
        if exercise.joint_position >= 1.0:
            exercise.phase = 'lowering'
            exercise.joint_velocity = 0.0
        elif exercise.joint_position <= 0.0:
            exercise.joint_velocity = 0.0
            if exercise.phase == 'lowering':
                exercise.repetitions += 1
                exercise.rep_in_set += 1
                exercise.phase = 'lifting'
                if exercise.rep_in_set == 3:
                    exercise.completed_sets += 1
                    if self._continuous_training:
                        exercise.rep_in_set = 0
                        exercise.recovery_remaining = CONTINUOUS_RECOVERY_SECONDS
                        exercise.phase = 'recovery'
                    else:
                        self.release(fly_id, exercise)
        return work
