# DrosoLift controls and recording, version 1

The follow-up [exercise extension](EXERCISES.md) adds explicit `set_exercise`,
optional per-fly `exercises`/`feedback` observations, a versioned synthetic
apparatus visual profile and two separately identified recorded samples. Legacy
frames, default profile `none` and the original bench calibration are preserved.
The opt-in [public session gateway](PUBLIC_SESSIONS.md) scopes these same messages
to an opaque browser cookie and restores its saved run across process restarts.

The audited schema-3 hello, nested schema-1 frames, running messages and
population command remain unchanged. The original strict clients continue to
work. New observers connect to `/ws?controls=1` to opt into two additional message
types. No extension messages are sent to ordinary `/ws` clients.

`control_state` contains `protocol: 1`, `run_id`, authoritative `step`, `elapsed`
and `loads`. Each load has `station_id`, `load`, nullable `pending_load` and
nullable `pending_command_id`. The run UUID identifies the model run, not a
biological specimen. Legacy `gym-web` creates a run per process; `public-web`
preserves each saved session's run UUID across restarts. Reconnect returns the current complete load state and
latest authoritative frame, including while paused.

The initial `control_state` also includes `metadata`: the explicitly supplied
seed (null if unspecified), timestep, upstream revision, source manifest, circuit
and implementation hashes, compact-model scope, initial frame and initial
food/gym memory snapshots. Reconnect returns the same run metadata. Ordinary
live states omit this larger object; clients retain the metadata from connection.

Send an absolute load with:

```json
{"type":"set_load","command_id":"load:1","station_id":"station-1","load":0.9}
```

Load is a finite number in 0.1..3.0 model force units. Booleans, strings, missing
values, nonfinite numbers, extra fields and unknown station IDs are rejected.
One requested change may be pending per station; a second request cannot
silently replace it. A load applies at the bottom with zero velocity before the
next upward physics substep, after a complete return. A load at an already racked
or unoccupied station may apply immediately without advancing model time.
Changing load never completes a repetition or supplies free work.

`command_ack` contains `command_id`, `command` (`set_load` or `set_running`),
`status` (`pending` or `applied`), `effective_step` (null until applied) and
`run_id`. The effective step is captured before network awaits. It identifies the
enclosing simulation tick, whose equipment substeps are at most 0.01 seconds.
Use `control_state` to show current and pending loads separately. A load waiting
mid-stroke while paused remains pending until the model resumes and returns.

`set_running` accepts an optional `command_id` for opted-in observers. Its
acknowledgement identifies the exact stopped/started model step. Repeating the
same ID and payload returns the saved acknowledgement without applying again.
Reusing an ID with different values returns `command_id_conflict`. A SQLite
journal now retains accepted identities independently of its bounded 128-entry
RAM cache. The explicit default quota is 100,000 IDs per session; further new
identified commands return `session_command_quota`, while old retries retain
their acknowledgements. Local `gym-web` uses an in-memory journal for its run;
`public-web` stores the journal and full model checkpoint in one durable
transaction before acknowledgement. Its 120-new-command/60-second session limit
returns `rate_limited`; exact retries are resolved before throttling.
Legacy unidentified
pause/resume commands remain absolute assignments. Population setup preserves
the upstream command contract.

When one immediate request releases older pending changes at the same resting
boundary, every newly applied command receives its own acknowledgement. The
current requester receives its response once; earlier applied changes are also
broadcast to opted-in observers. Two real-model regressions were observed
failing before this routing repair, then the 28 relevant protocol/world checks
passed in 24.589 seconds (`evidence/ack-boundary-checks.log`).

## Portable recording

From the repository root:

```powershell
.venv/Scripts/python.exe -m experiments.record_gym --output data/runs/bench --seconds 20 --dt .1 --load .6 --seed 7 --no-learning
```

