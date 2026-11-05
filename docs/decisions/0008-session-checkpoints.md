# Decision 0008: bounded JSON session checkpoints

Date: 2026-11-05
Status: Implemented for the optional isolated-session gateway

The ordinary gym saves learned synaptic multipliers but starts a new physical
run. A self-hosted shared browser application additionally needs each visitor's
paused or disconnected run to continue after a process restart, including an
in-flight repetition and an acknowledged command awaiting its physical boundary.

`experiments/session_checkpoint.py` composes brain and world state without adding
storage to either domain. `snapshot(simulation)` returns detached JSON primitives;
`restore(simulation, document)` restores into a newly composed compact gym with
already validated shared circuits. The gateway owns SQLite transactions, opaque
visitor identity, run identity, running/paused state and the durable command
journal. Model checkpoint and journal must commit at the same completed boundary.

The versioned document binds the dataset, official weights checksum, exact
runtime and both learning circuits, implementation source hash, and immutable
dynamics/configuration hash. It preserves all ten individuals, including inactive
ones, recurrent rates, eligibility, learned memory, physiology, work/counters,
body/apparatus state, pending setup commands and event queues, latest observations,
food and Python MT random-generator state. Profile and learning-enabled flags are
explicit saved state. It contains no pickle, object import paths or executable
payload, and loading requires no source-archive hydration.

Restore checks JSON shape, bounds, finiteness, official IDs/edges, labels, grip
occupancy and model compatibility before assigning any state. Rejection leaves
the supplied simulation unchanged. This deliberately rejects incompatible model
releases instead of silently resetting progress; migrations require a separate
explicit versioned design. Existing CLI/live/replay entry points are unchanged.

Verification compares exact subsequent frames, feedback, applied-command events,
reward/memory and RNG-driven food across both exercises, pending changes,
inactive/reactivated flies and no-learning runs. Public gateway tests additionally
exercise durable server/journal restoration; those are separate from this model
serialization contract.
