# Independent public sessions

`public-web` is a separate, opt-in entrypoint. It does not change the shared
conference `gym-web` run or the portable recorded demo. No hosting service is
created by this implementation.

## Local start

Build the public frontend with `bun --bun run build:public` in `frontend/web`, install the documented Python requirements, and
download and validate the pinned official MaleCNS sources first. Then run:

```powershell
.venv/Scripts/python.exe -B main.py public-web --session-db data/runs/public/sessions.sqlite3 --allow-origin http://127.0.0.1:8003 --insecure-local-cookie
```

Open `http://127.0.0.1:8003`. The public frontend bootstraps a session before
opening its model socket. The insecure cookie option is restricted to loopback
development. For HTTPS use the default Secure cookie and an exact production
origin, for example `--allow-origin https://gym.example.org`. Configure the bind
address and port explicitly when a container or reverse proxy needs them.

`--session-db` is required. On a hosted machine, point it at a persistent volume,
including its SQLite WAL/SHM sidecar files, rather than an ephemeral application
directory. The default frontend directory is `frontend/web/dist-public`;
`--dist-path` can select a different public build. Use **one gateway worker** per database. This implementation does not
coordinate in-memory simulations across multiple gateway processes or machines.

## Browser protocol

The client makes `POST /api/session` with browser credentials included. The
server accepts only an exact configured `Origin`; repeat `--allow-origin` for
additional origins. Credentialed CORS and preflight responses return that exact
origin, never `*`. Missing and unconfigured origins are rejected for bootstrap
and WebSockets.

The response sets a host-only `drosolift_session` cookie with `HttpOnly`,
`SameSite=Lax`, `Path=/`, a default 30-day lifetime, and `Secure` outside explicit
loopback development. The JSON response contains `run_id`, `resumed`,
`websocket: "/ws"`, `expires_in`, and `max_flies: 10`; it contains no bearer
credential. The cookie is a random 256-bit opaque value. Only its SHA-256 digest
is stored in SQLite. Session identifiers supplied through URL parameters are
rejected. Cookie possession resumes this browser's anonymous profile; this is
not an account system, and deleting the cookie loses access to that profile.

Connect to `/ws?controls=1` with the same cookie and an allowed browser origin.
The ordinary gym telemetry and acknowledged commands are unchanged. Both
simultaneous tabs for one cookie observe and control the same profile. Separate
cookie jars receive independent simulations, ten-fly banks, equipment, memories,
clocks, command journals, and run IDs.

For a frontend hosted separately, configure its backend URL and credentialed
requests. Use same-site custom frontend/API domains or a same-origin WebSocket
proxy: the `SameSite=Lax` cookie does not promise to work as a third-party cookie
between unrelated hosting domains. A reverse proxy must support WebSocket
upgrade. Allowed origins are configured explicitly; forwarded host headers do
not decide who can control a session.

## Saved state and clock

The validated compact circuit is loaded once at process startup. Each visitor
receives fresh mutable model objects using that immutable source-validated
circuit. There is no per-visitor download, alternate neuron model, training
boost, or changed force mapping.

Full checkpoints include the model clock; every fly's actual neural, body,
physiology, fitness, exercise, and learning state; food generator RNG; equipment
loads, occupancy, pending changes and reservations; plus the observer run ID,
run metadata, and running flag. Versioned checkpoints validate their source and
model configuration before restoration. Corrupt or incompatible records fail
with HTTP 503 and retain the original record instead of silently creating a
replacement profile.

Command identities and acknowledgements are stored in the same SQLite database.
The full state checkpoint and command result join one transaction at the actual
model/control boundary before an applied acknowledgement is sent. A retry after
restart therefore uses the original run and effective step. Checkpoint JSON is
bounded, finite, and SHA-256 checked. SQLite uses WAL and synchronous FULL commits.

The last socket disconnect freezes the simulation and saves its state. No model
time, work, fitness, or rewards accrue while the visitor is disconnected. On
reconnection, a running session resumes from its saved model step; a paused
session remains paused. Graceful shutdown checkpoints sessions. An abrupt process
termination restores the last committed boundary, without fabricating elapsed
offline training.

## Resource bounds

Defaults are four active session instances, two sockets per session, 256 saved
profiles, 30-day cookie/session retention, and idle instance eviction after 300
seconds. Use `--max-active`, `--max-clients`, `--max-profiles`, `--cookie-days`,
and `--idle-seconds` to change these bounded limits. Active and socket limits
are capped at 64 and eight; saved profiles are capped at 10,000. Each profile
still has the existing one-to-ten active fly limit. Simulation FPS is bounded
to 1–30 in this public entrypoint.

When all active slots have connected clients, new activation returns 503 with
Retry-After. A disconnected instance can be checkpointed and evicted to make
room; its saved profile remains available. A third simultaneous socket returns
429 under the default limit. A full durable profile quota refuses new profiles
without evicting unexpired profiles. Expiry reclaims the profile and its command
journal together. Full records are bounded to 4 MB each.

The public command limiter accepts up to 120 new commands per 60 seconds per
session; exact retries retain their original acknowledgement. Durable journals
retain up to 100,000 command identities per session. This explicit quota replaces
the old 1,024-command process-wide cache without forgetting accepted IDs.

## Verification

The gateway tests use the actual compact gym and separate browser cookie jars.
They cover isolation, exact paused restart and retry, origin/cookie rejection,
active/socket quotas, disconnected clock freeze, idle eviction, corrupt saved
records, and finite atomic SQLite storage. Run:

```powershell
.venv/Scripts/python.exe -B -m unittest tests.frontend.test_public_server tests.frontend.test_session_store tests.test_public_cli -v
```

The ordinary complete Python suite remains required. Browser acceptance should
also verify acknowledged load changes and earned training progress through a
gateway restart, using two independent browser contexts.

On 2026-11-05, the 17 gateway/store/CLI checks passed in 10.420 seconds
(`evidence/public-sessions/gateway-checks.log`). The final complete Python suite
passed all 209 tests in 341.248 seconds, including the six checkpoint and six
source-export tests (`evidence/publication/python-checks.log`). Official data
validation, direct domain import boundaries, and `git diff --check` also passed;
their logs are in `evidence/publication/`. Timings are observed on the review
machine under concurrent source validation, not performance guarantees.
