# Source publication

Work in progress, 5 November 2026. The user requested a GitHub repository and
explicitly declined deployment/hosting. The repository will contain instructions
for visitors to run it themselves; no hosted backend is required to inspect code
or play the bundled recorded sample.

## Source and rights

The implementation checkout retains the complete audited upstream Git history,
based on `2c5a03aa90f01048f011e13546b4d7fffc693945` and its license/notices.
That history contains `walking-fly.glb`, whose permission does not establish
public redistribution rights. Publishing that history would redistribute it even
if a later commit deleted the file. Therefore the public repository starts with a
clean source snapshot, retaining attribution and a versioned lineage record. The
local original history is preserved, not rewritten. The modern application uses
original Apache-2.0 procedural geometry. The independently licensed CT surface and
official anatomical data retain their own attribution.

The exporter inventories Git-tracked and nonignored source files, excludes
runtime/raw data, local tools, environments, private databases, the legacy GLB and
legacy renders, and generates a checksum manifest. It refuses an existing output
directory. Screenshots of the modern procedural fly and its actual recorded demo
are eligible; historical baseline screenshots of the legacy rig are omitted.

## Release gates

- Isolated opaque cookie profiles with exact-Origin checks and bounded active
  sessions; no session tokens in URLs or public telemetry.
- Versioned full-state SQLite checkpoints, validated before restore, with
  no simulation while disconnected; durable duplicate-command journal.
- Separate `build:public` frontend for session bootstrap; legacy live and recorded
  entry points remain available.
- Pinned Python production dependencies, frozen Bun lockfile, CI, Docker and
  local instructions. Deployment remains an optional task for repository users.
- Focused and full tests, checksum validation, browser evidence for isolation,
  controls, saved progress/restart, fallback and clean-source build.

## Measured verification

- Complete Python discovery: **209 passed**, no skips, **341.248 s**. This includes
  six full-state checkpoint tests, six source-export tests, gateway isolation,
  SQLite rollback/failure, pending/applied retry and all upstream regressions.
- Frontend: **67 passed**, **1,632 assertions**. Strict TypeScript and the legacy,
  public-session and recorded production builds passed. The existing Three.js
  neural chunk exceeds Vite's 600 kB advisory; the build succeeds.
- Independent public-source review: the **454-file** snapshot's hashes matched
  after a fresh Git clone, without the legacy GLB. Frozen Bun installation
  installed **29 packages / 21.89 s**; its **67 frontend tests / 1,632 assertions**
  passed in **4.14 s**. Public/replay builds succeeded. This review snapshot
  contains the final product behavior; subsequent changes are export tooling,
  repository attributes and release documentation. Final source inventory and
  exact hashes are supplied by root `PUBLIC_SOURCE_MANIFEST.json` and
  `UPSTREAM_LINEAGE.json` in the public repository.
- Official `data-status`: all source hashes, **151,856,684** connection rows,
  compact runtime **66/92** and learning **104/104** edges validated. Brain/world
  import boundary and `git diff --check` passed.
- Fresh Python virtual environment: the 16 pinned production dependencies
  installed, `pip check` found no broken requirements, and the public CLI loaded.
- Real Chrome **157.0.8103.15 / GTX 1060 / WebGL2** acceptance exited successfully:
  profile A froze at step **48** while B advanced **2→24**; weight **0.6→0.8**
  retained pending geometry and applied at step **66**; New fly created a second
  individual. Reload preserved the exact frame. After abrupt process-tree
  termination, both paused profiles restored their exact frames/run IDs at steps
  **67/202**. Retrying the old load returned its original effective step; changed
  payload was rejected. All five credentialed bootstraps succeeded, with no page,
  console or request errors, external requests or credentials in URLs.
  [Compact result](evidence/publication/public-browser-checks.json),
  [workout](evidence/publication/public-workout-1280x720.png),
  [selected neuron](evidence/publication/public-selected-neuron-1920x1080.png),
  [X-ray](evidence/publication/public-neural-xray-1920x1080.png),
  [390 px layout](evidence/publication/public-mobile-390x844.png).
- The newly built recorded package passed real Chrome/WebGPU checks for bench
  and curl at both `/` and `/demo/`: exact seek, neuron values, repetition counts,
  latched inputs and exports; zero WebSockets, external requests or page errors.
  Package: **15,143,226 bytes**, SHA256
  `e6ab5aad137a5e24c0efaebd51df89d3035bf6b4261182870d2ca292e26269f4`.
- Compose configuration validated. Docker image build remains unexecuted locally:
  this workstation has no running Docker daemon. A CI container build is configured.

Commands and logs are under [evidence/publication](evidence/publication).
The actual source export and browser checks also retain their own compact JSON
results. The local publication gates are complete. The GitHub target is
[lupumihnea/drosolift](https://github.com/lupumihnea/drosolift); CI is configured
for a future Linux run, which is distinct from the measured Windows checks above.

## Practical limits

This is an inspectable computational demo with authored gym mechanics and
illustrative within-body neural placement. It does not model biological exercise
specialization or spike events. The gateway supports device cookie profiles,
one SQLite worker and explicit resource quotas; it is not an account/recovery
service. Clearing the cookie loses access to that profile. Deployment and a
multi-user capacity benchmark have not been performed. Future self-hosters must
provide TLS and a persistent volume as documented in [SELF_HOST.md](SELF_HOST.md).

The original running local gym and prior conference archives remain preserved.
The new saved-profile preview uses a separate port and database.

## First Linux CI and numerical portability

The [first GitHub run](https://github.com/lupumihnea/drosolift/actions/runs/41946876964)
passed the frontend, all three web builds, Docker runtime-image build, official
download and data validation. Its 209-test Python run found one strict fixture
comparison failure: Windows-recorded continuous motor values differed from Linux
by about 4.4e-16. Browser acceptance was skipped after that failed prerequisite.
The original failing result is preserved in
[github-first-run.json](evidence/publication/github-first-run.json).

The fixture comparison now allows absolute/relative tolerance 1e-12 solely for
finite continuous neural, motor, body and related model measurements. JSON types,
identities, keys, ordered shapes, discrete counters and authoritative clocks
remain exact. Same-platform seeded-run equality and exact recording roundtrip
checks remain. Five comparator regressions reject changed IDs/types/counters,
clocks, schema, topology, nonfinite or materially different values, while allowing
one-ULP platform rounding. The focused recording module passes **10 tests / 25.439 s**
on Windows. Recordings, telemetry and model calculations are unchanged.
The [second CI run](https://github.com/lupumihnea/drosolift/actions/runs/41948230715)
passed **214 Python tests / 139.921 s**, all builds and data validation. Its browser
step timed out performing a pause click while both independent profiles rendered
full 3D: A became ready in 22 seconds; B readiness/isolation took another 142
seconds. This is consistent with graphics contention on the shared runner.
[The original second-run result](evidence/publication/github-second-run.json)
is preserved.

The browser check now keeps A in real WebGL2 for every workout/X-ray/inspection
capture, and explicitly exercises B with 3D unavailable. B must retain enabled
HTML controls, all **91 exact received readings**, selected body10783, and its 2D
rate history before and after restart. Both private model sessions, their clocks,
weight acknowledgement, exact restored frames and retry conflict checks remain.
The updated Windows audience flow passes with A/B restored at steps **66/135**;
only four expected B initialization diagnostics are classified, with zero
unexpected console/page/request errors. See
[the new result](evidence/publication/numerical-fallback/public-browser-checks.json).
The earlier two-full-3D native captures/result remain unchanged. The complete
Linux browser flow is rerun automatically after this harness adjustment.
