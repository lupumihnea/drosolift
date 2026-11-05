# DrosoLift implementation plan

This plan defines a local build and a portable recorded demo. The original gates
are preserved below. Execution on 4 November 2026 produced the following evidence.

## Publication hardening — 5 November 2026 (complete)

The user authorized the following repairs and a new GitHub repository. They
explicitly declined deployment and hosting. No hosting resources are to be created.

1. Preserve the audited implementation/history locally; produce a separate clean
   source snapshot omitting the legacy GLB with no redistribution license and its
   old rendered media. Preserve license/notices and record upstream lineage.
2. Add opt-in isolated cookie sessions, exact-Origin validation, bounded resource
   use and SQLite persistence. Preserve ordinary local `gym-web` behavior.
3. Restore complete model/training state on reconnect/restart, without offline
   rewards. Make retry deduplication durable beyond the former 1024-ID limit.
4. Provide reproducible pinned installs, CI, container/self-host instructions and
   static recorded-demo configuration for future repository visitors.
5. Verify focused regressions, the full suites, source/data checks, clean-source
   builds and real browser isolation/restart/control flows. Record actual results
   and any environment gaps before publication.

Acceptance: two browser profiles cannot control each other's gym; private progress
survives a backend restart; old command retries apply once; a clean public source
build passes without the restricted asset; actual UI and replay remain usable.
See [RELEASE.md](RELEASE.md) for the release inventory and evidence.

Verification now passes: **209 Python tests / 341.248 s**, **67 frontend tests /
1,632 assertions**, all three builds, official hashes/edges, import boundary and
Git whitespace checks. Real browser profiles remained isolated; weight 0.6→0.8
applied at step 66, and abrupt backend termination restored exact paused states at
steps 67/202 with original retry acknowledgement. Current desktop/X-ray/mobile
screenshots and JSON evidence are in `evidence/publication`. A fresh Python
dependency install passes. The latest offline package passes bench/curl at root
and subpath through WebGPU, with exact exports and no model WebSocket.

The clean-source review cloned with all **454 file hashes** intact; frozen Bun
installed 29 packages, and all 67 frontend tests/1,632 assertions and both public/
replay builds passed. The final publication snapshot adds settled evidence,
attributes and release documentation. Root manifest/lineage files enumerate its
exact contents. Public repository target:
`https://github.com/lupumihnea/drosolift`. Docker Compose validates; runtime-image
build and Linux CI subsequently passed as recorded below. The local Docker
daemon remains unavailable. No deployment was authorized or performed.

Publication: the licensed 469-file snapshot was pushed to `main` at `7856581`;
an ordinary Windows clone with `core.autocrlf=true` verified every byte/hash.
First Linux CI passed frontend and Docker builds/data validation, then found one
Windows/Linux continuous-value fixture rounding mismatch (~4.4e-16). The focused
test repair uses 1e-12 abs/relative tolerance only for continuous measurements,
with exact IDs, types, clocks and counters. All 10 recording-module tests pass;
the complete Linux CI and audience browser check are rerun automatically.
The second run passed all **214 Python tests / 139.921 s** plus frontend/container
builds and data validation, then hit a pause-click timeout under two concurrent
full-3D browser profiles. The revised audience check retains A's full WebGL2
screen/captures and explicitly tests B's live numerical fallback (91 exact
readings, HTML controls, 2D history). That flow passes on Windows with exact
A/B restart at steps 66/135; prior native evidence is preserved in its original
paths. New evidence is in `evidence/publication/numerical-fallback`; Linux
acceptance is rerun. Production calculations and renderers remain unchanged.

