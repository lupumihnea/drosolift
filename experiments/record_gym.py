"""Record fresh, source-validated gym observations for backend-free replay.

Run as ``python -m experiments.record_gym --output data/runs/bench --seconds 20``.
The recording is JSON, version 1; the adjacent CSV contains matching equipment
samples. This command never loads, resets or overwrites a user's learned memory.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import hashlib
import io
import json
import math
from pathlib import Path
from uuid import uuid4

from brain.gym_circuit import GymCircuits, load_gym_circuits
from experiments.experiment_002 import create_gym
from frontend.gym_telemetry import gym_control_state, gym_frame_message
from frontend.telemetry import hello_message
from world.equipment import ACTUATOR_FORCE, DAMPING, MAX_PHYSICS_STEP, validate_exercise_kind, validate_load
from world.apparatus_feedback import FEEDBACK_PROFILES, validate_feedback_profile


def record_gym(root: Path, *, duration: float, dt: float, load: float,
               seed: int, learning_enabled: bool,
               circuits: GymCircuits | None = None, exercise: str = 'bench_press',
               feedback: str = 'none') -> dict[str, object]:
    """Sample the normal GymSimulation, including exact zeros and initial state."""
    if type(seed) is not int or type(learning_enabled) is not bool:
        raise ValueError('Seed must be an integer and learning_enabled a boolean')
    if not math.isfinite(duration) or not 1 <= duration <= 3600:
        raise ValueError('Duration must be finite within 1..3600 seconds')
    if not math.isfinite(dt) or not .01 <= dt <= .1:
        raise ValueError('Sampling timestep must be finite within .01..0.1 seconds')
    steps = round(duration / dt)
    if not math.isclose(steps * dt, duration, abs_tol=1e-8):
        raise ValueError('Duration must be a whole number of timesteps')
    load = validate_load(load)
    exercise = validate_exercise_kind(exercise)
    feedback = validate_feedback_profile(feedback)
    circuits = circuits or load_gym_circuits(root)
    simulation = create_gym(*circuits, population=1, seed=seed, learning_enabled=learning_enabled, feedback=feedback)
    if exercise != 'bench_press' or feedback != 'none':
        simulation.request_exercise('fly-1', exercise, 'recording-initial-exercise')
        simulation.apply_pending_exercises()
        simulation.equipment.take_exercise_events()
    station_id = simulation.flies[0].exercise.station_id or 'station-1'
    simulation.equipment.request_load(station_id, load, 'recording-initial-load')
    simulation.equipment.apply_racked_loads(tuple(fly.exercise for fly in simulation.flies))
    simulation.equipment.take_load_events()
    hello = hello_message(backend='compact', dataset=circuits[0].dataset, fps=1 / dt,
                          world_width=simulation.environment.width, world_height=simulation.environment.height)
    hello.update(schema=3, experiment='gym', population=1, station=asdict(simulation.station),
                 equipment=[asdict(station) for station in simulation.equipment.stations])
    run_id = str(uuid4())
    frames = [gym_frame_message(simulation.snapshot())]
    controls = [gym_control_state(simulation, run_id)]
    for _ in range(steps):
        frames.append(gym_frame_message(simulation.step(dt)))
        controls.append(gym_control_state(simulation, run_id))
    paths = ['data/circuits/gym-v1-runtime.json', 'data/circuits/gym-v1-learning.json',
             'data/circuits/foraging-v1-learning.json', 'data/malecns/v1.0/source-manifest.json']
    hashes = {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}
    source = json.loads((root / paths[-1]).read_text(encoding='utf-8'))
    ids = sorted(node.body_id for node in circuits[0].nodes)
    return {'format': 'drosolift-recording', 'version': 1,
            'metadata': {'run_id': run_id, 'seed': seed, 'dt': dt, 'duration': steps * dt,
                'exercise': exercise, 'feedback_profile': feedback,
                'feedback_manifest': json.loads((root / 'data/circuits/apparatus-visual-v1.json').read_text(encoding='utf-8')),
                'control_history': controls,
                'learning_enabled': learning_enabled, 'memory_initialization': 'fresh bounded multipliers; no persistent memory',
                'load': load, 'load_unit': 'model force units; gravity=1',
                'time_base': 'simulation elapsed seconds; frames[0] is the pre-step initial state',
                'activity_unit': 'dimensionless normalized rate-like activity; no spike events',
                'model': ('DrosoLift gym-v1' if feedback == 'none' else 'DrosoLift gym-apparatus-visual-v1') + ' / upstream 2c5a03aa90f01048f011e13546b4d7fffc693945',
                'model_scope': {'simulated_neurons': len(ids), 'body_ids': ids,
                                'anatomical_overview': 'separate measured atlas positions; most are unobserved'},
                'source': source, 'circuit_sha256': hashes,
                'mechanics': {'actuator_force_gain': ACTUATOR_FORCE, 'damping': DAMPING,
                              'max_physics_step': MAX_PHYSICS_STEP,
                              'forward_readout': 'clamp(3 * 0.5 * (forward_left + forward_right),0,1)',
                              'force_mapping': '6 * clamp(forward,0,1) * min(1,capacity); 0 during lowering',
                              'capacity': '(1 - 0.75*fatigue) * fitness',
                              'work': 'sum(load * travel * max(0,dq))',
                              'registration': 'authored body pose; scientific overview uses native atlas coordinates'},
                'initial_state': frames[0]},
            'hello': hello, 'frames': frames}


def recording_csv(recording: dict[str, object]) -> str:
    """Export exact equipment observations using the recording's simulation clock."""
    output = io.StringIO(newline='')
    fields = ['index', 'step', 'elapsed', 'load', 'station_id', 'phase', 'joint_position',
              'joint_velocity', 'repetitions', 'completed_sets', 'total_work', 'motor_forward']
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for index, frame in enumerate(recording['frames']):
        fly = frame['flies'][0]
        exercise = fly['exercise']
        writer.writerow({'index': index, 'step': frame['step'], 'elapsed': frame['elapsed'],
            'load': recording['metadata']['load'],
            **{key: exercise[key] for key in ['station_id', 'phase', 'joint_position',
                'joint_velocity', 'repetitions', 'completed_sets']},
            'total_work': fly['training']['total_work'], 'motor_forward': fly['frame']['motor']['forward']})
    return output.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/runs/bench'))
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--dt', type=float, default=.1)
    parser.add_argument('--load', type=float, default=.6)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--learning', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('--exercise', choices=('bench_press', 'bicep_curl'), default='bench_press')
    parser.add_argument('--feedback', choices=FEEDBACK_PROFILES, default='none')
    options = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        recording = record_gym(root, duration=options.seconds, dt=options.dt, load=options.load,
                               seed=options.seed, learning_enabled=options.learning,
                               exercise=options.exercise, feedback=options.feedback)
    except ValueError as error:
        parser.error(str(error))
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.with_suffix('.json').write_text(json.dumps(recording, separators=(',', ':'), allow_nan=False) + '\n', encoding='utf-8')
    options.output.with_suffix('.csv').write_text(recording_csv(recording), encoding='utf-8')
    last = recording['frames'][-1]['flies'][0]
    print(f'Recorded {len(recording["frames"])} frames, {last["exercise"]["repetitions"]} repetitions, '
          f'{last["training"]["total_work"]:.6f} positive work to {options.output.with_suffix(".json")}')


if __name__ == '__main__':
    main()
