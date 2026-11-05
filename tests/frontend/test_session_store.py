"""Durable opaque session records reject corruption and enforce a finite store."""

import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from frontend.session_store import SessionStore, SessionStoreError, SessionStoreFull
from frontend.command_journal import CommandJournal
from frontend.gym_controls import GymControlCommand


class SessionStoreTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'sessions.sqlite3'

    def test_reopen_preserves_exact_json_and_expiry_without_storing_cookie(self):
        key = 'a' * 64
        payload = {'version': 1, 'step': 17, 'rates': [0, .00001, .4]}
        store = SessionStore(self.path, max_sessions=2)
        store.put(key, 'public-id', payload, now=10, ttl=30)
        store.close()
        store = SessionStore(self.path, max_sessions=2)
        self.addCleanup(store.close)
        self.assertEqual(payload, store.get(key, now=11).checkpoint)
        self.assertEqual('public-id', store.get(key, now=11).public_id)
        self.assertIsNone(store.get(key, now=40))

    def test_quota_preserves_existing_records_and_reclaims_only_expired(self):
        store = SessionStore(self.path, max_sessions=1)
        self.addCleanup(store.close)
        store.put('a' * 64, 'a', {'step': 1}, now=0, ttl=5)
        with self.assertRaises(SessionStoreFull):
            store.put('b' * 64, 'b', {'step': 2}, now=1, ttl=5)
        self.assertEqual({'step': 1}, store.get('a' * 64, now=1).checkpoint)
        store.put('b' * 64, 'b', {'step': 2}, now=6, ttl=5)
        self.assertIsNone(store.get('a' * 64, now=6))

    def test_corrupt_json_or_checksum_is_reported_without_reset(self):
        store = SessionStore(self.path)
        self.addCleanup(store.close)
        store.put('a' * 64, 'a', {'step': 1}, now=0, ttl=100)
        with closing(sqlite3.connect(self.path, isolation_level=None)) as connection:
            connection.execute("UPDATE sessions SET checkpoint = ?", (json.dumps({'step': 99}),))
        with self.assertRaises(SessionStoreError):
            store.get('a' * 64, now=1)
        with closing(sqlite3.connect(self.path)) as connection:
            self.assertEqual(1, connection.execute('SELECT COUNT(*) FROM sessions').fetchone()[0])

    def test_nonfinite_oversized_and_nonobject_checkpoints_are_not_written(self):
        store = SessionStore(self.path, max_checkpoint_bytes=256)
        self.addCleanup(store.close)
        for value in ({'rate': float('nan')}, {'long': 'x' * 300}, []):
            with self.assertRaises(SessionStoreError):
                store.put('a' * 64, 'a', value, now=0, ttl=100)
        self.assertIsNone(store.get('a' * 64, now=1))

    def test_corrupt_database_is_not_replaced(self):
        self.path.write_bytes(b'not a sqlite database')
        with self.assertRaises(SessionStoreError):
            SessionStore(self.path)
        self.assertEqual(b'not a sqlite database', self.path.read_bytes())

    def test_checkpoint_joins_command_transaction_and_rolls_back_with_it(self):
        store = SessionStore(self.path)
        self.addCleanup(store.close)
        store.connection.execute('BEGIN IMMEDIATE')
        store.put('a' * 64, 'a', {'step': 9}, now=0, ttl=100)
        self.assertTrue(store.connection.in_transaction)
        store.connection.rollback()
        self.assertIsNone(store.get('a' * 64, now=1))

    def test_expired_profile_and_its_journal_are_reclaimed_together(self):
        store = SessionStore(self.path, max_sessions=1)
        self.addCleanup(store.close)
        store.put('a' * 64, 'a', {'step': 9}, now=0, ttl=5)
        journal = CommandJournal(store.connection, session_id='a' * 64, run_id='run-a')
        command = GymControlCommand('running', False, 'pause')
        journal['pause'] = command, {'type': 'command_ack', 'command_id': 'pause', 'command': 'set_running',
            'status': 'applied', 'effective_step': 9, 'run_id': 'run-a'}
        store.put('b' * 64, 'b', {'step': 0}, now=6, ttl=5)
        self.assertEqual(0, len(journal))
        self.assertIsNotNone(store.get('b' * 64, now=6))
