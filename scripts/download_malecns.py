"""Download and verify the pinned MaleCNS release without replacing existing data.

Usage: python scripts/download_malecns.py
Raw sources stay in the Git-ignored data/raw tree. A unique sibling temporary
file is published only after its full SHA256 matches the source manifest.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.request import urlopen
from uuid import uuid4

CHUNK_SIZE = 1024 * 1024


def checksum(path: Path) -> str:
    """Hash an existing source incrementally, keeping large files off the heap."""
    digest = sha256()
    with path.open('rb') as stream:
        while block := stream.read(CHUNK_SIZE):
            digest.update(block)
    return digest.hexdigest()


def download_asset(url: str, expected_sha256: str, destination: Path, *, opener=urlopen) -> str:
    """Verify before use; mismatched existing files are always left intact."""
    if re.fullmatch(r'[0-9a-f]{64}', expected_sha256) is None:
        raise ValueError('Expected a lowercase SHA256 checksum')
    destination = Path(destination)
    if destination.exists():
        if checksum(destination) != expected_sha256:
            raise FileExistsError(f'Existing source has a different checksum; preserved: {destination}')
        return 'verified-existing'
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f'.{destination.name}.download-{uuid4().hex}.part')
    try:
        digest = sha256()
        with opener(url, timeout=120) as response, temporary.open('xb') as output:
            while block := response.read(CHUNK_SIZE):
                output.write(block)
                digest.update(block)
            output.flush()
            os.fsync(output.fileno())
        if digest.hexdigest() != expected_sha256:
            raise ValueError(f'Download checksum mismatch for {destination.name}; final source not installed')
        # Hard-link publication is atomic and refuses an existing destination on
        # Windows and POSIX. A concurrent caller cannot have its source replaced.
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if checksum(destination) != expected_sha256:
                raise FileExistsError(f'A concurrent existing source differs; preserved: {destination}')
        return 'downloaded-verified'
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=root/'data/malecns/v1.0/source-manifest.json')
    parser.add_argument('--output', type=Path, default=root/'data/raw/malecns/v1.0')
    options = parser.parse_args()
    manifest = json.loads(options.manifest.read_text(encoding='utf-8'))
    for name, source in manifest['sources'].items():
        url = source['url']
        parsed = urlparse(url)
        filename = Path(parsed.path).name
        if parsed.scheme != 'https' or not filename or filename in ('.', '..'):
            parser.error(f'Invalid HTTPS source for {name}')
        destination = options.output / filename
        try:
            status = download_asset(url, source['sha256'], destination)
        except (OSError, ValueError) as error:
            parser.exit(1, f'{name}: {error}\n')
        print(f'{name}: {status}, {destination.stat().st_size} bytes, SHA256 {source["sha256"]}')

if __name__ == '__main__':
    main()
