# P0 baseline — 4 November 2026

Publication note: this is a historical local-checkout record. The separate public
source preserves its numerical findings and attribution, but omits the original
P0 images/browser captures because they contain the restricted legacy rig. Modern
procedural-fly screenshots are available in `evidence/publication` and `evidence/demo-v3`.

The implementation is a separate clone on `drosolift/implementation`, based on
`tiredbooy/Fruit-Fly` commit `2c5a03aa90f01048f011e13546b4d7fffc693945`.
History, LICENSE, NOTICE and THIRD_PARTY_NOTICES.md are preserved. The handoff is
copied into this directory. Upstream AGENTS.md remains intact with an explicit
authorized DrosoLift overlay for the English interface and bounded load commands.

## Environment and exact commands

Windows, Python 3.12, Node 18.17.0, project-local Bun 1.4.4. GNU make and global Bun
were absent, so these are environment-equivalent upstream entrypoints:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
npm install --prefix .tools bun
.tools\node_modules\bun\bin\bun.exe install --cwd frontend/web --frozen-lockfile
# Run inside frontend/web:
..\..\.tools\node_modules\bun\bin\bun.exe test
..\..\.tools\node_modules\bun\bin\bun.exe --bun run build
# Run inside the repository:
.venv\Scripts\python.exe -B -m unittest discover -s tests -t . -v
.venv\Scripts\python.exe -B main.py data-status
.venv\Scripts\python.exe -B main.py gym-web --flies 1 --seed 7 --port 8000
```

The frozen Bun install succeeded, preserving bun.lock. Plain `bun run build`
initially selected host Node18 and failed on TypeScript7's extensionless ESM `tsc`
entry. `bun --bun run build` completed typechecking and the Vite8 build. Its
largest shared renderer chunk was 844.69kB (229.07kB gzip); Vite warned above 600 kB.

Parallel work introduced intentional new failing tests early, so exact upstream
baseline runs use `git archive` of the pinned revision in ignored
`.tools/p0-baseline`, with junctions to the identical dependencies, raw data and
unchanged baseline dist. No new implementation tests are counted as baseline.
Frontend baseline: **35 passed, 0 failed, 180 expectations across 9 files**.

## Required source downloads

Contrary to the handoff's initial estimate, normal gym startup loads the official
raw release to validate every selected edge. The initial startup and data-status
failed clearly when those files were absent. All three source-manifest URLs were
downloaded under ignored `data/raw/malecns/v1.0` and verified against pinned SHA256:

| Source | Bytes |
| --- | ---: |
| annotations | 14,483,314 |
| connectivity weights | 1,051,241,946 |
| neurotransmitters | 43,282,834 |
| Total | 1,109,008,094 |

No full graph build or raw morphology is needed for the compact workout. Raw
archives and experiment memory remain outside Git. Python dependencies add the
upstream scientific stack; Playwright is installed only for local verification.

## Source-to-screen map

| Screen capability | Existing implementation retained |
| --- | --- |
| Authoritative model and clock | `brain/gym.py`, `simulation/gym.py`, `frontend/gym_server.py` |
| Bench mechanics and reps | `world/equipment.py`, `frontend/web/src/equipment-scene.ts` |
| Actual telemetry and parsing | `frontend/gym_telemetry.py`, `frontend/web/src/gym-snapshot.ts` |
| Anatomy, exact values, filtering | `neuron-map.ts`, `neuron-inspector.ts`, `neuron-readings.ts` |
| Grip contact and poses | `animated-fly.ts`, `foreleg-pose.ts` |
| Renderer and observer cameras | `graphics-renderer.ts`, `fly-scene.ts`, `scene-camera.ts` |

Frontend paths without a prefix above are under `frontend/web/src`.

## Asset decision

The baseline walking GLB has no standalone redistribution permission. It can be
inspected locally as upstream evidence, but must not be the portable demo asset.
The separately attributed CT female surface is CC BY4.0 and unrigged. For the
first redistributed build use a newly authored procedural rig: six articulated
legs, red eyes, translucent wings, and existing measured-bar grip constraints.
Its pose and scale are authored display mechanics, not registered anatomy. Keep
the existing MaleCNS anatomical soma point cloud in native scientific coordinates;
activity is received rate activity, never fabricated spike events. A separate
asset record tracks the exact displayed geometry and remaining art differences.

## Evidence and remaining checks

See `evidence/p0-frontend-tests.txt`, `p0-python-tests.txt`, `data-status.log`,
`p0-telemetry.json`, `p0-browser.json`, `p0-workout-1280.png` and
`p0-workout-1920.png`. Status values below are completed only once their actual
outputs have been inspected.

### Actual baseline outcome

The untouched original startup was stopped after more than 10 minutes without
opening a listening port. The Python process reached approximately 5.3 GB private
paged memory and 10.5 GB virtual memory while hydrating 151,856,684 connectivity
rows. The exact archived Python suite was likewise interrupted during raw-data
loading. Its initial missing-source errors were environmental; a separate
upstream CLI test also revealed a POSIX-only path-string assertion on Windows.
These are recorded baseline gaps, not passes. The source loader was subsequently
changed to inspect bounded Arrow batches while preserving full-file checksums,
exact edge triples, count and row semantics; its focused regression is documented
with the implementation checks.

The original compiled UI was preserved before redesign. It was inspected through
`http://127.0.0.1:8001`, serving unchanged compiled baseline assets and forwarding
same-origin WebSockets to the compatible optimized backend at port 8000. This is
an explicit backend resource deviation from untouched upstream, not an unchanged
upstream-startup claim. Both requested viewport captures succeeded with WebGL2,
no page errors, and the original local-only authored rig. The 1280 px viewport's
original document extended to 951 px tall, recorded with full-page screenshot.

`p0-telemetry.json` contains received steps 515..517, simulation times 51.5..51.7 s,
and 91 compact readings per frame. Official body 11517 (`lLN2T_c`) changed from
0.5433102371762327 to 0.5433773812606072. Received zeros remain in the same payload.
The final browser snapshot reported 64 observed atlas positions, separately from
the 91 received circuit readings.

After the bounded reader and Windows assertion correction, the implementation
completed all 143 Python tests in 201.746 s and data-status validated all
151,856,684 rows, 92 gym runtime edges and 104 gym-learning edges. See
`evidence/python-checks.log` and `evidence/data-status.log`. The later supporting
checks are recorded separately; they are not claimed as untouched upstream.
