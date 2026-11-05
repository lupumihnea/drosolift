"""Atomic verified raw-data installation; no network access in these tests."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from scripts.download_malecns import download_asset

class DownloadMaleCNSTest(unittest.TestCase):
    def test_verified_download_publishes_exact_bytes_then_skips_network(self):
        content=b'official-test-content'
        digest=sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            destination=Path(directory)/'weights.feather'
            opener=Mock(return_value=BytesIO(content))
            self.assertEqual('downloaded-verified',download_asset('https://example.org/weights.feather',digest,destination,opener=opener))
            self.assertEqual(content,destination.read_bytes())
            self.assertEqual('verified-existing',download_asset('https://example.org/weights.feather',digest,destination,opener=opener))
            self.assertEqual(1,opener.call_count)
            self.assertEqual([destination],list(Path(directory).iterdir()))

    def test_mismatched_download_never_publishes_or_leaves_partial(self):
        with tempfile.TemporaryDirectory() as directory:
            destination=Path(directory)/'weights.feather'
            with self.assertRaisesRegex(ValueError,'checksum mismatch'):
                download_asset('https://example.org/weights.feather','0'*64,destination,opener=Mock(return_value=BytesIO(b'bad bytes')))
            self.assertFalse(destination.exists())
            self.assertEqual([],list(Path(directory).iterdir()))

    def test_existing_mismatched_user_source_is_preserved_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            destination=Path(directory)/'weights.feather'
            destination.write_bytes(b'user data')
            opener=Mock()
            with self.assertRaises(FileExistsError):
                download_asset('https://example.org/weights.feather','0'*64,destination,opener=opener)
            self.assertEqual(b'user data',destination.read_bytes())
            opener.assert_not_called()

    def test_concurrent_source_is_never_replaced(self):
        content=b'expected'
        with tempfile.TemporaryDirectory() as directory:
            destination=Path(directory)/'weights.feather'
            def open_concurrently(*args,**kwargs):
                destination.write_bytes(b'concurrent user data')
                return BytesIO(content)
            with self.assertRaises(FileExistsError):
                download_asset('https://example.org/weights.feather',sha256(content).hexdigest(),destination,opener=open_concurrently)
            self.assertEqual(b'concurrent user data',destination.read_bytes())
