"""Portable package contains only compiled demo assets and required provenance."""
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.package_conference import package_conference

class ConferencePackageTest(unittest.TestCase):
    def fixture(self, root):
        dist=root/'frontend/web/dist-replay'
        (dist/'assets').mkdir(parents=True)
        (dist/'index.html').write_text('<html>recorded demo</html>')
        (dist/'assets/app.js').write_text('const replay=true;')
        for name in ('LICENSE','NOTICE','THIRD_PARTY_NOTICES.md'):
            (root/name).write_text(name)
        (root/'licenses').mkdir()
        (root/'licenses/three-MIT.txt').write_text('MIT copyright test')
        (root/'data/malecns/v1.0').mkdir(parents=True)
        (root/'data/malecns/v1.0/source-manifest.json').write_text('{}')
        (root/'scripts').mkdir()
        (root/'scripts/serve_replay.py').write_text("print('explicit MIME static server')")
        docs=root/'docs/drosolift'; docs.mkdir(parents=True)
        for name in ('ASSETS.md','MORPHOLOGY.md','PROTOCOL.md','COMPARISON.md','IMPLEMENTATION_PLAN.md','SOURCES.md'):
            (docs/name).write_text(name)
        return dist

    def test_package_excludes_sources_and_preserves_notices(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.fixture(root)
            (root/'data/raw').mkdir(parents=True)
            (root/'data/raw/private.feather').write_bytes(b'raw source outside package')
            result=package_conference(root,root/'demo.zip')
            with zipfile.ZipFile(result) as archive:
                names=archive.namelist()
                self.assertEqual(sorted(names),names)
                self.assertIn('index.html',names)
                self.assertIn('LICENSE',names)
                self.assertIn('docs/drosolift/ASSETS.md',names)
                self.assertIn('RUN_DEMO.txt',names)
                self.assertFalse(any('raw' in name or (name.endswith('.py') and name != 'serve.py') for name in names))
                self.assertEqual((root/'scripts/serve_replay.py').read_bytes(), archive.read('serve.py'))
                self.assertIn('python serve.py',archive.read('RUN_DEMO.txt').decode())

    def test_static_server_pins_module_mime_independently_of_os_registry(self):
        from scripts.serve_replay import ReplayHandler
        self.assertEqual('text/javascript', ReplayHandler.extensions_map['.js'])
        self.assertEqual('text/javascript', ReplayHandler.extensions_map['.mjs'])
        self.assertEqual('text/css', ReplayHandler.extensions_map['.css'])

    def test_restricted_glb_is_rejected_before_output_is_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); dist=self.fixture(root)
            (dist/'assets/walking-fly.GLB').write_bytes(b'not redistributable')
            with self.assertRaisesRegex(ValueError,'GLB'):
                package_conference(root,root/'demo.zip')
            self.assertFalse((root/'demo.zip').exists())

    def test_existing_user_package_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.fixture(root)
            output=root/'demo.zip'; output.write_bytes(b'user output')
            with self.assertRaises(FileExistsError):
                package_conference(root,output)
            self.assertEqual(b'user output',output.read_bytes())

    def test_identical_files_make_identical_archives(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.fixture(root)
            first=package_conference(root,root/'one.zip')
            second=package_conference(root,root/'two.zip')
            self.assertEqual(first.read_bytes(),second.read_bytes())
