# Exercise and neural presentation upgrade — 4 November 2026

This revision responds to the request for a stronger neural demonstration and
access to the other exercise equipment. It preserves the audited upstream base,
the original `none` feedback behavior, the earlier recording and P4 comparison.

## What the audience can do

Bench press and Dumbbell curl are selectable in both the live workout and the
portable replay. In live mode, Python finishes the current return stroke,
reserves an available apparatus, attaches the fly in a two-second recovery and
acknowledges the effective step. Completed work, repetitions and sets remain
cumulative. A paused model keeps a pending switch without advancing its clock.
This is experimental apparatus setup, not learned walking or exercise selection.

The atlas remains prominent beside the workout, with eight licensed official
SWCs, measured soma positions, selected-neuron history and exact numerical
inspection. Anatomy preserves the source coordinate frame. Circuit lays out
the same compact cells and official edges by their model role; its layout is
explicitly authored. Selecting a group highlights its cells and measured means.
X-ray adds a separate labeled motor-command route through the fly's authored
rig; it is not a registered anatomical tract.

The gym uses rounded black pads, brushed steel hardware, beveled weights, a
ribbed graphite studio, soft lights and actual indicator lamps. The original
procedural fly has chitin segments, compound-eye facets, veined translucent
wings and six articulated legs. Front grips use the actual bar pose. Curl
support feet follow the inclined apparatus. The three reference PNGs were
opened before visual decisions and the real browser was inspected at 720p and
1080p. This remains a stylized authored rig rather than a scanned specimen.

## What the activity means

The optional `apparatus-visual-v1` profile supplies synthetic apparatus indicator
light values to the existing official bilateral L2 visual inputs **before** the
neural update. The bench's left indicator is stronger; the curl's right is
stronger. Joint travel and load change the indicator brightness. Existing food
vision combines by maximum, so it can also dominate a channel during a live run.
The numerical activity and all group means come from the resulting model state.
The camera and display do not inject neural values.

These are modeled visual responses to an engineered exercise cue. They are not
evidence for natural bench/curl specialization in fly brain regions. The six
display groups are circuit roles, not newly asserted anatomical regions. See
[the equations, exact IDs and version](../science/apparatus-visual-v1.md),
[exercise switching](EXERCISES.md) and [the wire protocol](PROTOCOL.md).

Activity is rate activity. No spike events or traveling action potentials are
invented. Brightness uses the documented bounded display calibration in
[morphology provenance](MORPHOLOGY.md); received zero and unobserved anatomy remain
distinct. Exact values remain available independently of the nonlinear color
mapping. The compact model still exposes 91 official IDs and 92 official edges;
the 139,659 soma backdrop does not imply whole-brain functional simulation.

## Reproduction and evidence

```powershell
.venv\Scripts\python.exe -u -B main.py gym-web --flies 1 --seed 7 --feedback apparatus-visual-v1 --memory-dir data/runs/demo-v2/live-memory
.tools\node_modules\bun\bin\bun.exe test --cwd frontend/web
.tools\node_modules\bun\bin\bun.exe --bun run --cwd frontend/web typecheck
.tools\node_modules\bun\bin\bun.exe --bun run --cwd frontend/web build
.tools\node_modules\bun\bin\bun.exe --bun run --cwd frontend/web build:replay
.venv\Scripts\python.exe -m scripts.check_demo_upgrade
.venv\Scripts\python.exe -m scripts.check_demo_presentation
```

The recorded bench and curl scenarios each contain 201 exact frames over 20
model seconds, with a matching control state at every frame. Bench at load 0.6
completes five repetitions and 2.2240732133714043 positive work; curl at load 0.4
completes six repetitions and 1.3200000000000007 positive work. All twelve L2
values match the applied visual input in every recorded frame (zero mismatches).
[Scenario measurements](evidence/exercise-feedback.json) retain exact extrema,
hashes, commands and the preservation check for the earlier baseline.

The final full Python suite passed **171 tests in 155.580 seconds**. The regression
also reproduces every earlier baseline frame with feedback `none`. A bounded
Arrow weight scan replaces the previous full-table hydration without changing
the generated official circuit. The scan has a multi-batch equality regression.
Two real-model regressions also cover acknowledgement delivery when another
pending apparatus/load becomes ready during an immediate command handler.
[Python check log](evidence/python-exercise-checks.log) retains full output.

[Browser acceptance](evidence/demo-v2/browser-checks.json) records exact selected
values and group means, pending/retried exercise changes, pause invariance,
full curl return, cumulative totals, controls on entering replay, recorded
seeking/export and zero replay WebSockets. [Presentation checks](evidence/demo-v2/presentation-checks.json)
record both renderer paths, responsive widths, numerical fallback, repeated
mode-switch resource counts and an actual application recording.

The final frontend counts, renderer measurements, screenshots and package
verification are recorded in the [implementation plan](IMPLEMENTATION_PLAN.md).
The frontend passes 57 tests / 1,556 expectations, and both production builds
pass. Native render-loop cadence is 143.59 callbacks/s at 1280×720; this is not
a GPU completion measurement. The inspected actual-browser walkthrough is
[24 seconds long](evidence/demo-v2/drosolift-demo-v2.webm), with both exercises
and neural/circuit selection. WebGPU, WebGL2, 320/390 layouts, five resource
switching cycles and the 91-reading numerical fallback pass.
The conference package preserves all licenses and the original package remains
untouched. No raw source archives, neural-backend dependencies or upstream GLBs
are required by the portable replay.

## Remaining limits

Only the two implemented upstream apparatus kinds are offered; additional
exercise physics would require a separate model. The setup transition snaps
the authored fly to the authoritative reserved apparatus after a safe boundary.
Morphologies cover eight selected cells, not all compact cells. Atlas chords
show connectivity between measured positions rather than reconstructed synaptic
paths. Body motor routing is authored and unregistered. The original comparison
does not evaluate the new optional sensory profile. Biological validation,
photographic anatomy and a user-provided human workout video remain outside
this demo's evidence.
