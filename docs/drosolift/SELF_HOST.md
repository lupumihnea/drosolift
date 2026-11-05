# Run your own copy

This repository does not require a hosted account or paid service. Nothing is
deployed automatically. Python 3.12 and Bun 1.4.4 are the tested tools. The live
model requires 1.109 GB of official source data; it is downloaded with pinned
SHA256 verification into ignored `data/raw/`. The recorded demo does not need it.

## Local saved gym

From the repository root, on Linux/macOS:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
bun install --cwd frontend/web --frozen-lockfile
bun --bun run --cwd frontend/web build:public
.venv/bin/python scripts/download_malecns.py
.venv/bin/python -B main.py public-web --session-db data/runs/public/sessions.sqlite3 --allow-origin http://127.0.0.1:8003 --insecure-local-cookie
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`.
If Bun is not on PATH, `npm install --prefix .tools bun@1.4.4` installs the pinned
tool locally; use `.tools\node_modules\bun\bin\bun.exe` in the Bun commands.

Open http://127.0.0.1:8003. Each browser cookie profile has an independent gym,
fitness, learning, counters and model clock. A reload/restart restores saved
progress. A closed gym does not train in the background. Two tabs with the same
cookie share the same profile. This is a device profile, not an account: clearing
cookies loses access, and copying a cookie grants access. The cookie expires in
30 days by default. Keep the SQLite database and its WAL files private and back
it up after a graceful server shutdown. No tokens are placed in URLs.

The old `main.py gym-web` is a local shared-session research entry point on port
8000; it does not save full training state across restarts. Use `public-web` for
isolated durable profiles. The original experiments and entry points remain.

See [PUBLIC_SESSIONS.md](PUBLIC_SESSIONS.md),
[SESSION_CHECKPOINTS.md](SESSION_CHECKPOINTS.md) and
[COMMAND_JOURNAL.md](COMMAND_JOURNAL.md) for limits and exact state/command semantics.

## Recorded sample only

```sh
bun --bun run --cwd frontend/web build:replay
python scripts/serve_replay.py
```

Open http://127.0.0.1:8010. The sample contains actual recorded model states;
replay controls do not train a live fly. The root `vercel.json` optionally builds
this static recorded version for someone who chooses to publish it. Set the
project Root Directory to this repository root. No backend URL, account secret
or automatic deploy workflow is included.

Vercel's optional Bun runtime selector accepts a managed `1.4.x` range rather
than an exact patch. Local builds and CI use Bun 1.4.4 with the frozen lockfile.
See the [official configuration reference](https://vercel.com/docs/project-configuration/vercel-json#bunversion).

## Optional container

Download the source data first with the command above, then:

```sh
docker build -t drosolift .
DROSOLIFT_ORIGIN=https://gym.example.org docker compose up
```

Configure your own TLS reverse proxy from that exact origin to localhost:8003,
including WebSocket upgrade support. `compose.yaml` binds the service to loopback,
uses a persistent named volume for sessions and a read-only raw-data mount. The
image runs as an unprivileged user; it does not download data or create hosting
resources at startup. Run exactly one gateway process per SQLite file. The default
four active gyms and two tabs/profile bound resource use; change limits only after
measuring your machine. Each accepted command and model tick checkpoints the state.

For an independently hosted frontend, build `build:public` with
`VITE_BACKEND_URL=https://api.example.org`, add the exact frontend origin via
`--allow-origin`, and serve both under the same HTTPS site (for example
`gym.example.org` and `api.example.org`). Cookies use SameSite=Lax; unrelated
domains such as a default vercel.app URL and a random backend host are unsupported.
A same-origin reverse proxy is the simplest arrangement. Remote HTTP and wildcard
origins are rejected; `--insecure-local-cookie` is restricted to loopback.

No container build or remote hosting result should be inferred from these
instructions; measured checks and environment gaps are recorded in [RELEASE.md](RELEASE.md).
