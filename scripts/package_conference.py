"""Create a self-contained static conference demo with notices and provenance.

Build first with frontend/web's build:replay script. Output is fresh by default:
existing user packages are never overwritten. Raw data and source GLBs are never
included. Use another output filename when preparing a revised package.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import os
from pathlib import Path
from uuid import uuid4
import zipfile

DOCS = ('ASSETS.md', 'MORPHOLOGY.md', 'PROTOCOL.md', 'COMPARISON.md', 'IMPLEMENTATION_PLAN.md', 'SOURCES.md')
STATIC_EXTENSIONS = {'.html', '.css', '.js', '.json', '.csv', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.ico', '.txt', '.woff', '.woff2'}
RUN_DEMO = '''DrosoLift conference demo

1. Extract this complete ZIP into a folder.
2. Open a terminal in that folder and run:

   python serve.py

3. Open http://127.0.0.1:8010/ in a current desktop browser.

The default screen is RECORDED replay. Pause/play, seek, restart, playback speed,
X-ray, neuron inspection and local video alignment use the bundled actual model
recording. Bench press and Dumbbell curl select separately recorded real runs.
The demo's apparatus lights provide explicitly synthetic visual inputs; the
displayed regional/model-group activity is received from the neural model.
Python here only serves static files; no neural backend, installation
of Python packages, network connection, or raw MaleCNS download is required.

If port 8010 is already in use, run python serve.py --port 8011 and open the
matching URL. This server supplies explicit JavaScript module MIME types,
including on Windows systems whose registry labels .js as text/plain.
The browser needs WebGL2 or compatible WebGPU for 3D. Exact numerical/HTML
readings remain available when graphics cannot initialize. Choose a local video
under Inspect neurons & data > Data & model details > Local video alignment
to replace the labeled placeholder; no video is uploaded.

See LICENSE, NOTICE, THIRD_PARTY_NOTICES.md, licenses/three-MIT.txt and
our docs/drosolift provenance. MANIFEST.sha256 hashes every other packaged file.
The actual screen recording at
docs/drosolift/evidence/demo-v3/drosolift-training-demo.webm is a standalone preview;
open it in a video player. Selected real screenshots accompany the methods.
The experiment comparison uses a frozen recorded neural command window, not an
online biological specimen or a claim of neural superiority.
'''


def package_conference(root: Path, output: Path) -> Path:
    """Validate the bounded static tree, then atomically publish a fresh ZIP."""
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(f'Existing package preserved; choose a fresh output filename: {output}')
    dist = root / 'frontend/web/dist-replay'
    if not (dist / 'index.html').is_file():
        raise FileNotFoundError('Build the replay distribution first: bun --bun run build:replay')
    files: dict[str, bytes] = {}
    for path in sorted(dist.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlink assets are not allowed in the portable demo: {path.name}')
        if not path.is_file():
            continue
        if path.suffix.lower() == '.glb':
            raise ValueError(f'GLB asset rejected; the redistributable demo uses authored procedural geometry: {path.name}')
        if path.suffix.lower() not in STATIC_EXTENSIONS:
            raise ValueError(f'Unexpected non-static asset in replay distribution: {path.name}')
        if path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError(f'Static asset exceeds the 32 MiB per-file budget: {path.name}')
        files[path.relative_to(dist).as_posix()] = path.read_bytes()
    for name in ('LICENSE', 'NOTICE', 'THIRD_PARTY_NOTICES.md', 'licenses/three-MIT.txt',
                 'data/malecns/v1.0/source-manifest.json',
                 *(f'docs/drosolift/{name}' for name in DOCS)):
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f'Required package notice/provenance is missing: {name}')
        files[name] = path.read_bytes()
    # Keep the comparison's linked figure and compact evidence usable offline.
    for name in ('p4-comparison.png', 'p4-comparison.svg', 'p4-summary.csv', 'p4-results.json'):
        path = root / 'docs/drosolift/evidence' / name
        if path.is_file() and not path.is_symlink():
            files[f'docs/drosolift/evidence/{name}'] = path.read_bytes()
    for name in ('equipment.md', 'gym.md'):
        methods = root / 'docs/science' / name
        if methods.is_file() and not methods.is_symlink():
            files[f'docs/science/{name}'] = methods.read_bytes()
    for name in ('docs/drosolift/EXERCISES.md','docs/science/apparatus-visual-v1.md','data/circuits/apparatus-visual-v1.json'):
        path=root/name
        if path.is_file() and not path.is_symlink():files[name]=path.read_bytes()
    for name in ('docs/drosolift/QA.md',
                 'docs/drosolift/DEMO_UPGRADE.md',
                 'docs/drosolift/TRAINING_UI.md',
                 'docs/drosolift/evidence/demo-v3/browser-checks.json',
                 'docs/drosolift/evidence/demo-v3/video-checks.json',
                 'docs/drosolift/evidence/demo-v3/python-checks.log',
                 'docs/drosolift/evidence/demo-v3/frontend-checks.log',
                 'docs/drosolift/evidence/demo-v3/frontend-build.log',
                 'docs/drosolift/evidence/demo-v3/replay-build.log',
                 'docs/drosolift/evidence/demo-v3/drosolift-training-demo.webm',
                 'docs/drosolift/evidence/demo-v3/training-bench-1184x839.png',
                 'docs/drosolift/evidence/demo-v3/training-curl-1920x1080.png',
                 'docs/drosolift/evidence/demo-v3/neural-xray-1184x839.png',
                 'docs/drosolift/evidence/exercise-feedback.json',
                 'docs/drosolift/evidence/python-exercise-checks.log',
                 'docs/drosolift/evidence/ack-boundary-checks.log',
                 'docs/drosolift/evidence/frontend-exercise-checks.log',
                 'docs/drosolift/evidence/frontend-exercise-build.log',
                 'docs/drosolift/evidence/replay-exercise-build.log',
                 'docs/drosolift/evidence/demo-v2/browser-checks.json',
                 'docs/drosolift/evidence/demo-v2/presentation-checks.json',
                 'docs/drosolift/evidence/demo-v2/video-metadata.txt',
                 'docs/drosolift/evidence/demo-v2/drosolift-demo-v2.webm',
                 'docs/drosolift/evidence/demo-v2/bench-1280x720.png',
                 'docs/drosolift/evidence/demo-v2/curl-1920x1080.png',
                 'docs/drosolift/evidence/demo-v2/curl-anatomy-xray-1920x1080.png',
                 'docs/drosolift/evidence/demo-v2/curl-circuit-xray-1920x1080.png',
                 'docs/drosolift/evidence/native/drosolift-live-demo.webm',
                 'docs/drosolift/evidence/native/workout-1280x720.png',
                 'docs/drosolift/evidence/native/neurons-xray-1920x1080.png',
                 'docs/drosolift/evidence/offline/replay-1920x1080.png'):
        path = root / name
        if path.is_file() and not path.is_symlink():
            files[name] = path.read_bytes()
    files['RUN_DEMO.txt'] = RUN_DEMO.encode('utf-8')
    server = root / 'scripts/serve_replay.py'
    if not server.is_file() or server.is_symlink():
        raise FileNotFoundError('Required explicit-MIME static server is missing: scripts/serve_replay.py')
    files['serve.py'] = server.read_bytes()
    if len(files) > 1000 or sum(map(len, files.values())) > 80 * 1024 * 1024:
        raise ValueError('Portable demo exceeds the bounded static package budget')
    files['MANIFEST.sha256'] = ''.join(f'{sha256(data).hexdigest()}  {name}\n' for name, data in sorted(files.items())).encode('utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f'.{output.name}.package-{uuid4().hex}.part')
    try:
        with zipfile.ZipFile(temporary, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data, compresslevel=9)
        with temporary.open('r+b') as stream:
            os.fsync(stream.fileno())
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=root / 'data/runs/drosolift-conference.zip')
    options = parser.parse_args()
    try:
        output = package_conference(root, options.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Package failed: {error}\n')
    print(f'Conference package: {output} ({output.stat().st_size} bytes), SHA256 {sha256(output.read_bytes()).hexdigest()}')

if __name__ == '__main__':
    main()
