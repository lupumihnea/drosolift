"""Opt-in commands extending gym schema 3 without changing legacy messages."""

from dataclasses import dataclass
import json
import re

from frontend.gym_telemetry import parse_gym_command
from frontend.telemetry import MAX_CLIENT_MESSAGE_BYTES, TelemetryProtocolError
from world.equipment import validate_exercise_kind, validate_load


@dataclass(frozen=True, slots=True)
class GymControlCommand:
    kind: str
    value: bool | int | float | str
    command_id: str | None = None
    station_id: str | None = None
    fly_id: str | None = None


def parse_gym_control_command(text: str) -> GymControlCommand:
    """Validate extensions strictly; legacy pause/population inputs retain their contract."""
    try:
        if len(text.encode('utf-8')) > MAX_CLIENT_MESSAGE_BYTES:
            raise ValueError('Client command is too large')
        document = json.loads(text)
        if not isinstance(document, dict):
            raise ValueError('Command must be an object')
        kind = document.get('type')
        command_id = document.get('command_id')
        if command_id is not None and (not isinstance(command_id, str)
                or re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}', command_id) is None):
            raise ValueError('Invalid command identity')
        if kind == 'set_load':
            if set(document) != {'type', 'station_id', 'load', 'command_id'} or command_id is None:
                raise ValueError('Load command fields are invalid')
            station_id = document['station_id']
            if not isinstance(station_id, str) or not 1 <= len(station_id) <= 80:
                raise ValueError('Invalid station identity')
            return GymControlCommand('load', validate_load(document['load']), command_id, station_id)
        if kind == 'set_exercise':
            if set(document) != {'type', 'fly_id', 'kind', 'command_id'} or command_id is None:
                raise ValueError('Exercise command fields are invalid')
            fly_id = document['fly_id']
            if not isinstance(fly_id, str) or re.fullmatch(r'fly-([1-9]|10)', fly_id) is None:
                raise ValueError('Invalid fly identity')
            return GymControlCommand('exercise', validate_exercise_kind(document['kind']), command_id, fly_id=fly_id)
        if kind == 'set_running' and 'command_id' in document:
            if set(document) != {'type', 'running', 'command_id'} or command_id is None:
                raise ValueError('Run command fields are invalid')
            if type(document['running']) is not bool:
                raise ValueError('Running must be a boolean')
            return GymControlCommand('running', document['running'], command_id)
        legacy_kind, value = parse_gym_command(text)
        return GymControlCommand(legacy_kind, value)
    except (ValueError, TypeError, UnicodeError) as error:
        raise TelemetryProtocolError('Invalid gym command') from error
