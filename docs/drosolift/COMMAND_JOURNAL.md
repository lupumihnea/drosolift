# Durable command identities

The previous process-local 1,024-entry command limit is replaced by a SQLite
journal in `frontend/command_journal.py`. A bounded 128-entry hot cache accelerates
retries; eviction removes only the cached copy. The durable identity is the
tuple `(session_id, run_id, command_id)`. An identical retry returns its saved
pending or applied acknowledgement. Reusing an identity for a different payload
is rejected. An applied acknowledgement and its original effective step are
immutable.

`GymObservatoryServer` completes each command and clock boundary synchronously
inside `CommandJournal.atomic()`. Its optional `on_boundary(server)` callback
writes the full model checkpoint through the same SQLite connection and
transaction. Network delivery happens after commit. Pending load and exercise
correlations are part of the model checkpoint; after restoration they can advance
to applied exactly once at their actual model step. A failed model/checkpoint
write rolls back the journal, sends no acknowledgement, and freezes that instance.
Its uncommitted in-memory state cannot overwrite the last durable checkpoint on
shutdown.

Public sessions use the gateway's persistent session database, WAL and
`synchronous=FULL`. Their run ID and initial run metadata survive process restart.
The ordinary local `gym-web` entrypoint uses an in-memory SQLite journal for its
current run unless a durable journal is supplied to the server. A local process
restart starts a new run; it does not claim durable profile restoration.

The default quota retains 100,000 identities per session across its runs. Reaching
it rejects new commands with `session_command_quota`, preserving all old retries.
The public server separately limits new commands to 120 per 60 seconds and returns
`rate_limited` when exceeded. Exact retries are looked up before either check.
Rows are bounded to 2,048 UTF-8 bytes each for payload and result. Whole expired
profiles and their journals are reclaimed together by the gateway. Live individual
command IDs are never silently deleted. One gateway worker owns each database;
multi-process simulation coordination is outside this implementation.

Focused verification:

```powershell
.venv/Scripts/python.exe -B -m unittest tests.frontend.test_command_journal tests.frontend.test_gym_command_durability -v
.venv/Scripts/python.exe -B -m unittest tests.frontend.test_gym_controls tests.frontend.test_gym_server -v
```

The first command passed 9 tests in 13.011 seconds on 5 November 2026: 1,100
acknowledged commands, actual hot-cache eviction and SQLite reopen, payload
conflicts, pending-to-applied load restoration, exact old effective steps,
separate quota/rate errors, external-transaction rollback, and checkpoint failure
without acknowledgement or a failed-state shutdown save. The existing protocol
checks passed 13 tests in 22.259 seconds. Gateway tests and real-browser evidence
are recorded alongside the public-session acceptance results in
`docs/drosolift/evidence/publication/`.

Run the portable audience check after building `dist-public` and installing
Playwright Chromium:

```powershell
python -B -m scripts.check_public_sessions
```

It owns only its temporary database and port 8004, checks two independent browser
contexts, and abruptly restarts its own subprocess. It never stops an existing
server. The result JSON records exact-frame hashes, original command responses,
cookie attributes without cookie values, screenshots, and browser errors.

The actual Windows browser pass used:

```powershell
[Local filesystem path omitted from this publication copy.]
```

Chrome 157.0.8103.15 rendered WebGL2 on the NVIDIA GTX 1060. Browser A stayed
exactly frozen at step 48 while independent browser B advanced from step 2 to
24. A's weight changed from 0.6 to 0.8 at effective step 66, after its pending
state preserved the previous plates; A activated a second fly without changing
B. Reload preserved A's exact paused frame. Abrupt process restart restored the
exact complete paused frames at A step 67 and B step 202, with both original run
IDs. Retrying A's old load returned effective step 66 without reapplying it;
changing that identity's payload was rejected. All five credentialed bootstrap
requests returned HTTP 200. There were no page errors, console errors, failed
requests, external requests, or session credentials in URLs. Both cookies were
HttpOnly and SameSite=Lax; Secure was intentionally disabled only for this
loopback check.

The clean-exit result is
[public-browser-checks.json](evidence/publication/public-browser-checks.json).
Reviewed captures include the
[1280 × 720 workout](evidence/publication/public-workout-1280x720.png),
[exact neuron inspection](evidence/publication/public-selected-neuron-1920x1080.png),
[1920 × 1080 neural X-ray](evidence/publication/public-neural-xray-1920x1080.png),
and [390 × 844 mobile view](evidence/publication/public-mobile-390x844.png).
The browser harness's owned test server and temporary database were removed;
the existing demo and public preview servers were left running.