This uses the ordinary `create_gym`/`GymSimulation.step` implementation with the
validated official runtime and fresh per-run memory. It never loads or resets
existing user memory. Output is JSON plus an adjacent CSV. The JSON format is
`drosolift-recording`, `version: 1`, with `metadata`, the normal schema-3 `hello`
and the complete ordered `frames` array. Frame zero is the actual initialized
model state; subsequent indices advance by the declared `dt`. Each frame retains
all simulated identity/activity pairs, schema versions, timestamps, equipment
position, velocities, repetitions and training counters.

Metadata records UUID, seed, timestep, duration, load, learning flag, source
manifest, source/circuit SHA-256 values, compact-model IDs, engineered mechanics,
activity units and initial state. All activity values are dimensionless rate-like
model values. There are no modeled spike events. CSV exports one row per exact
recorded sample, including elapsed time, joint state, repetitions and positive
load-lifting work; it is derived from the same in-memory recording.

The bundled `frontend/web/public/samples/bench.json` sample is generated by the
same command. Official IDs and source-derived circuit metadata retain the
upstream data attribution in `THIRD_PARTY_NOTICES.md`; the newly computed model
observations are project output under Apache-2.0. The authored visual body and
native anatomical atlas remain separate from these scalar mechanics.

## Verification

The new world regression was observed failing before implementation with
`AttributeError: EquipmentFloor.request_load`, then the equipment suite passed
12 tests. The recording tests were observed failing on missing
`experiments.record_gym` before implementation. Relevant commands:

```powershell
.venv/Scripts/python.exe -m unittest tests.world.test_equipment tests.frontend.test_gym_controls tests.frontend.test_gym_server tests.test_record_gym -v
```

Final integrated check on 4 November 2026: the complete Python discovery run
passed **143 tests in 201.746 seconds**; see `evidence/python-checks.log`.
`python -B main.py data-status` passed all pinned source checks and reported
151,856,684 connection rows, 66 foraging runtime edges, 92 gym runtime edges and
104 edges in each learning circuit; see `evidence/data-status.log`. Direct
`world -> brain` and `brain -> world` import searches returned no matches.

The bundled seed-7, load-0.6, learning-disabled sample has 201 frames over 20
simulation seconds, 91 official IDs per frame, five completed repetitions and
2.232383 positive-work units. JSON is 1,598,543 bytes and CSV is 25,613 bytes.
This document does not claim browser acceptance or complete P2/P3 acceptance
by itself.

## Source-validation memory bound

The unchanged upstream startup hydrated the complete official Feather edge table
and did not expose its HTTP endpoint after more than ten minutes on this test
host (baseline evidence records the resource limitation). The compact validator
now verifies the same SHA-256 before opening Feather V2 as Arrow record batches.
It retains only a batch plus the expected-edge set while checking exact
`(body_pre, body_post, weight)` membership. Count and row access retain their
semantics, and Feather V1 retains its legacy loader. The neural update loop,
selection, connectome and equipment integrator are unchanged by this memory fix.

A multibatch regression compares row/count/exact-edge results with a hydrated
fixture, rejects incorrect weights/endpoints/checksums and guards against full
table hydration. It was observed failing before the change, then all seven
data-access tests passed. The normal optimized server was observed ready at
about 227 MB working set. A separate startup timing is recorded in
`evidence/startup.json`; it is a warm source-cache measurement, not a cold-install
or renderer benchmark. The observed readiness time was 12.577 seconds, with
225,427,456 bytes working set and a 437,583,872-byte peak on
`DESKTOP-9CHQBV3`, Windows build 19045, Python 3.12.2. The probe was run as
`.venv/Scripts/python.exe scripts/check_drosolift_startup.py`; it uses a separate
port, fresh temporary memory and terminates only its own server process.
The follow-up exercise task also exposed the same hydration problem in the
separate offline circuit-reproduction scanner. `WeightScanner.select` now reuses
the bounded batches, while retaining an explicit full-table inspection property
for compatibility. Its multibatch test preserves exact filter results, source
order and duplicates; the official runtime and learning JSON were regenerated
identically. Those three tests passed in 91.026 seconds. No selection rule,
official edge or neural update changed.
