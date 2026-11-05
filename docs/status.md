# Project Status

## Publication hardening — 5 November 2026

Completed and published at [lupumihnea/drosolift](https://github.com/lupumihnea/drosolift).
[Final Linux CI](https://github.com/lupumihnea/drosolift/actions/runs/41950656218)
passes all three jobs: 214 Python tests, 67 frontend tests/1,632 assertions, all
web builds, Docker runtime-image build, official data validation and the actual
browser flow (full WebGL2 and numerical fallback, isolated profiles, exact saved
state/restart and retry handling). The source snapshot preserves notices and
lineage while excluding the restricted legacy rig/history. Original history and
the prior running local gym remain preserved. No deployment was performed.

The user requested a GitHub repository and explicitly declined deployment.
An opt-in `public-web` entry point adds independent cookie profiles and durable
full training/model state. SQLite commits checkpoints and command outcomes before
acknowledgement; reconnect/restart restores the exact saved state. Disconnected
profiles do not train. Origin validation, bounded active profiles/sockets and
durable command deduplication replace the shared-session publication hazards.
Legacy `gym-web` retains its local research behavior.

Frontend session bootstrap, pinned dependencies, CI, Docker/self-host instructions
and a clean-source exporter are included. The public source omits an unlicensed
legacy asset and its old renders; upstream history remains preserved locally.
See [RELEASE.md](drosolift/RELEASE.md) for final measured results and remaining
publication/environment gaps, and [SELF_HOST.md](drosolift/SELF_HOST.md) to run it.
The v3 measurements below describe the earlier shared local entry point.

## DrosoLift implementation — 4 November 2026

The 5 November user review adds a frontal reference-inspired blue neural view,
received-rate history, simplified controls, explicit per-fly training progress
and direct weight adjustment with applied plate geometry. The reference image
supplies visual guidance only; activity remains actual MaleCNS model rate data.
Fitness is earned by existing completed-set mechanics and is scoped to the live
server run. No neural model, reward or physics change is introduced. Current
acceptance is tracked in [TRAINING_UI.md](drosolift/TRAINING_UI.md) and the
implementation plan; earlier milestone measurements below are historical.
Final v3 checks pass: 171 Python tests, 64 frontend tests, both production builds,
WebGPU/WebGL2, numerical fallback and the extracted offline package at root and
subpath. A new individual earns 1.000→1.005 fitness from its first completed set;
applied weight changes add visible plates. The updated live walkthrough is
24.36 seconds. Existing live state and both earlier packages remain preserved.

The subsequent demo upgrade adds safe live Bench/Curl apparatus selection,
separately recorded offline scenarios, eight licensed selected morphologies,
an authored circuit layout, received-value group meters and refined fly/gym art.
An optional versioned apparatus-light profile produces actual exercise-dependent
visual-channel responses; the default remains `none`. These are engineered
inputs, not biological exercise-specialized regions. Exact source IDs, rates,
latched input values and effective setup steps remain inspectable.
The upgraded final suite passes 171 Python tests and 57 frontend tests; strict
TypeScript and both production builds pass. Native WebGPU and WebGL2 initialize
and show the new neural markers. All 91 numerical readings and playback survive
a deliberately unavailable renderer; 320/390 layouts have no horizontal overflow.
See [the upgrade report](drosolift/DEMO_UPGRADE.md) and
[its acceptance evidence](drosolift/IMPLEMENTATION_PLAN.md#follow-up--exercise-and-neural-demonstration-upgrade).
Earlier verification and limitations below are retained as the initial baseline.

The separate `drosolift/implementation` checkout adds the English conference
workout, a redistributable six-legged procedural fly, actual compact telemetry,
exact neuron selection/history, native atlas and two official detailed SWCs.
Python-authoritative pause/load controls acknowledge effective steps and preserve
legacy clients. A 201-frame actual recording replays without the model backend,
including static subpaths, local-video alignment and JSON/CSV export.

The full Python suite passed 143 tests, followed by the additional focused
comparison/downloader/package checks; all 46 frontend tests and both production
builds passed. Official data checks passed. Native GTX 1060 WebGL2 measured
143.59 render-loop callbacks/s at 1280×720 over ten seconds; the default WebGPU
path initialized successfully. Software rendering was separately measured at
3.43 callbacks/s. Numerical controls survive graphics failure. These are measured
presentation cadences, not GPU completion or neural update rates.

The fixed-budget open-loop comparison and deterministic repeats are exported,
including outcomes favoring the periodic controller in work. The source loader
now validates bounded Arrow batches rather than hydrating the complete weights
table. Startup measured 12.577 seconds after cache warm-up, about 225 MB working
set. The original stalled baseline, Windows portability/MIME repairs, artifact
rights and remaining stylized art differences are documented rather than hidden.

See [the executed implementation plan](drosolift/IMPLEMENTATION_PLAN.md) for
commands, screenshots, actual demo, evidence, scope and remaining gaps. Original
project status and historical measurements are preserved below.

---

Last updated: 2026-09-13

The public repository includes a 38-second H.264 preview and linked README
thumbnail under `docs/media/`. Original project material is licensed under
Apache-2.0 with a root `NOTICE` that identifies tiredbooy; MaleCNS and visual
asset terms remain separately documented in `THIRD_PARTY_NOTICES.md` and their
source manifests.

## Run the completed gym

```bash
make gym FLIES=3
```

Open <http://127.0.0.1:8000>. Change population from 1 to 10, select a fly,
and inspect its real movement, workout state, neural anatomy and eye camera.
`make gym-run FLIES=3` runs a finite headless experiment. `make web` and
`make web-full` preserve Experiment 1 and its existing memory file.

## Implemented state

Experiment 2 now combines shared dynamic food with independent compact brains,
hunger, smell, simple vision, physical bench presses and dumbbell curls, fatigue, work/set
counts, bounded completion rewards and separate per-fly food/gym association.
The world measures physical outcomes; it never chooses training, food or rest.
Only actual loaded joint displacement earns work; three full up/down strokes
complete a set. Standing still and partial strokes produce no set reward.

The gym runtime has 91 official bodies and 92 validated edges. Synthetic gym
odor uses documented DM2 inputs; its distinct KC-to-MBON plastic edges are
selected from pinned MaleCNS data. This task cue and the physiology/reward
equations are explicit assumptions, not evidence of natural gym behavior.

Up to ten flies start on a separated grid touching alternating bench/curl stations.
Default Experiment 2 keeps active flies restrained at those stations through
two-second inter-set recovery, then permits the next neurally powered set. That
continuous attendance is intentional experimental setup, not learned station seeking. Inactive
flies retain their body and two memories in a bounded bank during a process.
Memory persists separately under `data/runs/experiment-002/fly-N/`; body state
and workout counters restart. Count updates work while paused without advancing
the clock. Selection and camera controls cannot steer or inject neural activity.

The current 308 KB authored rig supplies distance-sampled walking and actual
ingestion-driven feeding. It is user-authorized visual reuse from fly-escape;
no brain/controller code or anatomy dataset is copied. Public redistribution
licensing is not supplied by that source. The former CC-BY female CT asset
remains separately attributed, not misrepresented as the current rig.

The neural panel now shows 139,659 measured soma positions from our own official
annotations, among 166,606 valid bodies. Received-positive, received-zero and
unobserved points are distinct; missing positions are counted, not invented.
Exact official labels/IDs and activity remain searchable behind a disclosure.
Training curves contain actual selected-fly samples, including flat results.

The authored forelegs now reach the moving handles with a two-bone pose solver.
Received support poses place a fly supine on a bench or raised for curls; the
eye camera follows that head height and orientation while attached. These are
illustrative task mechanics, not measured insect biomechanics. No new biological
identities or edges were added. The gym wire protocol is now schema 3; the browser
also reads legacy schema 2, and Experiment 1 remains schema 1.

## Articulated-equipment measurements

A fresh seed-7 continuous-protocol run for 1000 ticks at `dt=0.1` kept all ten
flies on their original stations with zero locomotor distance. Bench flies
completed 7 sets each and curl flies completed 10 sets each; every set still
required three full loaded repetitions. This sustained training is imposed by
the apparatus, not evidence of learned exercise-seeking. Earlier release-and-roam
measurements remain recorded in [equipment science](science/equipment.md).

The compact gym network benchmark changed from 210.13 to 159.26 microseconds per
update (24.2% less time), and E1 from 151.05 to 107.31 (29.0%), using alternating
original/optimized batches. Exact snapshot equivalence is tested. These are
machine-specific CPU timings, not browser FPS or full-brain acceleration.
The live browser retained all 91 received-neuron rows and six role rows through
ten updates, with search focus preserved; previously all were rebuilt. See the
[performance report](neural-performance-2026-09-13.md).

## Historical resistance-lane baseline

Before articulated equipment, fresh memory, seed 7, three flies, 600 ticks at dt=0.1:

| Learning | Sets by fly | Gym association by fly | Integration after loading |
| --- | --- | --- | --- |
| on | 21, 6, 4 | 0.041787, 0.017176, 0.010599 | 0.5637 s |
| off | 21, 6, 4 | 0, 0, 0 | 0.5525 s |

Peak fatigue was about 0.563; final fitness was 1.105, 1.03 and 1.02.
The ten-fly, 100-tick smoke completed in 0.3395 s after loading, with set counts
`[2,3,3,1,1,2,2,2,1,1]`. These are machine-specific measurements.
The baseline establishes acquisition, not improved set counts or addiction.
Full equations, per-fly work/distance and reproduction commands are in
[gym science](science/gym.md).

## Verification from the preceding gym milestone

The final integration passed 102 Python tests in 92.623 seconds, including official circuit
regeneration, work-boundary cases, independent state and persistence,
learning-disabled runs, deterministic population/disconnect races and full-mode
telemetry capacity. The frontend passed 32 Bun tests (113 assertions), strict TypeScript checking
and the Vite production build. `make data-status` validates both experiments'
edges against all 151,856,684 official weight rows.

Real-browser gym checks passed on the actual local Python server: 1-10-1 count
changes while paused, selected-fly IDs/labels/exact activity matching WebSocket
frames, visible anatomical activity pixels, camera-only commands, paused reload,
320/390px layouts and independent model/anatomy failure with live instruments.
Browser scripts and maintenance details are in [the observatory guide](frontend-observatory.md).
The final full-connectome browser run also passed overview/follow/eye, exact
received readings, search, pause/reload, mobile layouts, missing-model fallback
and real graphics-context loss during and after loading. Both final browser
runs reported no console errors. Experiment 1 compact was separately verified.
Its final layout regression also passed: hiding gym controls restores a
three-row chamber with a growing scene, rather than stretching the footer.
Anatomical screenshots wait for actual map readiness before capture.

The final UI review's two findings were resolved: connection status remains
visible on narrow screens, and invalid counts receive Persian messages even
in an English-locale browser. Invalid requests send no command; valid input
recovers. No detector suppression was added. The semantic atlas legend color
is intentional; the graphics chunk warning remains visible.
Final code review closed the population race, telemetry overflow, disconnect
handling and point-cloud cleanup findings. No unresolved review finding remains.
The design skill preserved the existing laboratory identity and recorded the
built gym/anatomy layout in `DESIGN.md` and its design sidecars.

WebGL2 rendering is verified. Native WebGPU is enabled but this environment has
no exposed `/dev/dri` devices; independent adapter/device probes failed. Native
GPU correctness and speed claims require a supported browser/device. The shared
lazy graphics chunk is about 845 KB raw/229 KB gzip; Vite's 600 KB warning remains
unsuppressed. No new runtime dependency was added.

## Preserved full-connectome backend

Experiment 1 can update all 166,606 valid MaleCNS bodies (206 isolated) and
25,574,615 valid neuron-to-neuron edges. The existing artifact is 198.3 MiB.
Earlier 2026-09-13 CPU measurements were 0.0679 s load and 14.596 ms per neural
substep; these are historical, machine-specific results, not this gym's speed.
The full runtime retains bounded observer telemetry while updating all bodies.
Final compatibility testing exposed an older intermittent overflow: the union
of interface bodies and top-64 activity could exceed the browser's 128-record
contract. Snapshot selection now reserves all 70 configured interface bodies
and fills at most 58 remaining slots; neural computation is unchanged.

Whole-graph normalization currently produces motor output around `10^-6`, so
the full backend needs an explicit calibration study before meaningful gym
movement or ten-fly real-time promises. Gym full mode is deliberately rejected,
not silently replaced with compact. This integration does not alter full-graph
artifacts or neural dynamics.

## Known limitations

- No evidence of consciousness, feelings, pleasure or addiction. Activity is a
  rate proxy, not measured voltage or spikes; reward is a bounded model signal.
- No demonstrated learned exercise preference or set-count advantage. The initial
  lane exposure is controlled setup; longer balanced learning ablations are next.
- Ground physics only: no airborne flight, climbing or inter-fly collision.
  Eye view is an approximate perspective camera, not biological compound vision.
- Anatomy is measured soma location only, not complete morphology/connectivity;
  most atlas points have no transmitted activity in compact mode.
- Separate memory files save atomically individually, not as a cross-file
  transaction. Actual flight, aversive learning and poker remain future work.
