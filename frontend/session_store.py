"""Finite SQLite checkpoints for opaque public browser sessions, not model logic."""

from dataclasses import dataclass
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3


class SessionStoreError(ValueError):
    """A durable record is unavailable or corrupt; never silently reset it."""


class SessionStoreFull(SessionStoreError):
    """All configured durable profile slots are occupied by unexpired sessions."""


@dataclass(frozen=True, slots=True)
class StoredSession:
    public_id: str
    checkpoint: dict[str, object]
    expires: float


class SessionStore:
    """One gateway worker owns this database on an explicitly persistent volume."""

    def __init__(self, path: Path, *, max_sessions: int = 256,
                 max_checkpoint_bytes: int = 4_000_000) -> None:
        if type(max_sessions) is not int or not 1 <= max_sessions <= 10_000:
            raise ValueError('Stored session limit must be an integer within1..10000')
        if type(max_checkpoint_bytes) is not int or not 128 <= max_checkpoint_bytes <= 16_000_000:
            raise ValueError('Checkpoint byte limit must be within128..16000000')
        self.path = Path(path)
        self.max_sessions = max_sessions
        self.max_checkpoint_bytes = max_checkpoint_bytes
        self.connection: sqlite3.Connection | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            self.connection.execute('PRAGMA journal_mode=WAL')
            self.connection.execute('PRAGMA synchronous=FULL')
            version = self.connection.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1):
                raise SessionStoreError('Unsupported session database version')
            with self.connection:
                self.connection.execute('''CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, public_id TEXT NOT NULL UNIQUE,
                    checkpoint TEXT NOT NULL, checksum TEXT NOT NULL,
                    updated REAL NOT NULL, expires REAL NOT NULL)''')
                self.connection.execute('PRAGMA user_version=1')
                self.connection.execute('SELECT token_hash,public_id,checkpoint,checksum,updated,expires FROM sessions LIMIT 1')
        except (OSError, sqlite3.Error, SessionStoreError) as error:
            self.close()
            raise SessionStoreError('Cannot open the session database without replacing existing data') from error

    def _database(self) -> sqlite3.Connection:
        if self.connection is None:
            raise SessionStoreError('Session database is closed')
        return self.connection

    @contextmanager
    def transaction(self):
        """Join a journal boundary without committing its acknowledgement early."""
        database = self._database()
        owns_transaction = not database.in_transaction
        if owns_transaction:
            database.execute('BEGIN IMMEDIATE')
        try:
            yield database
        except BaseException:
            if owns_transaction:
                database.rollback()
            raise
        else:
            if owns_transaction:
                database.commit()

    @staticmethod
    def _validate_key(key: str) -> None:
        if not isinstance(key, str) or re.fullmatch(r'[a-f0-9]{64}', key) is None:
            raise SessionStoreError('Invalid session digest')

    def get(self, key: str, *, now: float) -> StoredSession | None:
        self._validate_key(key)
        try:
            row = self._database().execute(
                'SELECT public_id,checkpoint,checksum,expires FROM sessions WHERE token_hash=?', (key,)).fetchone()
            if row is None:
                return None
            if (not all(isinstance(value, str) for value in row[:3])
                    or not isinstance(row[3], (float, int)) or not math.isfinite(row[3])):
                raise SessionStoreError('Saved session column types are invalid')
            if row[3] <= now:
                return None
            encoded = row[1].encode('utf-8')
            if len(encoded) > self.max_checkpoint_bytes or hashlib.sha256(encoded).hexdigest() != row[2]:
                raise SessionStoreError('Saved session checksum does not match')
            checkpoint = json.loads(row[1], parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
            if not isinstance(checkpoint, dict):
                raise SessionStoreError('Saved checkpoint must be an object')
            json.dumps(checkpoint, allow_nan=False)
            return StoredSession(row[0], checkpoint, row[3])
        except (sqlite3.Error, UnicodeError, ValueError, TypeError) as error:
            raise SessionStoreError('Cannot validate the saved session; original record retained') from error

    def put(self, key: str, public_id: str, checkpoint: object, *, now: float, ttl: float) -> None:
        self._validate_key(key)
        try:
            if not isinstance(checkpoint, dict) or not isinstance(public_id, str) or not 1 <= len(public_id) <= 80:
                raise ValueError('Invalid checkpoint or public identity')
            if not math.isfinite(now) or not math.isfinite(ttl) or ttl <= 0:
                raise ValueError('Invalid checkpoint expiry')
            text = json.dumps(checkpoint, sort_keys=True, separators=(',', ':'), allow_nan=False)
            encoded = text.encode('utf-8')
            if len(encoded) > self.max_checkpoint_bytes:
                raise ValueError('Checkpoint exceeds configured byte limit')
            checksum = hashlib.sha256(encoded).hexdigest()
            database = self._database()
            with self.transaction():
                if database.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='gym_command_journal'").fetchone():
                    database.execute('''DELETE FROM gym_command_journal WHERE session_id IN
                        (SELECT token_hash FROM sessions WHERE expires<=?)''', (now,))
                database.execute('DELETE FROM sessions WHERE expires<=?', (now,))
                exists = database.execute('SELECT 1 FROM sessions WHERE token_hash=?', (key,)).fetchone()
                if not exists and database.execute('SELECT COUNT(*) FROM sessions').fetchone()[0] >= self.max_sessions:
                    raise SessionStoreFull('Durable session capacity reached')
                database.execute('''INSERT INTO sessions VALUES (?,?,?,?,?,?)
                    ON CONFLICT(token_hash) DO UPDATE SET checkpoint=excluded.checkpoint,
                    checksum=excluded.checksum,updated=excluded.updated,expires=excluded.expires''',
                    (key, public_id, text, checksum, now, now + ttl))
        except SessionStoreFull:
            raise
        except (sqlite3.Error, ValueError, TypeError, UnicodeError) as error:
            raise SessionStoreError('Cannot save the session checkpoint') from error

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
