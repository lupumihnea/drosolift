# Compact gym checkpoint contract

`experiments.session_checkpoint.snapshot(sim) -> dict[str, object]` produces
format `drosolift-session-checkpoint`, version `1`.
`restore(sim, document) -> None` accepts a fresh compact `GymSimulation` composed
with the same validated immutable circuits. `CheckpointValidationError` rejects
invalid or incompatible documents before any mutation. No file or database I/O
occurs in these functions, and neither function imports serialized code.

The envelope has `format`, `version`, `metadata`, and `state`. Metadata records
the dataset and official weights SHA256, canonical runtime/food/gym circuit
SHA256s, the relevant implementation-source SHA256, and the immutable simulation
configuration SHA256. Runtime circuits are read without copying their read-only
mapping proxies. Shared circuits are fingerprinted once per distinct object in
each call; changes to numerical configuration are still checked on every call.

Saved state includes the model clock, seed, population/pending population,
environment food, food scheduler timer and full MT state (including cached
Gaussian); every active/inactive fly's body, hunger, fitness/fatigue, work,
distance, rep/set progress, joint position/velocity and support pose; recurrent
network rates; both learners' bounded synaptic memories, eligibility and active
KC count; learning flag; feedback profile and latched readings; trail and latest
exact numerical observation. Apparatus loads, exclusive occupants, pending
load/exercise command IDs and unapplied event queues are retained. A queued setup
for a removed individual remains queued until that individual is reactivated,
matching the existing simulation. Dictionary iteration order is preserved using
ordered ID/value pairs where it can affect floating-point accumulation.

Validation rejects unknown fields, duplicate/reordered official rate IDs,
incorrect labels/roles, unknown or duplicate plastic edges, conflicting grips,
unknown profiles, booleans as numbers, nonfinite/out-of-range values and invalid
MT state. Arrays, depth, strings and the full JSON document are bounded (8 MiB,
250,000 tree nodes, depth 24; the supported bank is at most ten flies). Rates,
eligibility and multipliers remain within 0–1, apparatus loads 0.1–3, fitness
0–1.5, cumulative work/time within 10^12 and counters within JSON's exact integer
range. Fixed geometry, sensor/readout/learning parameters, network leak and food
spawn configuration must match the supplied model. The implementation hash is a
compatibility gate, not authentication; storage access and session identity are
the gateway's responsibility.

The gateway must snapshot after a complete authoritative boundary and commit
the opaque JSON and durable command journal in one SQLite transaction before
broadcasting its acknowledgement/frame. It restores the simulation before
constructing/restoring server observer state. Run UUID, running/paused flag,
source/run metadata and command journal are deliberately outside this model
checkpoint. The ordinary memory-only gym workflow remains available.

Focused verification:

```powershell
.venv\Scripts\python.exe -m unittest tests.experiments.test_session_checkpoint
```

Six tests passed in 11.557 seconds on the implementation workstation. The tests
compare subsequent frames exactly, including 400 mixed-timestep boundaries after
a bench/curl checkpoint with pending load/exercise commands, real set rewards,
learning and random food. They also cover no-learning/default-feedback runs,
inactive bank restoration, queued population/setup changes, Gaussian RNG cache,
source/config mismatch and eleven malformed-state variants with atomic rejection.
A 121,345-byte one-active-fly checkpoint measured 16.13 ms mean serialization
over ten warm calls on this workstation; this includes all ten saved bank members.
That is a local measurement, not a concurrent-session throughput guarantee.
