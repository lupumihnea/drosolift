"""A public snapshot must contain reproducible source, not private/history assets."""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.export_public_source import (
    MAX_FILE_BYTES, REQUIRED_NOTICES, export_public_source, verify_public_source,
)


class ExportPublicSourceTest(unittest.TestCase):
    def fixture(self, base):
        root = base / 'source'
        root.mkdir()
        for name in REQUIRED_NOTICES:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f'Preserved attribution: {name}\n', encoding='utf-8')
        (root / '.gitignore').write_text('ignored.txt\n', encoding='utf-8')
        (root / 'main.py').write_text('print("source")\n', encoding='utf-8')
        subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
        self.git(root, 'add', '.')
        self.git(root, '-c', 'user.name=Export fixture', '-c',
                 'user.email=fixture@example.invalid', 'commit', '-qm', 'upstream fixture')
        revision = self.git(root, 'rev-parse', 'HEAD').decode().strip()
        return root, revision

    def git(self, root, *args):
        return subprocess.run(['git', '-C', str(root), *args], check=True,
                              capture_output=True).stdout

    def write(self, root, name, data=b'local fixture'):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_inventory_exclusions_manifest_lineage_and_fresh_history(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, revision = self.fixture(base)
            excluded = ['frontend/web/src/assets/fly/walking-fly.glb',
                        'docs/media/old.mp4', 'docs/drosolift/evidence/p0-workout.png',
                        'data/raw/source.csv', 'data/runs/profile/state.sqlite3',
                        'accidental.sqlite-journal', 'accidental.sqlite-wal',
                        '.venv/bin/python', '.tools/private.exe', '.env', 'ignored.txt']
            for name in excluded:
                self.write(root, name)
            for name in ('docs/drosolift/evidence/demo-v3/current.png',
                         'frontend/web/.env.public', 'frontend/web/.env.replay'):
                self.write(root, name, b'VITE_DEMO_REPLAY=1\n')
            output = export_public_source(root, base / 'public', audited_revision=revision)
            self.assertFalse((output / '.git').exists())
            for name in excluded:
                self.assertFalse((output / name).exists(), name)
            self.assertTrue((output / 'docs/drosolift/evidence/demo-v3/current.png').is_file())
            self.assertTrue((output / 'frontend/web/.env.public').is_file())
            lineage = json.loads((output / 'UPSTREAM_LINEAGE.json').read_text())
            self.assertEqual(revision, lineage['audited_upstream_revision'])
            self.assertEqual(revision, lineage['implementation_head'])
            manifest = verify_public_source(output)
            names = {item['path'] for item in manifest['files']}
            self.assertTrue(set(REQUIRED_NOTICES) <= names)
            self.assertIn('UPSTREAM_LINEAGE.json', names)
            self.assertTrue((root / '.git').is_dir())
            (output / 'main.py').write_text('changed\n')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                verify_public_source(output)

    def test_existing_destination_and_nested_output_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, revision = self.fixture(base)
            output = base / 'existing'
            output.mkdir()
            self.write(output, 'user.txt', b'preserve me')
            with self.assertRaises(FileExistsError):
                export_public_source(root, output, audited_revision=revision)
            self.assertEqual(b'preserve me', (output / 'user.txt').read_bytes())
            with self.assertRaisesRegex(ValueError, 'outside'):
                export_public_source(root, root / 'nested', audited_revision=revision)

    def test_missing_notice_oversize_and_renamed_restricted_bytes_reject_before_output(self):
        for failure in ('notice', 'size', 'forbidden'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                root, revision = self.fixture(base)
                if failure == 'notice':
                    (root / 'NOTICE').unlink()
                elif failure == 'size':
                    with (root / 'oversize.dat').open('wb') as stream:
                        stream.truncate(MAX_FILE_BYTES + 1)
                else:
                    self.write(root, 'renamed.data', b'restricted fixture bytes')
                digest = hashlib.sha256(b'restricted fixture bytes').hexdigest()
                with patch('scripts.export_public_source.FORBIDDEN_SHA256', {digest}):
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        export_public_source(root, base / 'public', audited_revision=revision)
                self.assertFalse((base / 'public').exists())

    def test_credentials_reject_without_echoing_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, revision = self.fixture(base)
            secret = 'ghp_' + 'x' * 36
            self.write(root, 'accidental.txt', ('token=' + secret).encode())
            with self.assertRaisesRegex(ValueError, 'credential') as caught:
                export_public_source(root, base / 'public', audited_revision=revision)
            self.assertNotIn(secret, str(caught.exception))
            self.assertFalse((base / 'public').exists())

    def test_path_escape_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, revision = self.fixture(base)
            with patch('scripts.export_public_source.git_inventory', return_value=['../outside.txt']):
                with self.assertRaisesRegex(ValueError, 'path'):
                    export_public_source(root, base / 'public', audited_revision=revision)
            link = root / 'linked.txt'
            try:
                link.symlink_to(root / 'main.py')
            except OSError:
                # Exercise the same rejection on accounts without Windows's
                # CreateSymbolicLink privilege; do not silently skip the gate.
                link.write_bytes(b'stand-in for a filesystem link')
                original = Path.is_symlink
                with patch.object(Path, 'is_symlink', autospec=True,
                                  side_effect=lambda path: path == link or original(path)):
                    with self.assertRaisesRegex(ValueError, 'link'):
                        export_public_source(root, base / 'public', audited_revision=revision)
            else:
                with self.assertRaisesRegex(ValueError, 'link'):
                    export_public_source(root, base / 'public', audited_revision=revision)

    def test_only_exported_evidence_is_sanitized_with_original_checksum_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root, revision = self.fixture(base)
            name = 'docs/drosolift/evidence/demo-v3/browser-checks.json'
            original = json.dumps({'browser': 'C:/Users/Example/Chrome/chrome.exe',
                                   'hostname': 'private-workstation', 'fps': 42.5,
                                   'graphics': {'renderer': 'NVIDIA observed GPU'}}).encode()
            self.write(root, name, original)
            output = export_public_source(root, base / 'public', audited_revision=revision)
            self.assertEqual(original, (root / name).read_bytes())
            exported = json.loads((output / name).read_text())
            self.assertEqual(42.5, exported['fps'])
            self.assertEqual('NVIDIA observed GPU', exported['graphics']['renderer'])
            self.assertNotIn('Example', exported['browser'])
            self.assertNotIn('private-workstation', exported['hostname'])
            entry = next(item for item in verify_public_source(output)['files'] if item['path'] == name)
            self.assertEqual(hashlib.sha256(original).hexdigest(), entry['source_sha256'])
            self.assertEqual(['local-machine/path redaction'], entry['transformations'])
