"""Durable retry identities survive hot-cache eviction and process reopen."""
from pathlib import Path
import sqlite3
import tempfile
import unittest

from frontend.command_journal import CommandJournal, CommandConflictError, CommandQuotaExceeded
from frontend.gym_controls import GymControlCommand


def ack(identity, step=0, status='applied'):
    return {'type':'command_ack','command_id':identity,'command':'set_running',
            'status':status,'effective_step':step if status=='applied' else None,'run_id':'stable-run'}

class CommandJournalTest(unittest.TestCase):
    def test_more_than_1024_commands_remain_retryable_after_cache_eviction_and_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sessions.sqlite'
            journal=CommandJournal(path,session_id='session-a',run_id='stable-run',hot_cache_size=2)
            for index in range(1100):
                identity=f'pause-{index}'
                journal[identity]=(GymControlCommand('running',False,identity),ack(identity,index))
            self.assertEqual(1100,len(journal));self.assertLessEqual(journal.hot_cache_entries,2)
            journal.close()
            reopened=CommandJournal(path,session_id='session-a',run_id='stable-run',hot_cache_size=2)
            self.assertEqual(ack('pause-0',0),reopened['pause-0'][1])
            self.assertEqual(ack('pause-1099',1099),reopened['pause-1099'][1])
            self.assertEqual(ack('pause-1098',1098),reopened['pause-1098'][1])
            self.assertNotIn('pause-0', reopened._hot)
            self.assertEqual(ack('pause-0',0),reopened['pause-0'][1])
            with self.assertRaises(CommandConflictError):
                reopened['pause-0']=(GymControlCommand('running',True,'pause-0'),ack('pause-0',9000))
            self.assertEqual(ack('pause-0',0),reopened['pause-0'][1]);reopened.close()

    def test_pending_to_applied_retains_the_original_effective_step(self):
        journal=CommandJournal(None,session_id='session-a',run_id='stable-run',hot_cache_size=0)
        command=GymControlCommand('running',False,'pending')
        journal['pending']=(command,ack('pending',status='pending'))
        self.assertEqual('pending',journal['pending'][1]['status'])
        journal['pending']=(command,ack('pending',37))
        with self.assertRaises(CommandConflictError):journal['pending']=(command,ack('pending',38))
        self.assertEqual(37,journal['pending'][1]['effective_step']);journal.close()

    def test_quota_rejects_new_ids_but_preserves_existing_retries_and_session_isolation(self):
        connection=sqlite3.connect(':memory:',isolation_level=None)
        journal=CommandJournal(connection,session_id='session-a',run_id='stable-run',max_commands=2)
        for identity in ('one','two'):journal[identity]=(GymControlCommand('running',False,identity),ack(identity))
        with self.assertRaises(CommandQuotaExceeded):journal['three']=(GymControlCommand('running',False,'three'),ack('three'))
        self.assertEqual(ack('one'),journal['one'][1])
        other=CommandJournal(connection,session_id='session-b',run_id='stable-run',max_commands=2)
        self.assertIsNone(other.get('one'))
        other['one']=(GymControlCommand('running',True,'one'),ack('one',1))
        self.assertNotEqual(journal['one'][0],other['one'][0])
        CommandJournal.purge_session(connection,'session-a')
        self.assertEqual(0,len(journal));self.assertEqual(1,len(other));connection.close()

    def test_checkpoint_and_ack_commit_or_roll_back_together(self):
        connection=sqlite3.connect(':memory:',isolation_level=None)
        connection.execute('CREATE TABLE checkpoints (value TEXT)')
        journal=CommandJournal(connection,session_id='session-a',run_id='stable-run')
        with self.assertRaisesRegex(ValueError,'checkpoint failed'):
            with journal.atomic():
                journal['one']=(GymControlCommand('running',False,'one'),ack('one'))
                connection.execute("INSERT INTO checkpoints VALUES ('new state')")
                raise ValueError('checkpoint failed')
        self.assertIsNone(journal.get('one'));self.assertEqual(0,connection.execute('SELECT COUNT(*) FROM checkpoints').fetchone()[0])
        connection.close()

    def test_outer_transaction_rollback_cannot_leave_uncommitted_hot_cache_records(self):
        connection = sqlite3.connect(':memory:', isolation_level=None)
        connection.row_factory = sqlite3.Row
        journal = CommandJournal(connection, session_id='session-a', run_id='stable-run')
        connection.execute('BEGIN IMMEDIATE')
        journal['one'] = GymControlCommand('running', False, 'one'), ack('one')
        self.assertEqual(ack('one'), journal['one'][1])
        connection.rollback()
        self.assertIsNone(journal.get('one'))
        journal['one'] = GymControlCommand('running', True, 'one'), ack('one', 2)
        self.assertEqual(ack('one', 2), journal['one'][1])
        connection.close()
