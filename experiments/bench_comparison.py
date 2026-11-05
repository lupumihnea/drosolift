"""A fixed-budget open-loop comparison using the gym's unchanged bench mechanics.

The neural condition replays an actual recorded motor waveform. Its four-second
presentation period is a declared experimental input, not a claim of neural
oscillation. The periodic control matches commanded positive actuator impulse
before fatigue scaling and the apparatus lowering/recovery gate.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
from uuid import uuid4

from simulation.signals import MotorDrive
from world.environment import Environment
from world.equipment import ACTUATOR_FORCE, MAX_PHYSICS_STEP, EquipmentFloor, EquipmentStation, ExerciseState, validate_load
from world.fly import FlyBody
from world.gym import TrainingState


def matched_periodic(neural: tuple[float, ...]) -> tuple[float, ...]:
    """Freeze a bounded rectangular controller with exactly the same cycle sum."""
    if not neural or any(not math.isfinite(x) or not 0 <= x <= 1 for x in neural):
        raise ValueError('Calibration requires finite normalized commands')
    total = math.fsum(neural)
    on_samples = max(math.ceil(len(neural) / 2), math.ceil(total))
    amplitude = total / on_samples
    return (amplitude,) * on_samples + (0.0,) * (len(neural) - on_samples)


def run_condition(waveform: tuple[float, ...], *, load: float, dt: float, cycles: int) -> dict:
    """Advance fresh real equipment, support and physiology for one frozen input."""
    load = validate_load(load)
    if not waveform or not math.isfinite(dt) or not .01 <= dt <= .1 or type(cycles) is not int or cycles <= 0:
        raise ValueError('Invalid finite experiment grid')
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in waveform):
        raise ValueError('Drive must be bounded')
    station = EquipmentStation('bench', 'bench_press', 0, 0, 0, load, .7, .45)
    equipment = EquipmentFloor((station,), continuous_training=True)
    body, training, exercise = FlyBody(0, 0, 0), TrainingState(), ExerciseState()
    environment = Environment(20, 12, None)
    initial = {'body': asdict(body), 'training': asdict(training), 'exercise': asdict(exercise)}
    rows = []
    maximum_position = 0.0
    physics_substeps = math.ceil(dt / MAX_PHYSICS_STEP)
    for index in range(len(waveform) * cycles):
        command = waveform[index % len(waveform)]
        # Observe the same physics grid so a top stop between saved samples is retained.
        for _ in range(physics_substeps):
            equipment.advance('fly-1', body, MotorDrive(command, 0), dt / physics_substeps, environment, training, exercise)
            maximum_position = max(maximum_position, exercise.joint_position)
        rows.append({'index': index + 1, 'elapsed': (index + 1) * dt,
            'motor_forward': command, 'commanded_force': ACTUATOR_FORCE * command,
            'joint_position': exercise.joint_position, 'joint_velocity': exercise.joint_velocity,
            'phase': exercise.phase, 'repetitions': exercise.repetitions,
            'completed_sets': exercise.completed_sets, 'positive_work': training.total_work,
            'fatigue': training.fatigue, 'fitness': training.fitness})
    return {'initial_state': initial, 'samples': rows, 'summary': {
        'load': load, 'duration': len(rows) * dt, 'period': len(waveform) * dt,
        'cycles': cycles, 'repetitions': exercise.repetitions,
        'completed_sets': exercise.completed_sets,
        'maximum_travel': maximum_position * station.travel,
        'positive_work': training.total_work,
        'commanded_positive_impulse': ACTUATOR_FORCE * math.fsum(waveform) * dt * cycles}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('data/runs/comparison'))
    parser.add_argument('--calibration-recording', type=Path)
    parser.add_argument('--cycles', type=int, default=15)
    options = parser.parse_args()
    if options.cycles <= 0:
        parser.error('Cycles must be positive')
    root = Path(__file__).resolve().parents[1]
    if options.calibration_recording:
        recording = json.loads(options.calibration_recording.read_text(encoding='utf-8'))
    else:
        from experiments.record_gym import record_gym
        recording = record_gym(root, duration=20, dt=.1, load=.6, seed=7, learning_enabled=False)
    if recording.get('format') != 'drosolift-recording' or recording.get('version') != 1:
        parser.error('Calibration must be a version1 actual gym recording')
    metadata = recording['metadata']
    if metadata['load'] != .6 or metadata['learning_enabled']:
        parser.error('Use separate load0.6 calibration with learning disabled')
    dt, start, period = float(metadata['dt']), 8.0, 4.0
    selected = [frame for frame in recording['frames'] if start < frame['elapsed'] <= start + period + 1e-8]
    if len(selected) != round(period / dt):
        parser.error('Calibration recording must cover8..12 simulation seconds')
    neural = tuple(frame['flies'][0]['frame']['motor']['forward'] for frame in selected)
    periodic = matched_periodic(neural)
    calibration = {'format': 'drosolift-bench-calibration', 'version': 1,
        'source_metadata': metadata, 'start_exclusive': start, 'end_inclusive': start + period,
        'neural_waveform': neural, 'periodic_waveform': periodic,
        'period_interpretation': 'authored4s replay window; not an inferred biological oscillation',
        'budget': '6 * sum(clamp(motor_forward,0,1)) * dt per cycle, before capacity and lowering/recovery gates',
        'commanded_impulse_per_cycle': ACTUATOR_FORCE * math.fsum(neural) * dt,
        'neural_samples': selected}
    encoded = json.dumps(calibration, separators=(',', ':'), allow_nan=False).encode()
    calibration_hash = hashlib.sha256(encoded).hexdigest()
    implementation_paths = ('experiments/bench_comparison.py', 'world/equipment.py',
                            'world/gym.py', 'simulation/signals.py')
    implementation_hashes = {path: hashlib.sha256((root / path).read_bytes()).hexdigest()
                             for path in implementation_paths}
    output = options.output
    output.mkdir(parents=True, exist_ok=True)
    (output/'calibration.json').write_bytes(encoded)
    summaries=[]
    repeat_identical=True
    for load in (.4, .8, 1.2):
        for name, waveform in (('recorded-neural', neural), ('periodic', periodic)):
            result=run_condition(waveform,load=load,dt=dt,cycles=options.cycles)
            repeat=run_condition(waveform,load=load,dt=dt,cycles=options.cycles)
            repeat_identical = repeat_identical and result == repeat
            result.update(format='drosolift-bench-condition',version=1,
                run_id=str(uuid4()),condition=name,seed=metadata['seed'],dt=dt,
                calibration_sha256=calibration_hash,implementation_sha256=implementation_hashes,
                mechanics=metadata['mechanics'],deterministic_repeat_identical=result==repeat)
            stem=f'{name}-load-{load:.1f}'
            (output/f'{stem}.json').write_text(json.dumps(result,separators=(',', ':'),allow_nan=False),encoding='utf-8')
            with (output/f'{stem}.csv').open('w',newline='',encoding='utf-8') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(result['samples'][0]))
                writer.writeheader(); writer.writerows(result['samples'])
            summaries.append({'condition': name, **result['summary']})
    with (output/'summary.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(summaries[0])); writer.writeheader(); writer.writerows(summaries)
    report={'format':'drosolift-bench-comparison','version':1,'calibration_sha256':calibration_hash,
        'calibration_load':.6,'evaluation_loads':[.4,.8,1.2],'dt':dt,'seed':metadata['seed'],
        'implementation_sha256':implementation_hashes,
        'deterministic_repeats_identical':repeat_identical,'summaries':summaries,
        'scope':'Deterministic engineered bench driven by a frozen received neural waveform versus matched periodic input. No biological specimen replicates or neural superiority claim.'}
    (output/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
