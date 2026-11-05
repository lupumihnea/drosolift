"""SQLite command identities with a bounded hot cache and whole-session retention.

Evicting an entry from RAM never removes its durable retry record. A session's
explicit command quota rejects new identities, while previous retries remain
available. Session expiry may purge the whole retired session, never individual
live command UUIDs. Shared connections permit checkpoint + ack transactions.
"""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import time

from frontend.gym_controls import GymControlCommand


class CommandConflictError(ValueError):
    """An identity or completed acknowledgement cannot be rewritten."""


class CommandQuotaExceeded(ValueError):
    """The retained session command quota is full; old retries are still valid."""


CommandResult = tuple[GymControlCommand, dict[str, object]]


class CommandJournal(MutableMapping[str, CommandResult]):
    """Session/run-scoped SQLite ledger; caller owns externally supplied connections."""

    def __init__(self, database: sqlite3.Connection | Path | str | None = None, *,
                 session_id: str, run_id: str, hot_cache_size: int = 128,
                 max_commands: int = 100_000) -> None:
        if any(not isinstance(value, str) or not 1 <= len(value) <= 128
               for value in (session_id, run_id)):
            raise ValueError('Session and run identities must be bounded strings')
        if type(hot_cache_size) is not int or not 0 <= hot_cache_size <= 4096:
            raise ValueError('Hot cache must be within 0..4096 entries')
        if type(max_commands) is not int or not 1 <= max_commands <= 1_000_000:
            raise ValueError('Command quota must be within 1..1000000')
        self.session_id, self.run_id = session_id, run_id
        self.hot_cache_size, self.max_commands = hot_cache_size, max_commands
        self._owns_connection = not isinstance(database, sqlite3.Connection)
        if self._owns_connection:
            if database is not None:
                Path(database).parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(str(database) if database is not None else ':memory:',
                                              isolation_level=None)
            self.connection.execute('PRAGMA journal_mode=WAL')
            self.connection.execute('PRAGMA synchronous=FULL')
        else:
            self.connection = database
        self.connection.execute('''CREATE TABLE IF NOT EXISTS gym_command_journal (
            session_id TEXT NOT NULL, run_id TEXT NOT NULL, command_id TEXT NOT NULL,
            payload TEXT NOT NULL, result TEXT NOT NULL, status TEXT NOT NULL,
            created_at REAL NOT NULL, updated_at REAL NOT NULL,
            PRIMARY KEY (session_id, run_id, command_id),
            CHECK (status IN ('pending','applied')),
            CHECK (length(payload) <= 2048 AND length(result) <= 2048)
        )''')
        self._hot: OrderedDict[str, CommandResult] = OrderedDict()
        self._depth = 0

    @property
    def hot_cache_entries(self) -> int:
        return len(self._hot)

    @contextmanager
    def atomic(self):
        """Join an existing transaction or own one; never await inside this scope."""
        owns = self._depth == 0 and not self.connection.in_transaction
        if owns:
            self.connection.execute('BEGIN IMMEDIATE')
        self._depth += 1
        try:
            yield
        except BaseException:
            self._hot.clear()
            if owns:
                self.connection.rollback()
            raise
        else:
            if owns:
                try:
                    self.connection.commit()
                except BaseException:
                    self._hot.clear()
                    self.connection.rollback()
                    raise
        finally:
            self._depth -= 1

    def _cache(self, identity: str, value: CommandResult) -> None:
        if not self.hot_cache_size:
            return
        self._hot[identity] = value[0], dict(value[1])
        self._hot.move_to_end(identity)
        while len(self._hot) > self.hot_cache_size:
            self._hot.popitem(last=False)

    @staticmethod
    def _encode(command: GymControlCommand, result: dict[str, object], run_id: str) -> tuple[str, str]:
        if command.command_id is None or command.kind not in ('running', 'load', 'exercise'):
            raise ValueError('Only identified model commands enter the journal')
        if (result.get('type') != 'command_ack' or result.get('command_id') != command.command_id
                or result.get('run_id') != run_id or result.get('status') not in ('pending', 'applied')):
            raise ValueError('Invalid journal acknowledgement')
        effective = result.get('effective_step')
        if (result['status'] == 'pending' and effective is not None) or (
                result['status'] == 'applied' and (type(effective) is not int or effective < 0)):
            raise ValueError('Invalid effective step')
        payload = json.dumps(asdict(command), sort_keys=True, separators=(',', ':'), allow_nan=False)
        encoded = json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if len(payload.encode('utf-8')) > 2048 or len(encoded.encode('utf-8')) > 2048:
            raise ValueError('Journal record exceeds its bounded size')
        return payload, encoded

    def __getitem__(self, identity: str) -> CommandResult:
        # An outer checkpoint transaction may later roll back. Never let its
        # uncommitted rows enter (or read stale values from) the durable cache.
        if not self.connection.in_transaction and identity in self._hot:
            self._hot.move_to_end(identity)
            command, result = self._hot[identity]
            return command, dict(result)
        row = self.connection.execute('''SELECT payload, result FROM gym_command_journal
            WHERE session_id=? AND run_id=? AND command_id=?''',
            (self.session_id, self.run_id, identity)).fetchone()
        if row is None:
            raise KeyError(identity)
        command = GymControlCommand(**json.loads(row[0]))
        result = json.loads(row[1])
        # Corrupt records fail closed rather than turning an old retry into a new command.
        if command.command_id != identity or self._encode(command, result, self.run_id) != (row[0], row[1]):
            raise ValueError('Corrupt command journal record')
        if not self.connection.in_transaction:
            self._cache(identity, (command, result))
        return command, dict(result)

    def ensure_capacity(self, identity: str) -> None:
        """Check before model mutation; updates/retries never consume another slot."""
        exists = self.connection.execute('''SELECT 1 FROM gym_command_journal
            WHERE session_id=? AND run_id=? AND command_id=?''',
            (self.session_id, self.run_id, identity)).fetchone()
        if exists:
            return
        count = self.connection.execute('SELECT COUNT(*) FROM gym_command_journal WHERE session_id=?',
                                        (self.session_id,)).fetchone()[0]
        if count >= self.max_commands:
            raise CommandQuotaExceeded(f'Session reached its {self.max_commands}-command quota; existing retries remain available')

    def __setitem__(self, identity: str, value: CommandResult) -> None:
        command, result = value
        if command.command_id != identity:
            raise ValueError('Command key differs from its identity')
        payload, encoded = self._encode(command, result, self.run_id)
        with self.atomic():
            previous = self.connection.execute('''SELECT payload, result, status FROM gym_command_journal
                WHERE session_id=? AND run_id=? AND command_id=?''',
                (self.session_id, self.run_id, identity)).fetchone()
            if previous is not None:
                if previous[0] != payload:
                    raise CommandConflictError('Command identity already has a different payload')
                if previous[2] == 'applied' and previous[1] != encoded:
                    raise CommandConflictError('An applied acknowledgement and effective step are immutable')
                self.connection.execute('''UPDATE gym_command_journal SET result=?, status=?, updated_at=?
                    WHERE session_id=? AND run_id=? AND command_id=?''',
                    (encoded, result['status'], time.time(), self.session_id, self.run_id, identity))
            else:
                self.ensure_capacity(identity)
                now = time.time()
                self.connection.execute('''INSERT INTO gym_command_journal
                    (session_id,run_id,command_id,payload,result,status,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?)''',
                    (self.session_id, self.run_id, identity, payload, encoded, result['status'], now, now))
            self._hot.pop(identity, None)

    def __delitem__(self, identity: str) -> None:
        raise TypeError('Live command identities cannot be evicted; expire the whole retired session')

    def __iter__(self) -> Iterator[str]:
        rows = self.connection.execute('''SELECT command_id FROM gym_command_journal
            WHERE session_id=? AND run_id=? ORDER BY command_id''', (self.session_id, self.run_id))
        return (row[0] for row in rows)

    def __len__(self) -> int:
        return self.connection.execute('''SELECT COUNT(*) FROM gym_command_journal
            WHERE session_id=? AND run_id=?''', (self.session_id, self.run_id)).fetchone()[0]

    @staticmethod
    def purge_session(connection: sqlite3.Connection, session_id: str) -> None:
        """Delete a whole expired session; caller must retire its live server/cache first."""
        connection.execute('DELETE FROM gym_command_journal WHERE session_id=?', (session_id,))

    def close(self) -> None:
        self._hot.clear()
        if self._owns_connection:
            self.connection.close()
