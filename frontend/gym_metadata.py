"""Inspectable provenance captured at a live gym server's initial state."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from simulation.gym import GymSimulation


def gym_run_metadata(simulation: GymSimulation, *, run_id: str, fps: float,
                     initial_state: dict[str, object]) -> dict[str, object]:
    """Record supplied seed, exact sources and initial persistent memory separately."""
    root = Path(__file__).resolve().parents[1]
    circuits = ['data/circuits/gym-v1-runtime.json', 'data/circuits/gym-v1-learning.json',
                'data/circuits/foraging-v1-learning.json']
    implementation = ['brain/network.py', 'brain/readout.py', 'world/equipment.py',
                      'world/apparatus_feedback.py', 'simulation/gym.py', 'experiments/experiment_002.py']

    def hashes(paths: list[str]) -> dict[str, str]:
        return {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}

    ids = sorted(node.body_id for node in simulation.bank[0].brain.network.circuit.nodes)
    return {'run_id': run_id, 'seed': simulation.seed, 'dt': 1 / fps,
            'upstream_revision': '2c5a03aa90f01048f011e13546b4d7fffc693945',
            'model': 'DrosoLift gym-v1' if simulation.bank[0].feedback_profile == 'none' else 'DrosoLift gym-apparatus-visual-v1',
            'feedback_profile': simulation.bank[0].feedback_profile,
            'feedback_manifest': json.loads((root / 'data/circuits/apparatus-visual-v1.json').read_text(encoding='utf-8')),
            'learning_enabled': simulation.bank[0].brain.learning_enabled,
            'source': json.loads((root / 'data/malecns/v1.0/source-manifest.json').read_text(encoding='utf-8')),
            'circuit_sha256': hashes(circuits), 'implementation_sha256': hashes(implementation),
            'activity_unit': 'dimensionless normalized rate-like activity; no spike events',
            'model_scope': {'simulated_neurons': len(ids), 'body_ids': ids},
            'mechanics': {'load_unit': 'model force units; gravity=1',
                          'actuator_mapping': '6 * clamp(forward,0,1) * min(1,capacity); 0 on lowering',
                          'forward_readout': 'clamp(3*.5*(forward_left+forward_right),0,1)',
                          'damping': 3.0, 'max_physics_step': .01},
            'initial_state': initial_state,
            'initial_memories': {fly.id: {'food': asdict(fly.brain.food_learning.memory),
                                         'gym': asdict(fly.brain.gym_learning.memory)}
                                 for fly in simulation.bank}}
