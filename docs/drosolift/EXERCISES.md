# Bench/curl setup and neural feedback

The one-fly demo can switch between the existing bench press and dumbbell curl.
This is explicit experimental apparatus setup, not a learned exercise choice or
navigation policy. Python retains the same neural network, memory, hunger,
fatigue and lifetime work/repetition/set counters throughout the change.

## Live command

Connect to the existing opt-in `/ws?controls=1` endpoint and send:

```json
{"type":"set_exercise","command_id":"exercise:1","fly_id":"fly-1","kind":"bicep_curl"}
```

`kind` is exactly `bench_press` or `bicep_curl`; `fly_id` must identify an active
fly. The same bounded command-ID/retry rules apply. A requested kind reserves
the first free matching station in the authoritative equipment list. Other
grips cannot steal that reservation. If every matching station is occupied or
reserved, the server returns `exercise_unavailable`. One pending change is
allowed per fly. Selecting the already active kind is an acknowledged no-op.

A moving joint first reaches its bottom stop with zero velocity. A complete
return counts normally; a partial return never creates a completed repetition.
At that safe boundary, setup places the fly at the destination station's actual
position, heading and support pose, then gives two seconds of attached recovery.
Setup itself adds no locomotor distance, lifting work, repetition or reward.
Already completed repetitions within the current set carry over. While paused,
mid-stroke changes remain pending; an already resting setup can apply at the
current simulation step. A removed inactive identity retains its queued setup
until re-added. No observer animation supplies the placement or lifting motion.

`command_ack.command` adds `set_exercise`; pending/applied status, run identity
and effective simulation-step semantics are unchanged. `control_state.exercises`
contains one row per active fly:

```json
{"fly_id":"fly-1","kind":"bench_press","station_id":"station-1","pending_kind":"bicep_curl","pending_station_id":"station-2","pending_command_id":"exercise:1"}
```

An immediate request can also release an older pending change for another fly
or station at the same resting boundary. Every applied command receives its own
acknowledgement once; collecting the current response must not discard earlier
applied responses. Two real-model regressions cover this boundary for both
exercise setup and load changes.

## Optional synthetic apparatus vision

Launch the new demonstration with:

```powershell
.venv/Scripts/python.exe -u -B main.py gym-web --flies 1 --seed 7 --feedback apparatus-visual-v1 --memory-dir data/runs/demo-v2/live-memory --port 8000
```

The `none` profile remains the default for all entry points. The optional
`apparatus-visual-v1` profile supplies explicitly engineered physical indicator
lights through the existing compact visual input channels. All twelve selected
visual input bodies are official L2 neurons. These are visual channels, gym-cue
paths and descending motor roles, not biological bench/curl-specialized regions.
The profile, calibration and limits are documented in
[the scientific methods](../science/apparatus-visual-v1.md) and
`data/circuits/apparatus-visual-v1.json`.

`control_state.feedback` holds `{fly_id, profile, indicator_left,
indicator_right, sample_step, sample_elapsed}`. Left and right mean the fly's
visual channels; camera orbit does not exchange the inputs. The values are
latched before the neural update and are the actual synthetic input used at
that step. They are not recomputed from the post-integration joint. Pause holds
the sample, including during a paused setup; the next model step samples the
new station. The existing food vision can dominate the corresponding lamp.

The neural network, official edges and motor readout remain unchanged. Rates
must be displayed from received official identity/value pairs. The display must
not paint regions by exercise name or animate a spike that the model did not
produce.

## Recorded demonstrations

The recording schema remains version 1 with unchanged schema-3 frames. Optional
metadata adds `exercise`, `feedback_profile`, the feedback manifest and
`control_history`, whose control states align exactly with the frames. The two
new 20-second samples can be regenerated with:

```powershell
.venv/Scripts/python.exe -m experiments.record_gym --output frontend/web/public/samples/demo-bench --seconds 20 --dt .1 --load .6 --seed 7 --no-learning --exercise bench_press --feedback apparatus-visual-v1
.venv/Scripts/python.exe -m experiments.record_gym --output frontend/web/public/samples/demo-curl --seconds 20 --dt .1 --load .4 --seed 7 --no-learning --exercise bicep_curl --feedback apparatus-visual-v1
```

Each sample has 201 actual frames and all 91 official compact IDs per frame.
Bench completes five repetitions with 2.2240732133714043 positive-work units;
curl completes six with 1.3200000000000007. Positive work includes actual partial
upward travel; only full upper-stop/bottom returns count as repetitions.

Across both samples, all twelve L2 readings match the corresponding actual
received visual input at every frame: zero mismatches. Bench left/right group
means range 0.0665–0.539916 and 0.016625–0.134979; curl ranges
0.01575–0.1325 and 0.063–0.53. These demonstrate the engineered light/input
relationship under the stated different tasks and loads, not biological
specialization or an isolated biological effect. Exact IDs, hashes and results
are in [exercise-feedback.json](evidence/exercise-feedback.json).

The original `samples/bench.json` remains untouched (SHA-256
`ad29f1343ab5ad712c538653c3d14a336f5cd295224f61c7418981b82e1fe150`). A regression
reproduces all its original frames exactly with profile `none`. The existing
fixed-budget conference comparison continues to use that original profile and
calibration; the new interactive demo is a separately identified model setup.

## Checks

New world and protocol tests were observed failing before implementation, then
passed. Focused regressions cover safe setup, occupied/reserved stations,
unchanged counters/work, incomplete strokes, real L2 inputs, actual q/load
dependence, recovery, disabled feedback, last-input latching, pause, retries,
reconnect and exact original-recording equivalence. Final complete-suite results
are recorded in `evidence/python-exercise-checks.log`; browser acceptance is
recorded separately in the implementation plan.

The final complete Python suite passed **171 tests in 155.580 seconds**, including
the acknowledgement boundary regressions and portable two-scenario verifier.
The earlier source-selector run passed 166 tests in 134.602 seconds and is
preserved in `evidence/python-exercise-first-full.log`. The official generated runtime
and learning JSON remain exactly equal to their committed versions. Both direct
brain/world import searches and `git diff --check` passed. The separate source
status command is recorded in `evidence/data-status-exercises.log`.
