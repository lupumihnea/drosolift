# Reference neural view and training workflow — 5 November 2026

The user supplied a photographed neural-panel reference and twelve browser
annotations. The reference guides the frontal composition, blue anatomy,
cyan/yellow activity palette, history strip and readout hierarchy. The screenshot
is reference-only and is not redistributed as an app asset. Its FlyWire label,
neuron counts, scale and spike claims are not this model's data.

## Requested interface changes

Removed the visible connection/model header block, apparatus caption, pending
rack callout, Gym/Fly-eye buttons, footer, Replay navigation tab and apparatus
feedback strip. Connection/pending announcements remain available to assistive
technology; actionable connection failures and weight/setup errors appear beside
the controls. Exact data, provenance, exports and the full circuit remain behind
**Inspect neurons & data**, outside the normal workout composition.

The neural view uses measured MaleCNS coordinates, a frontal brain crop, blue
unobserved anatomy and actual received rates mapped from cyan to yellow. The
crop is a documented display cutoff in the source frame, not an official ROI
segmentation. Full CNS and circuit views remain in the disclosure. Cell colors
show stable model group colors as a separate display mode. The history strip
contains received rate samples with source times and official IDs; no spike
events are synthesized. Missing activity remains distinct from a received zero.
See [morphology and display provenance](MORPHOLOGY.md).

The X-ray shows actual compact neural observations within an authored body
scaffold and keeps the engineered motor route identifiable. Its placement is
illustrative and is not a measured atlas-to-body registration.

## Weight and individual training

**Add weight** and **Remove weight** change the selected apparatus by 0.2 virtual
load units within the existing 0.1–3.0 bounds. A moving joint finishes its return
before the applied weight changes. A queued change keeps the current geometry;
only the acknowledged applied load updates its visible plate stacks. Numerical
weight remains available without the renderer. These are model units, not kg.

The fly selector observes an existing individual. **New fly** activates the next
identity from the bounded ten-fly bank and requests an available apparatus of
the current exercise kind. Python retains exclusive grip reservation and safe
setup. An occupied original spawn cannot steal another fly's apparatus. All
active flies advance on the shared model clock, including those outside the
selected camera view.

Each identity has independent neural state, body, fatigue, training and separate
food/gym learning memories using the same pinned compact circuit. Selection does
not swap datasets or create a new neural model type. The UI exposes received
fitness, its gain above the initial 1.0, fatigue and the current three-rep set.
There is no button that awards training progress.

Existing model recurrence:

```text
one completed set = three full loaded upper-stop/bottom-return repetitions
fitness = min(1.5, fitness + 0.005 * newly_completed_sets)
fatigue = clamp(fatigue + 0.30 * positive_work - 0.025 * dt * (1 - effort), 0, 1)
actuator multiplier = min(1, (1 - 0.75 * fatigue) * fitness)
```

Conditioning preserves force under fatigue without exceeding the rested peak
force of six model units. Partial work does not earn fitness or a completed set.
Floating-point accumulation may display 1.500 before reaching the exact cap.
Pause freezes time and recovery; recovery happens while the simulation runs.
Fitness, fatigue, counters and neural state last for the current server run.
Only the existing per-fly food/gym edge memories persist across server restarts.
This revision changes no model, reward, physics, sensory profile or P4 calibration.

## Verification

The new browser flow was first run against the previous build and failed on the
removed header, confirming that it checks the actual app. Weight-step regressions
were observed failing before their module existed, then passed at finite bounds.
Actual plate, X-ray and rate-history regressions cover the corresponding modules.

```powershell
.tools\node_modules\bun\bin\bun.exe test --cwd frontend/web
.tools\node_modules\bun\bin\bun.exe --bun run --cwd frontend/web build
.tools\node_modules\bun\bin\bun.exe --bun run --cwd frontend/web build:replay
.venv\Scripts\python.exe -u -m scripts.check_training_ui
```

The complete Python suite passes **171 tests in 469.798 seconds**. Official data
status validates 151,856,684 source weight rows and all selected runtime/learning
edges. Direct brain/world import checks remain empty. Logs, audience screenshots,
new trainee progress and pending/applied plate measurements are retained under
`evidence/demo-v3/`. Final frontend/browser results and remaining gaps are recorded
in [the implementation plan](IMPLEMENTATION_PLAN.md).

Final results: **64 frontend tests / 1,615 assertions**, both builds, both native
graphics paths, the 91-reading fallback, 320/390 widths and five resource cycles
pass. Fly 03 earned its first set and moved 1.000→1.005 fitness from actual
completed repetitions. Applied bench and curl weights each add one disc per
stack at a 0.2 change; pending changes preserve geometry. The exact received
values, selected identities, control states and screenshots remain inspectable
in [browser-checks.json](evidence/demo-v3/browser-checks.json).
The [24.36-second live walkthrough](evidence/demo-v3/drosolift-training-demo.webm)
includes selection, added weight, X-ray and both exercise/neural modes.
