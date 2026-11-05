"""Versioned synthetic apparatus lamps transduced through existing vision inputs."""

from simulation.signals import ApparatusFeedback
from world.equipment import ExerciseState, MAX_LOAD


FEEDBACK_PROFILES = ('none', 'apparatus-visual-v1')


def validate_feedback_profile(value: object) -> str:
    if not isinstance(value, str) or value not in FEEDBACK_PROFILES:
        raise ValueError('Unknown apparatus feedback profile')
    return value


def apparatus_feedback(profile: str, exercise: ExerciseState, load: float) -> ApparatusFeedback:
    """Read actual joint/load/recovery state; no clock-driven brightness animation."""
    validate_feedback_profile(profile)
    if profile == 'none' or exercise.station_id is None or exercise.kind is None:
        return ApparatusFeedback(profile)
    q = min(1.0, max(0.0, exercise.joint_position))
    brightness = .16 + .35 * q + .15 * min(1.0, max(0.0, load / MAX_LOAD))
    if exercise.phase == 'recovery':
        brightness *= .35
    left, right = brightness, .25 * brightness
    if exercise.kind == 'bicep_curl':
        left, right = right, left
    return ApparatusFeedback(profile, left, right)
