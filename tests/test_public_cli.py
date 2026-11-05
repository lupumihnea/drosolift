"""Public mode validates bounded hosting configuration before loading source data."""

from pathlib import Path
import unittest
from unittest.mock import patch

from main import build_parser
from public_cli import run_public


ROOT = Path(__file__).resolve().parents[1]


class PublicCliTest(unittest.TestCase):
    def test_public_command_has_separate_port_and_explicit_durable_path_and_origin(self):
        options = build_parser().parse_args(['public-web', '--session-db', 'data/runs/public/sessions.sqlite3',
            '--allow-origin', 'https://gym.example.org'])
        self.assertEqual(8003, options.port)
        self.assertEqual(4, options.max_active)
        self.assertEqual(2, options.max_clients)
        self.assertEqual(256, options.max_profiles)
        self.assertEqual(30, options.cookie_days)
        self.assertFalse(options.insecure_local_cookie)

    def test_invalid_public_configuration_never_starts_or_loads_model(self):
        for extra in (['--fps', 'nan'], ['--fps', '100'], ['--max-active', '0'],
                      ['--port', '0'], ['--max-clients', '9'], ['--max-profiles', '0'], ['--insecure-local-cookie']):
            options = build_parser().parse_args(['public-web', '--session-db', 'unused.sqlite3',
                '--allow-origin', 'https://gym.example.org'] + extra)
            with patch('public_cli.load_gym_circuits') as load, patch('public_cli.web.run_app') as run:
                self.assertEqual(1, run_public(options, ROOT))
                load.assert_not_called()
                run.assert_not_called()