Final gate: [GitHub run 41950656218](https://github.com/lupumihnea/drosolift/actions/runs/41950656218)
is **completed / success** for `50c08af`. All three jobs passed: **214 Python
tests / 143.938 s**, **67 frontend tests / 1,632 assertions**, all web builds,
runtime Docker build, pinned source/data validation and the actual Linux browser
flow with full WebGL2 plus numerical fallback, exact reload/restart and retries.
The compact record is `evidence/publication/github-final-ci.json`. Final changes
only record evidence/documentation and update source lineage/checksums; executable
and test files match the verified commit. GitHub publication is complete. Hosting
remains an optional future task for repository visitors; no deployment occurred.

## Execution record — 4 November 2026

Separate implementation clone: `implementation`, branch `drosolift/implementation`,
based on `2c5a03aa90f01048f011e13546b4d7fffc693945`. Upstream history, instructions,
LICENSE and NOTICE remain. The approved DrosoLift overlay is appended to AGENTS.md.
No author name/email was configured, so changes remain reviewable without inventing
a commit identity. The original handoff remains outside this checkout unchanged.

### P0 — reproduced, with measured upstream failures and a verified repair

Read the four handoff documents and opened all three reference PNGs before visual
decisions. [BASELINE.md](BASELINE.md) maps upstream files to screens and records
asset decisions, exact environment-equivalent commands, source sizes and failures.
The pinned Bun lockfile was retained. Baseline frontend tests: **35 passed**;
baseline typecheck/build succeeded using `bun --bun run build` on host Node 18.

Untouched gym startup and the original Python suite stalled while expanding the
151,856,684-row weights table: over ten minutes without an HTTP port, approximately
5.3 GB paged memory. Missing raw sources and a POSIX-only test assertion were
also identified, recorded and repaired rather than reported as passes. The
three official sources total **1,109,008,094 bytes**, downloaded outside Git and
verified against their pinned SHA256. Compact artifacts alone were insufficient
for upstream startup, contrary to the initial handoff estimate.

Bounded Arrow-batch edge validation retains full source checksums and exact
edge/count/row semantics. The final normal startup measured **12.577 seconds**,
225,427,456 bytes working set and 437,583,872 bytes peak on the named Windows host
after filesystem cache warm-up ([startup.json](evidence/startup.json)). This is
not a cold-install timing. The untouched compiled frontend was captured through
a compatible optimized backend, explicitly qualified in the baseline record.
[Baseline 1280 screenshot](evidence/p0-workout-1280.png),
[1920 screenshot](evidence/p0-workout-1920.png) and
[actual telemetry](evidence/p0-telemetry.json) include official body 11517 changing
from 0.5433102371762327 at step 515 to 0.5433773812606072 at step 517.

### P1 — reviewable workout delivered; artistic differences remain explicit

The running [live gym](http://127.0.0.1:8000/?renderer=webgl) uses the original
Python compact model and equipment integration. An original reproducible
Apache-2.0 procedural fly replaces the unlicensed walking GLB in the runtime.
It has six independent articulated legs, red compound-eye facets, segmented
chitin, bristles and translucent veined wings. Front-leg IK reaches the actual
bar targets at bottom, midpoint and top, with both bench and curl regressions.
The full body, bench, plates and bar fit both requested resolutions. Studio
lighting, steel reflection, dark padding and a graphite surface were iterated
against real screenshots; the neural panel occupies approximately 38% of desktop.

Actual browser evidence:
[workout 1280×720](evidence/native/workout-1280x720.png),
[workout 1920×1080](evidence/native/workout-1920x1080.png),
[received telemetry](evidence/native/browser-telemetry.json),
[23.08-second actual screen recording](evidence/native/drosolift-live-demo.webm).
The native run observed rep 15→16 and 28 distinct rates for official DNp09 body
10783 across 96 samples. The recorded demo contains completed reps 18 through 21.
[ASSETS.md](ASSETS.md) identifies the geometry actually displayed, transformations,
license and source hashes. Remaining art work: the fly is stylized, the floor and
bench are simpler than the photographic reference, and far resting legs can be
occluded by the body/apparatus. The default view is more frontal than reference
01 to expose both bar grips; the camera remains orbitable. These are not measured
insect biomechanics.

### P2 — authoritative controls and official morphology verified

The additive `/ws?controls=1` negotiation preserves legacy schema 1/2/3 messages.
Loads are finite within 0.1–3 model force units, command IDs are duplicate-safe,
and Python acknowledges the effective step. A pending load applies at a bottom/
rack boundary. Pause stops the model clock after acknowledgement. The native
browser queued 0.6→0.8, applied at step 705, and retried the same command without
applying twice. Paused step 656 froze; reconnect preserved step 821 and the run.
Invalid/nonfinite/conflicting commands and partial strokes are regression-tested.

Stable neuron selection, exact values and received history preserve zero versus
unobserved activity. Camera, selection, rapid X-ray toggles and detailed geometry
leave received equipment and neural samples unchanged. X-ray fades the authored
body without asserting within-body atlas registration. The large external view
uses measured native soma coordinates and official public SWCs for bodies 10783
and 11177. The cache preserves 22,413 parent edges and is 978,668 bytes. Source
URLs, CC BY 4.0 terms, 8 nm units and normalization are in
[MORPHOLOGY.md](MORPHOLOGY.md). No token or invented morphology was used.
[X-ray 1280](evidence/native/neurons-xray-1280x720.png),
[X-ray 1920](evidence/native/neurons-xray-1920x1080.png) and
[PROTOCOL.md](PROTOCOL.md) provide visual and numerical evidence.

### P3 — exact backend-free replay verified

The versioned `drosolift-recording` format stores initial state, run ID, seed,
timestep, source/circuit hashes and exact official-ID/value frames. The included
20-second seed-7, load-0.6, learning-disabled sample contains **201 frames, 91
readings per frame, five completed repetitions and 2.232383 positive work**.
CSV and JSON use the same sampled clock and counters. CLI recording starts with
fresh memory and does not reset a user's persistent memories. Live export retains
the bounded received capture, initial provenance and load-state history.

The recorded build defaults to RECORDED without a backend or WebSocket. With the
model backend stopped and health unreachable, root and `/conference/` hosting
both sought exactly to step 100, preserved repetition counts, paused/restarted,
advanced four recorded steps during the quarter-speed check, and round-tripped
all exact JSON frames plus 201 CSV rows. The replay build was also tested without
a replay query. [Offline checks](evidence/offline/browser-results.json),
[replay 1280](evidence/offline/replay-1280x720.png) and
[replay 1920](evidence/offline/replay-1920x1080.png) are saved.

The local-video panel has one model playhead and a manual positive offset; until
a file is chosen it clearly says VIDEO PLACEHOLDER. Using the actual app recording
as a local test fixture, a two-second offset aligned to exactly 6.52 video seconds.
Recorded observer tabs preserve step 78 through NEURONS→WORKOUT→REPLAY and open
zero WebSockets; returning to live is explicit. User videos remain local.
No human sample video has been supplied. A Windows registry MIME mismatch in
bare `http.server` was found by the actual browser and repaired with the bundled
standard-library `scripts/serve_replay.py` / archive `serve.py`.

### P4 — deterministic fixed-budget comparison exported

[COMPARISON.md](COMPARISON.md) documents the frozen load-0.6 calibration,
authored four-second actual neural-command window and matched periodic control.
Both inputs use exactly 174.34679255998174 commanded positive impulse over 60 s,
before fatigue/lowering/recovery gates. Evaluation loads 0.4, 0.8 and 1.2 have
identical initial mechanics and remain outside calibration. This is explicitly
open-loop recorded neural drive, with no claim of online feedback or biological
replication. The normal neural model itself remains unchanged.

| Load | Recorded neural reps | Periodic reps | Recorded neural work | Periodic work |
| ---: | ---: | ---: | ---: | ---: |
| 0.4 | 16 | 15 | 4.760000 | 4.200000 |
| 0.8 | 11 | 11 | 6.720000 | 7.499729 |
| 1.2 | 7 | 4 | 6.305143 | 7.201256 |

All conditions reached the top stop; maximum travel is measured at the existing
physics substeps to avoid undersampling. Six deterministic repeats matched every
mechanics sample. The periodic controller ties at 0.8 and performs more positive
work at 0.8 and 1.2. No overall neural advantage is claimed.
[CSV](evidence/p4-summary.csv), [results](evidence/p4-results.json),
[PNG plot](evidence/p4-comparison.png) and [SVG plot](evidence/p4-comparison.svg)
derive from saved runs. Full traces and calibration remain under ignored
`data/runs/comparison`. Optional Matplotlib is separate from app requirements.

### P5 — conference verification and package

The final native browser run passed all live flows with **zero page errors** on
Windows 10 build 19045, AMD64/12 logical CPUs, Chrome 157.0.8103.15 and NVIDIA
GeForce GTX 1060 6 GB. WebGL2 used ANGLE/D3D11. At 1280×720, after 1.5 s warm-up,
the two real Three.js loops each produced 1,437 callbacks over 10.0004 s, or
**143.59 callbacks/s**, maximum gap 7.1 ms. This exceeds the initial 30 FPS cadence
target; GPU completion/scanout time is not measured. Forced SwiftShader achieved
only 3.43 callbacks/s and is separately qualified, not presented as GPU performance.
The default graphics path initialized **WebGPU successfully**. A deliberately
disabled renderer preserved all 91 numerical readings and reachable model controls.
320/390 layouts, pause/reload/reconnect and exact telemetry were exercised.
[Native browser checks](evidence/native/browser-results.json) retain the details.

Python: **143 tests passed in 201.746 s** in full discovery, then the added
comparison/downloader/package/portable CLI checks passed separately. Frontend:
**46 tests passed, 266 expectations**, strict TypeScript and normal/replay
production builds passed. Official data validation passed all source rows and
selected edges. The Three.js shared chunk remains about 859 KB raw / 233 KB gzip;
Vite's 600 KB warning is retained. See `evidence/python-checks.log`,
`supporting-checks.txt`, `frontend-checks.log`, `frontend-build.log`,
`replay-build.log` and `data-status.log`. No `brain`↔`world` direct imports were added.
The new comparison/downloader/package checks total 14 tests; the supporting log
also reruns four overlapping CLI tests. `git diff --check` passed. Optional
diagnostics observed stable renderer resources over five X-ray cycles: workout
89 geometry objects / 9 textures / 45,758,411 estimated bytes; atlas/detail 5 /
2 / 3,349,121. These are renderer estimates, not measured driver VRAM. Actual
paused 1→10→1 population changes and network loss/reconnect also passed.
[QA.md](QA.md) and [the final aggregate](evidence/browser-results.json) retain
commands, resource counts, screenshots and qualifications. Removed identities
retain physical state/recovery; adding them again does not promise reattachment.

Startup, static-build, source-download, recording, comparison and package commands
are documented in README.md and Makefile. The redistributable package excludes
raw data and upstream GLBs, includes the recorded sample, provenance, notices,
Three.js MIT license and a MIME-correct static server. Package creation and
extracted-package verification are recorded in `evidence/package-verification.json`.
The actual native demo is `evidence/native/drosolift-live-demo.webm`.

Remaining scope: photographic surface quality, validated body/atlas registration,
online closed-loop controller comparisons, broader seeds/sensitivity analysis and
biological calibration. A user-supplied human video is required for a meaningful
human/model comparison; the implementation retains a labeled placeholder.

---

## Follow-up — exercise and neural demonstration upgrade

The audience requested stronger neural visuals during exercise and use of the
other gym apparatus. This follow-up preserves the completed P0–P5 evidence above
and executes the corresponding gates in order for the changed behavior.

### P0 — baseline and decisions

Re-read the project prompt, source/asset decisions and applicable instructions;
opened all three reference PNGs before visual work. Retained the existing audited
checkout and all upstream history/notices. The original recording, package and
P4 calibration remain preserved. New apparatus feedback is optional and defaults
to `none`, so it cannot silently change the earlier experimental condition.

Decision: stronger exercise-dependent neural readings require an explicit model
input rather than painting values by exercise name. The new versioned apparatus
lights feed the existing official L2 channels before model stepping. Source,
equations, limitations and exact input metadata are inspectable in
[EXERCISES.md](EXERCISES.md) and
[apparatus-visual-v1.md](../science/apparatus-visual-v1.md).

### P1 — workout and apparatus

Both upstream apparatus kinds are reachable from the same workout screen.
Python reserves an available apparatus and applies setup at a safe stopped
boundary with acknowledged effective steps. Setup preserves accumulated work,
repetitions and sets. Retry, pause, occupancy, incomplete stroke and legacy
baseline behavior have focused regressions. Frontend regressions check grip
targets, inclined curl supports and station-anchor changes before interpolation.

The authored fly, gym hardware, surfaces and lighting were refined against
reference 01. Real native-browser bench/curl screenshots at 1280×720 and
1920×1080 are retained under `evidence/visual-revision/` and the combined final
acceptance frames under `evidence/demo-v2/`. A connecting frame captured during
server restart was rejected as visual evidence; subsequent frames use actual
attached model states. No imported unlicensed fly asset was introduced.

### P2 — inspectable neural view

Expanded the licensed morphology cache from two descending cells to eight
official sensory, relay and descending cells in the same native atlas frame.
The atlas camera reveals the brain-to-VNC extent. Circuit mode uses explicitly
authored positions and official edges; role-group means use received cells only.
Exact IDs, values and traces remain available. Received zero and unobserved
anatomy remain distinct. The fly's optional motor-command overlay is labeled
authored, separate from the anatomical atlas. See [DEMO_UPGRADE.md](DEMO_UPGRADE.md)
and [MORPHOLOGY.md](MORPHOLOGY.md) for bounds and display calibration.

### P3 — two exact recorded scenarios

Added separately identified actual 20-second bench and curl recordings, each
with 201 frames, 91 official IDs and same-clock control/input history. Bench
completes five repetitions at load 0.6; curl completes six at load 0.4. Every L2
value matches the applied visual input: zero mismatches. The earlier baseline
recording is unchanged and every frame reproduces with feedback `none`.
Recorded observer tabs never connect to the live model. Entering replay disables
live population setup. The video-alignment export specifies its nonzero recording
start explicitly. [Scenario evidence](evidence/exercise-feedback.json).

### P4 — preserve the original comparison

The earlier fixed-budget comparison and its calibration remain on the original
condition. They are not reused as evidence for the new sensory profile. New
demonstration measurements describe only the two identified recordings and the
engineered light/input relationship; they do not establish biological exercise
specialization or controller superiority.

### P5 — final verification

Final Python discovery passed **171 tests in 155.580 s**, including the original
profile's exact frame reproduction, two shared-boundary acknowledgment regressions
and three complete-package scenario checks. Relevant protocol/world regressions
passed **28 tests in 24.589 s**. See `evidence/python-exercise-checks.log` and
`evidence/ack-boundary-checks.log`. Frontend passed **57 tests / 1,556 expectations**
across 18 files, strict TypeScript and both production builds. The shared Three.js
chunk is 861.01 KB raw / 233.85 KB gzip; the existing 600 KB warning is retained.
See `evidence/frontend-exercise-checks.log`, `evidence/frontend-exercise-build.log`
and `evidence/replay-exercise-build.log`.

The first WebGPU visual review exposed one-pixel point primitives and invisible
textured point halos. Actual camera-facing sprites now render the observed
markers on both paths; context remains bounded untextured points. Normal
blending avoids white morphology clipping. Shared sprite resources have a
red-to-green disposal regression. A 320-pixel header overflow found in real
browser verification was repaired with a two-row header. The overview camera
also hides the outside studio shell so it can show the full arena.

The final audience-flow check passed with **zero page errors**. It exercised
actual live Bench→Curl setup, pending/retried commands, paused-state invariance,
a complete curl return, cumulative counters and recorded-mode population lockout.
Both offline samples seek exactly to step 111 and export all 201 original frames
with **zero WebSocket connections**. [Browser report](evidence/demo-v2/browser-checks.json).
Native Chrome 157 on Windows 10 / GTX 1060 6 GB rendered both actual Three.js
loops at **143.59 requestAnimationFrame callbacks/s** over the measured ten-second
interval at 1280×720 after warm-up. This measures presentation callbacks, not GPU
completion, scanout or neural computation rate.

Both **WebGPU and WebGL2** passed visual/mode checks, all three cameras and
320/390 layouts with no horizontal overflow. Five X-ray/circuit/atlas cycles
retained stable geometry/texture counts and no estimated memory growth:
WebGPU workout 51 geometries / 12 textures, atlas 22 / 3; WebGL2 the same counts.
Byte estimates decreased slightly as view-dependent resources settled; they are
renderer estimates, not driver VRAM. With rendering deliberately unavailable,
all **91 numerical readings**, exercise selection and play/pause still worked.
[Presentation report](evidence/demo-v2/presentation-checks.json).

The actual **24-second 1280×720 VP9 video** demonstrates bench, neural selection,
curl and circuit view from the bundled model recordings. Only the initial
renderer startup wait was trimmed; the original capture is preserved outside
Git under `data/runs/demo-v2/`. The exported video is 1,429,645 bytes, SHA-256
`8e3ba39e2ef15e5b2889dd142ca92d5ed80bd158ab05c6c65337fdf016628d05`.
[Watch the actual app](evidence/demo-v2/drosolift-demo-v2.webm).

Final screenshots:
[bench 720p](evidence/demo-v2/bench-1280x720.png),
[bench 1080p](evidence/demo-v2/bench-1920x1080.png),
[curl 1080p](evidence/demo-v2/curl-1920x1080.png),
[anatomy and X-ray](evidence/demo-v2/curl-anatomy-xray-1920x1080.png),
[circuit](evidence/demo-v2/curl-circuit-xray-1920x1080.png).
The original conference ZIP remains preserved; this revision produces
`data/runs/drosolift-conference-v2.zip`. Its extracted root/subpath acceptance
and manifest hashes are recorded after package creation in
`evidence/demo-v2/package-verification.json`.

**Extracted-package gate passed:** 58 ZIP entries and all 57 manifest hashes
verified; both Bench/Curl scenarios passed at `/` and `/demo/` with exact exports,
selected rates, latched inputs and step-111 repetition counts (bench 2 / curl 3).
All four flows had zero WebSockets, external requests and page errors; JavaScript
MIME types were correct. Native WebGPU initialized from the extracted package.
Archive size is **12,356,579 bytes**, SHA-256
`0d796d718b93ff3df40057ae257799210a48e76015a80154a93ee72f026e1a29`.
The report and this final verification note are produced after the immutable
archive; its embedded plan is the snapshot taken immediately before extraction.

```powershell
.venv\Scripts\python.exe scripts/package_conference.py --output data/runs/drosolift-conference-v2.zip
.venv\Scripts\python.exe scripts/check_conference_package.py --archive data/runs/drosolift-conference-v2.zip --port 8211 --output docs/drosolift/evidence/demo-v2/package-verification.json
.venv\Scripts\python.exe -B -m unittest tests.test_package_conference tests.test_conference_verifier -v
git diff --check
```

The eight package/verifier unit checks passed in 0.994 s; final whitespace check
passed. No Git author is configured, so the implementation remains a reviewable
uncommitted change set and user Git configuration was left intact. Live gym
remains on port 8000 with the optional feedback profile; portable replay remains
on port 8010. Package verifier-owned servers were closed after checking.

Remaining scope includes photographic anatomy,
validated body/atlas registration, additional exercise physics, biological
calibration and broader controller comparisons.

## Follow-up — reference neural UI and training controls, 5 November 2026

The supplied screenshot is a visual reference only. Its FlyWire name, counts,
spike events and scale are not adopted as this model's data. Preserve the MaleCNS
source, actual rate telemetry and historical comparison. The current checkpoint
is P1/P2 implementation, followed by audience-flow and final package verification.

- **P0:** opened the new reference; audited existing fitness and per-fly state.
  Fitness is earned on a completed three-repetition set, not a button boost.
  Existing independent identities and bounded population setup support selection.
- **P1:** address the twelve annotations and remove the marked clutter; clarify weight changes,
  expose fly selection and real training progress; display applied weight as
  plates while preserving actual q/grip transforms.
- **P2:** match the large frontal blue brain, cyan/yellow rate accents, display
  modes, received-rate history and readout hierarchy. Improve the authored body
  X-ray with actual identity/value markers and clearly qualified placement.
- **P3/P4:** retain offline samples, exports and old comparisons without the
  Replay navigation tab; do not modify the model's learning or force calibration.
- **P5:** verify 1184×839 (annotation viewport), 1280×720, 1920×1080 and narrow
  layouts. Exercise Add weight, safe pending/application, New fly, selection,
  earned fitness, both apparatus kinds, neural modes and X-ray through the real
  browser. Record screenshots, checks, remaining gaps and a fresh demo package.

### Completed reference/training gates

**P1/P2 pass:** all marked visible elements are removed. The actual 1184×839
annotation viewport, 1280×720 and 1920×1080 screenshots show the frontal blue
brain, received cyan/yellow rates, history and compact readouts beside the gym.
The display crop retains **124,294 measured somata** at native normalized
`Z <= -0.28`; it is a display cutoff, not an official ROI. The eight licensed
SWCs and all source coordinates remain unchanged. Cell colors has its own
group legend. The **96-column × 91-cell** rate history resets on individual,
run identity and backward seek. X-ray preserves all 91 official IDs and 92 edges
on a labeled authored body layout; no spike events or body registration are
claimed. [Training UI report](TRAINING_UI.md), [morphology](MORPHOLOGY.md),
[asset calibration](ASSETS.md).

**Actual control and training pass:** the audience flow activates Fly 03 and
observes its first earned set: **0→1 sets, fitness 1.000→1.005**. Choosing flies
and changing neural/X-ray views preserve the frozen model frame and send no
model commands. A paused pending weight preserves plate geometry. At applied
steps, bench station 1 changes **1.0→1.2**, **5→6 discs per stack**; curl station 4
changes **0.4→0.6**, **2→3 per stack**. Full grips and actual bar motion remain
unchanged. Exercise and weight setup controls wait for one another at safe
boundaries. The old live run and memories were retained, without a server reset.
[Audience-flow evidence](evidence/demo-v3/browser-checks.json).

**Checks pass:** Python **171 tests / 469.798 s**, frontend **64 tests / 1,615
expectations / 21 files**, strict TypeScript and both production builds. Official
data validation checks all **151,856,684** source weight rows and the selected
edges; no direct brain/world imports were added. Logs are in `evidence/demo-v3/`.
The shared Three.js chunk is **870.63 KB raw / 237.04 KB gzip**; the existing
600 KB warning remains documented. Eight focused package/verifier tests pass.

Native Chrome 157 / Windows 10 / GTX 1060 6 GB observed **143.59 callbacks/s** in
both real render loops over ten seconds after warm-up at 1280×720. This is
requestAnimationFrame cadence, not measured GPU completion or model speed.
Both **WebGPU and WebGL2** pass, with zero page errors. Five activity/Cell-color/
X-ray cycles retain exact renderer object/byte estimates: workout **56 geometries,
12 textures**; neural view **20 geometries, 3 textures**. WebGPU estimates are
49,845,144 + 4,415,305 bytes; WebGL2 estimates 49,711,690 + 4,416,884. These are
renderer estimates, not driver VRAM. Both 320/390 layouts have no horizontal
overflow. With graphics deliberately unavailable, all **91 readings**, playback
and exact **201-frame export** remain available, with no page errors.

The real browser found an expanded data-list overlay intercepting its summary;
it now uses normal document flow. A failed graphics initialization also exposed
Three r186 disposal re-entering initialization without handling the rejection.
Cleanup now disposes initialized managers only; the detached uninitialized
canvas is collected. Targeted real-browser reruns verify both fixes, preserving
the already-passed live-flow evidence. Instance buffers now dispose once per
object while shared geometry/material resources remain deduplicated.

The actual live walkthrough is **24.36 s, 1280×720 VP9**, 1,227,225 bytes, SHA-256
`f52ab672fa74e9f2fa9eb1c2592a80eed55bcbfe51f1743ae13f69fc5c47759f`.
It shows Fly 03, added weight, neural X-ray, bench/curl and both neural modes.
Only renderer/setup wait before the interaction is trimmed; the raw capture
is preserved outside Git. [Video](evidence/demo-v3/drosolift-training-demo.webm)
and [exact capture metadata](evidence/demo-v3/video-checks.json).

Screenshots: [bench / annotation viewport](evidence/demo-v3/training-bench-1184x839.png),
[curl / 1080p](evidence/demo-v3/training-curl-1920x1080.png),
[neural X-ray](evidence/demo-v3/neural-xray-1184x839.png),
[native WebGPU](evidence/demo-v3/training-default-1184x839.png).
The fresh portable artifact is `data/runs/drosolift-conference-v3.zip`;
its post-creation root/subpath report is `evidence/demo-v3/package-verification.json`.
The earlier packages remain preserved.

**Final v3 package gate passed:** **69 entries / 68 manifest hashes** verified.
Both Bench/Curl scenarios pass at `/` and `/demo/` in native WebGPU, with exact
step-111 counters (bench 2 / curl 3), selected-neuron precision, latched inputs
and complete original-frame exports. All four cases have **zero WebSockets,
external requests or page errors** and correct JavaScript MIME types. The ZIP
is **15,141,659 bytes**, SHA-256
`031294ee500d49353ff5944552cc7a080b9ceb52ee311b166effe48846b36b09`.
The post-creation [verification report](evidence/demo-v3/package-verification.json)
and this final note follow the archive's immutable documentation snapshot.
Verifier-owned servers were closed; the original live process remains healthy
on port 8000 with population three. No user training state was reset.

Remaining limits: the fly is stylized; body neural placement is illustrative;
eight selected morphologies do not represent all compact cells; the display
shows rates rather than spikes. Individuals share the pinned model/circuit but
have independent state. Fitness/counters persist for the live server run, while
only existing learning memories persist across restarts. This revision does not
change the P4 comparison or introduce biological strength claims.

## Original milestone gates

## P0 · Reproduce the base and record decisions

Work in a separate checkout of the audited revision. Read the applicable project instructions. Install the source's Python requirements and use its existing Bun lockfile for the frontend. Start with the committed compact model artifacts.

Run the normal Python tests, frontend tests and production build. Launch the gym with one fly through its existing entry point. Inspect the rendered page and record a sample of actual telemetry. Map the scene and protocol files listed in SOURCES.md to the new screens.

Acceptance evidence

- A running gym at a documented localhost URL.
- Results of `make test`, `make frontend-test`, `make frontend-build` or documented environment-equivalent commands.
- A screenshot and a short sample matching an official ID to received activity.
- A concise source/assets decision and a list of actual baseline failures, if any.
- An estimate of which source downloads are necessary. Start the visual work using committed compact artifacts while raw-data reproduction is prepared separately.

## P1 · Ship the first compelling workout screen

Replace the asset with a redistributable rig. Tune an accurately scaled fly, steel bench/rack, bar, plates, rubber surface, materials and lighting against reference 01. Keep bar movement authoritative and solve the front-leg grips against its targets.

Retain the real anatomical panel from the base. Compose the workout and neural area to remain useful on a 16:9 conference display. Implement reachable pause/resume and camera controls.

Acceptance evidence

- Full-body fly, bench and bar visible at 1280×720 and 1920×1080.
- Six-legged rig with front-leg contact maintained at the top and bottom of the stroke.
- Visible motion synchronized with received equipment position.
- An inspectable neural value changing with real telemetry.
- Source/rights record for the model actually displayed.
- At least one full repetition captured in the actual browser.
- A note of remaining differences from reference 01.

## P2 · Add load control and inspect the circuit

Extend the existing command flow for a bounded load update with an acknowledged effective state. Preserve the existing client behavior. Add a force/load readout in model units, observed activity history and stable selection by body ID.

Create an X-ray material mode, a native-coordinate anatomical view and a small detailed skeleton view. First verify public download and licensing of selected morphologies. The official neuPrint route needs a user token. Use documented public downloads where available. If morphology access is blocked, deliver the measured soma/circuit view and record the remaining access requirement while continuing other work.

Acceptance evidence

- Add Load affects the next eligible repetition and acknowledges the applied step.
- Invalid, repeated and retried commands leave the state consistent.
- Pause, resume and reconnect restore the same authoritative state.
- A selected neuron remains selected as activity rankings change.
- The same trace under different camera/X-ray settings has identical equipment and neural samples.
- Every geometry/reading maps to the recorded source or is labeled an authored overlay.
- Actual screenshots of both neural and workout views.

## P3 · Record and replay a complete run

Add one versioned recording/export path that preserves states, time and provenance. Build a static replay entry using the same view code. Include one licensed sample with actual recorded activity.

Add a user-video panel with a manually chosen synchronization offset. Use the same playhead for recorded video time and model states. Provide seek, restart and slower playback.

Acceptance evidence

- The recorded demo opens with the Python backend stopped.
- Seeking to a known time reproduces the corresponding state and repetition count.
- Slowing playback changes presentation time while preserving recorded event timing.
- A short sample works at the root and under a static hosting subpath.
- CSV and exact recording describe the same completed repetitions.
- The interface clearly identifies live and recorded operation.

## P4 · Run the reproducible bench comparison

Define a fixed-duration lifting task, period and actuator budget. Keep the same starting state and mechanics for the neural and periodic drive conditions. Specify whether budget matching uses commanded positive actuator impulse or applied positive impulse, and use that choice consistently. Fix the calibration before running the evaluation loads.

Sweep a small predeclared set of virtual loads. Measure completed repetitions, maximum achieved travel and positive mechanical work. Save per-condition traces, model/config versions and any seed. Treat the ordinary period/force waveform as a meaningful control. A tie or a poorer neural result remains part of the exported result.

Acceptance evidence

- One command regenerates the results from the configured inputs.
- Plots and CSV are derived from the saved runs.
- Deterministic repeats are reported as reproducibility checks.
- The report's claims refer to this model and this task.
- The methods state the connectivity source, model dynamics, engineered actuator mapping and simulated mechanics.

## P5 · Verify the conference build

Measure rendering performance on a named test machine over a repeatable interval after warm-up. Aim first for at least 30 FPS at 1280×720 in the default scene. Inspect GPU resource use as views switch, the fallback renderer, network loss and reload.

Prepare a short real screen recording and an offline sample. Check startup from a clean environment. Preserve the source's attribution and record new contributions in the README.

Final acceptance evidence

- Three real screenshots and a 15–30-second actual app recording.
- Working UI controls, real activity display and a portable replay.
- A documented start command, static-build command and experiment command.
- Passed relevant checks, plus explicit hardware or service gaps.
- Asset/data provenance and a redistributable application package.

## Focused regressions to add when the corresponding behavior is introduced

- Zero neural drive produces no new upward work.
- A partial stroke never increments the completed-repetition count.
- Under the same drive, a heavier load follows the expected mechanics.
- Retried load commands take effect once at the documented boundary.
- Pause acknowledgement freezes the model clock and the joint.
- Visual mode changes preserve the stored trajectory.
- Replay round-trips IDs, timestamps, equipment position and repetition counts.
- Missing activity remains distinguishable from zero, including after reconnect.

Prefer these observable behaviors over tests that restate internal implementation.
