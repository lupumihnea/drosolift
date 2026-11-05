"""Export a fresh, attributed source snapshot without restricted Git history.

This does not publish, initialize Git, alter the original checkout or deploy a
service. Git supplies tracked and nonignored files; explicit rights/privacy gates
then validate every retained file before creating the fresh output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess


AUDITED_REVISION = '2c5a03aa90f01048f011e13546b4d7fffc693945'
UPSTREAM_URL = 'https://github.com/tiredbooy/Fruit-Fly'
FORBIDDEN_SHA256 = {'2c7a3398c2b0f9fdae6f62351379b4ea5a01d7fcf6f3a1d582d4c5106ab75b57'}
CT_SHA256 = 'c967c27467b1373be70c32f90dffc56e6f11ce38d8699671f40740a2316a7d75'
CT_PATH = 'frontend/web/src/assets/fly/drosophila.glb'
MAX_FILE_BYTES = 50_000_000
MANIFEST = 'PUBLIC_SOURCE_MANIFEST.json'
LINEAGE = 'UPSTREAM_LINEAGE.json'
REQUIRED_NOTICES = (
    'LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md', 'licenses/three-MIT.txt',
    'frontend/web/src/assets/fly/ATTRIBUTION.md',
    'frontend/web/src/assets/fly/source-manifest.json',
    'frontend/web/src/assets/fly/walking-source.json',
    'data/malecns/v1.0/source-manifest.json',
    'docs/drosolift/SOURCES.md', 'docs/drosolift/ASSETS.md', 'docs/drosolift/MORPHOLOGY.md',
)
_PRIVATE_PARTS = {'.git', '.venv', '.tools', '.agents', '.codex', '.serena',
                  '.impeccable', 'node_modules', '__pycache__', '.pytest_cache',
                  '.mypy_cache', '.ruff_cache', '.cache'}
_SECRET_PATTERNS = (
    re.compile(rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{20,255}\b'),
    re.compile(rb'\bgithub_pat_[A-Za-z0-9_]{20,255}\b'),
    re.compile(rb'\bsk-(?:proj-)?[A-Za-z0-9_-]{24,255}\b'),
    re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    re.compile(rb'(?im)^\s*(?:api[_-]?key|api[_-]?token|secret[_-]?key|access[_-]?token|password|cookie[_-]?secret)\s*[:=]\s*[\x22\x27]?[A-Za-z0-9+/=_-]{20,}'),
    re.compile(rb'https?://[^\s/:@\x22\x27]+:[^\s/@\x22\x27]+@'),
)
_MACHINE_PATH = re.compile(r'(?<![\w])(?:[A-Za-z]:[\\/]|/(?:Users|home)/[^/\s]+/)')
_MACHINE_KEYS = {'hostname', 'computername', 'computer_name', 'machine_name', 'username', 'user_name', 'userprofile'}


def _git(root: Path, *arguments: str) -> bytes:
    result = subprocess.run(['git', '--no-optional-locks', '-C', str(root), *arguments],
                            check=False, capture_output=True)
    if result.returncode:
        # Do not echo Git configuration/remote credentials in errors.
        raise ValueError('Read-only Git inventory/lineage check failed; run as the checkout owner')
    return result.stdout


def git_inventory(root: Path) -> list[str]:
    """Inventory Git-tracked plus nonignored untracked paths, without mutations."""
    data = _git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z')
    return [name.decode('utf-8') for name in data.split(b'\0') if name]


def _relative(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or path.as_posix() != name or
            '\\' in name or ':' in name or any(ord(c) < 32 for c in name) or
            any(part in ('', '.', '..') or part.endswith((' ', '.')) for part in path.parts)):
        raise ValueError('Unsafe source path in publication inventory')
    return path


def _source_path(root: Path, name: str) -> Path:
    relative = _relative(name)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink() or getattr(current, 'is_junction', lambda: False)():
            raise ValueError(f'Symbolic link/junction is not allowed in public source: {name}')
    if not current.resolve().is_relative_to(root):
        raise ValueError(f'Source path escapes the checkout: {name}')
    return current


def _exclusion(name: str) -> str | None:
    path = _relative(name)
    lower = name.lower()
    if any(part.lower() in _PRIVATE_PARTS for part in path.parts):
        return 'private tool/runtime state or Git history'
    if lower.startswith(('data/raw/', 'data/runs/', 'data/processed/')):
        return 'raw source archive or per-run state'
    if lower.startswith('frontend/web/dist') and path.parts[2].startswith('dist'):
        return 'generated frontend output'
    if lower.startswith('docs/media/'):
        return 'legacy renders without standalone public rig permission'
    if lower.startswith('docs/drosolift/evidence/p0'):
        return 'legacy baseline evidence'
    if path.name.lower() == 'walking-fly.glb':
        return 'legacy rig without standalone public redistribution license'
    if path.name.lower().startswith('.env') and name not in (
            'frontend/web/.env.public', 'frontend/web/.env.replay') and path.name not in (
                '.env.example', '.env.sample'):
        return 'private environment configuration'
    if (path.suffix.lower() in ('.pyc', '.pyo', '.pem', '.key', '.p12', '.pfx', '.bak', '.backup')
            or re.search(r'\.(?:sqlite3?|db)(?:-(?:shm|wal|journal))?$', lower)):
        return 'private database, credential or generated bytecode'
    if lower.endswith(('.zip', '.7z', '.rar', '.tar', '.gz', '.tgz', '.bz2', '.xz', '.zst')):
        return 'source/package archive; use the reproducible source inputs instead'
    return None


def _read(root: Path, name: str) -> bytes:
    path = _source_path(root, name)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError(f'Public source path is not a regular file: {name}')
    if info.st_size > MAX_FILE_BYTES:
        raise ValueError(f'Public source file exceeds the 50 MB limit: {name}')
    data = path.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f'Public source file exceeds the 50 MB limit: {name}')
    return data


def _sanitize_docs(name: str, data: bytes) -> tuple[bytes, list[str]]:
    """Redact only publication copies; retain exact local historical evidence."""
    if not name.startswith('docs/') or Path(name).suffix.lower() not in ('.json', '.md', '.txt', '.log', '.csv', '.svg'):
        return data, []
    try:
        text = data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return data, []
    changed = [False]
    if name.endswith('.json'):
        try:
            document = json.loads(text)
        except ValueError:
            document = None
        if document is not None:
            def redact(item):
                if isinstance(item, dict):
                    result = {}
                    for key, value in item.items():
                        if key.lower() in _MACHINE_KEYS and value is not None and value != '':
                            changed[0] = True
                            result[key] = '<local-machine omitted>'
                        else:
                            result[key] = redact(value)
                    return result
                if isinstance(item, list):
                    return [redact(value) for value in item]
                if isinstance(item, str) and _MACHINE_PATH.search(item):
                    changed[0] = True
                    return '<local-filesystem path omitted>'
                return item
            sanitized = redact(document)
            if changed[0]:
                return (json.dumps(sanitized, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'), ['local-machine/path redaction']
            return data, []
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if _MACHINE_PATH.search(line):
            lines[index] = '[Local filesystem path omitted from this publication copy.]\n'
            changed[0] = True
    return (''.join(lines).encode('utf-8'), ['local-machine/path redaction']) if changed[0] else (data, [])


def _inspect(name: str, data: bytes) -> tuple[bytes, dict]:
    digest = hashlib.sha256(data).hexdigest()
    if digest in FORBIDDEN_SHA256:
        raise ValueError(f'Restricted legacy asset bytes found under retained path: {name}')
    if Path(name).suffix.lower() == '.glb' and (name != CT_PATH or digest != CT_SHA256):
        raise ValueError(f'Unverified GLB asset cannot enter the public source: {name}')
    if any(pattern.search(data) for pattern in _SECRET_PATTERNS):
        raise ValueError(f'Possible credential pattern in public source: {name}')
    exported, transformations = _sanitize_docs(name, data)
    record = {'path': name, 'bytes': len(exported), 'sha256': hashlib.sha256(exported).hexdigest()}
    if transformations:
        record.update(source_sha256=digest, transformations=transformations)
    return exported, record


def export_public_source(root: Path, output: Path, *, audited_revision: str = AUDITED_REVISION) -> Path:
    """Create a fresh source directory after all rights/privacy checks pass.

    The optional audited revision supports independent fixture repositories; the
    CLI always uses the pinned project audit. No Git history is copied or edited.
    """
    root = Path(root).resolve(strict=True)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('Existing public source output preserved; choose a fresh directory')
    output = output.resolve()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError('Public source output must be outside the implementation checkout')
    inventory = git_inventory(root)
    if len(inventory) > 20_000:
        raise ValueError('Source inventory exceeds its bounded file count')
    records, exclusions, seen = [], [], set()
    for name in sorted(inventory):
        _source_path(root, name)
        if name.casefold() in seen:
            raise ValueError('Duplicate or case-colliding source path')
        seen.add(name.casefold())
        reason = _exclusion(name)
        if reason:
            exclusions.append({'path': name, 'reason': reason})
            continue
        if name in (MANIFEST, LINEAGE):
            raise ValueError('Generated publication metadata already exists in the source inventory')
        _, record = _inspect(name, _read(root, name))
        records.append(record)
    retained = {item['path'] for item in records}
    missing = set(REQUIRED_NOTICES) - retained
    if missing or any(item['bytes'] == 0 for item in records if item['path'] in REQUIRED_NOTICES):
        raise FileNotFoundError('Required public source notice/provenance is missing or empty')
    if not re.fullmatch('[0-9a-f]{40}', audited_revision):
        raise ValueError('Audited upstream revision must be a full Git SHA1')
    _git(root, 'merge-base', '--is-ancestor', audited_revision, 'HEAD')
    head = _git(root, 'rev-parse', 'HEAD').decode('ascii').strip()
    lineage = {
        'format': 'drosolift-public-source-lineage', 'version': 1,
        'upstream_repository': UPSTREAM_URL, 'audited_upstream_revision': audited_revision,
        'implementation_head': head,
        'uncommitted_changes_included': bool(_git(root, 'status', '--porcelain', '--untracked-files=normal')),
        'history_policy': 'Fresh source snapshot; original upstream history preserved in the local implementation checkout.',
        'reason': 'Historical walking-fly.glb has no supplied public redistribution license; excluded with legacy renders.',
        'notices': list(REQUIRED_NOTICES), 'excluded_asset_sha256': sorted(FORBIDDEN_SHA256),
        'documentation_policy': 'Exported documentation/evidence omits local machine paths; transformed files retain their original SHA256 in the manifest.',
    }
    lineage_data = (json.dumps(lineage, indent=2, sort_keys=True) + '\n').encode('utf-8')
    records.append({'path': LINEAGE, 'bytes': len(lineage_data), 'sha256': hashlib.sha256(lineage_data).hexdigest()})
    records.sort(key=lambda item: item['path'])
    manifest = {'format': 'drosolift-public-source-manifest', 'version': 1,
                'files': records, 'total_bytes': sum(item['bytes'] for item in records),
                'exclusions': exclusions, 'manifest_self_excluded': True}
    manifest_data = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode('utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir()  # Exclusive creation: never overwrite an existing directory.
    try:
        for record in records:
            name = record['path']
            data = lineage_data if name == LINEAGE else _inspect(name, _read(root, name))[0]
            if hashlib.sha256(data).hexdigest() != record['sha256']:
                raise ValueError(f'Source changed during publication validation: {name}')
            target = output.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as stream:
                stream.write(data)
        with (output / MANIFEST).open('xb') as stream:
            stream.write(manifest_data)
        verify_public_source(output)
    except BaseException:
        # Only this newly-created directory is removable; verify its exact
        # resolved absolute identity and parent before recursive cleanup.
        if (not output.is_symlink() and output.resolve() == output
                and output.parent.resolve() == output.parent and output != root
                and not root.is_relative_to(output)):
            shutil.rmtree(output)
        raise
    return output


def verify_public_source(root: Path) -> dict:
    """Validate every exported checksum; a later .git directory is ignored."""
    root = Path(root).resolve(strict=True)
    manifest = json.loads((root / MANIFEST).read_text(encoding='utf-8'))
    if manifest.get('format') != 'drosolift-public-source-manifest' or manifest.get('version') != 1:
        raise ValueError('Unsupported public source manifest')
    expected = {MANIFEST}
    for record in manifest['files']:
        name = record['path']
        if name in expected:
            raise ValueError('Duplicate public source manifest path')
        expected.add(name)
        data = _read(root, name)
        if len(data) != record['bytes'] or hashlib.sha256(data).hexdigest() != record['sha256']:
            raise ValueError(f'Public source checksum mismatch: {name}')
        _inspect(name, data)
    found = {p.relative_to(root).as_posix() for p in root.rglob('*')
             if '.git' not in p.relative_to(root).parts and (p.is_file() or p.is_symlink())}
    if found != expected:
        raise ValueError('Public source contains missing or unmanifested files')
    if not set(REQUIRED_NOTICES) <= expected:
        raise ValueError('Public source is missing required notices')
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--output', type=Path, help='Fresh directory outside the implementation checkout')
    action.add_argument('--verify', type=Path, help='Verify an existing source snapshot without requiring upstream Git history')
    args = parser.parse_args()
    try:
        if args.verify is not None:
            manifest = verify_public_source(args.verify)
            print(f'Public source snapshot verified: {len(manifest["files"])} files')
            return
        result = export_public_source(args.root, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Public source export rejected: {error}\n')
    print(f'Public source snapshot verified: {result}')


if __name__ == '__main__':
    main()
