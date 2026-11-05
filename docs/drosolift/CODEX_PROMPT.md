# Build DrosoLift Observatory

You are implementing a reviewable local web application for a university student who studies computer science and movement science and helps run Power & Fit Student. The product is a visually impressive fruit-fly gym with an inspectable neural model.

Read IMPLEMENTATION_PLAN.md, SOURCES.md and the proposed AGENTS.md. Open all three images in references before changing visuals. They define the artistic target. Their anatomy, neural activity and human video are illustrative. Explain unavoidable deviations concretely.

## Ownership and starting point

Begin with the audited Apache-2.0 project https://github.com/tiredbooy/Fruit-Fly at commit 2c5a03aa90f01048f011e13546b4d7fffc693945. Prepare a separate local checkout on a working branch, preserve its history and notices, and retain applicable upstream instructions. Copy the handoff into docs/drosolift and adopt its project rules without discarding upstream requirements. Reconcile routine instruction differences within the user's authorized task.

Inspect and execute its normal entry points before redesigning. It already has a compact MaleCNS-derived neural circuit, a gym, articulated equipment, telemetry, TypeScript and Three.js. Preserve working model behavior and the existing commands and clients. Record the upstream revision and baseline checks. Use the package manager and lockfile already present.

The target stack follows the source: Python with aiohttp, TypeScript, Three.js and Vite. Preserve compatible WebGPU/WebGL2 rendering. Add a dependency only for a concrete missing capability.

Follow the asset decision in SOURCES.md. Produce a redistributable articulated fly with a documented source, six legs, red compound eyes, translucent wings and front-leg joints that can reach the bar. A buildable Blender script and licensed source meshes are acceptable. Keep asset creation reproducible and preserve required attribution.

## Product priorities

1. A compelling 3D fly performing a physically driven bench press.
2. A large inspectable neural view synchronized with the same simulation.
3. Pause, load adjustment, neuron selection and a recorded replay that really work.
4. A reproducible computational comparison that can support a conference presentation.

Implement one active fly and one usable bench first. Keep the existing gym population behavior compatible. Continue through milestones in order, stopping a session at a coherent runnable state when necessary. Resolve ordinary reversible decisions autonomously.

## Visual target

Match references/01-workout.png for the main composition. Use a dark graphite gym stage, brushed steel, textured black bench padding, soft overhead studio light, readable pale typography, restrained cyan neural glow and coral activity accents. The fly, bar and plates should have convincing scale, contact, surface detail and shadows. Reserve about 35–40% of the wide desktop screen for the neural view. Keep controls compact and legible.

Use real scene geometry for the fly and equipment, with a side three-quarter camera. Drive the bar from authoritative joint position, and front-leg IK from the bar's grip targets. Keep wings, legs and body recognizably insect-like. Tune scale, pose, lights and materials from rendered screenshots. Document the remaining art work while a temporary asset is in use.

Implement references/02-neuron-explorer.png as the X-ray and circuit view. Fade the outer mesh, maintain recognizable eyes and wings, and show a selectable neural scene. Use measured soma coordinates for the overview. For a small selected group, fetch and cache documented official skeletons when accessible, record IDs, units, coordinate transforms and source version. Treat within-body registration as an explicit authored overlay unless landmarks validate its placement. Label that registration status in the method/inspector view. The enlarged external scientific view can use native atlas coordinates independently of the body's display pose.

Use references/03-replay.png for the replay layout. Provide a local user-selected video, the fly view and the neural view with one playhead. Support manual alignment to the start of a repetition. Until the user supplies a video, show a clearly labeled placeholder.

## Meaning of the neural display

Every activity value must resolve to a received simulation value with a stable official body ID and a simulation timestamp. The current compact model uses rate-like activity. Make glow intensity reflect that quantity. An animated firing event or propagation delay needs the corresponding modeled event and timing data. Show missing observations distinctly from a received zero.

Reuse the source's anatomical overview, circuit metadata and inspector where they remain correct. The overview contains more anatomical positions than the compact circuit simulates. Make the active model scope and observed counts inspectable. Display a selected neuron's identity and value precisely, and show its received time series.

The actuator mapping from descending activity to force is an engineered model of this gym. Record the mapping and its units. Separate measured connectivity, model dynamics and authored mechanics in a concise methods view. Claims in the interface must follow what this implementation actually computes.

## Authoritative simulation and controls

Python owns neural updates, load, joint motion, repetitions, rewards and simulation time. Rendering reads snapshots. Interpolation may smooth poses visually and must preserve the values used for counters and export.

Extend the existing protocol minimally for load changes and run control. Inspect its current schemas first. Validate finite bounded values, support duplicate-safe command identifiers where retries are possible, and return an acknowledgement with the effective simulation step. Apply new load at an unambiguous rack/repetition boundary and show any pending change in the UI. Make reconnects restore an authoritative snapshot.

Pause must stop model time after acknowledgement. Changing the camera, activating X-ray or selecting a neuron must leave the simulated trajectory intact. Implement slower playback through recorded timestamps first. Use the existing repetition mechanics and preserve rejection of incomplete strokes. Test a zero-drive run and identical-drive runs with different loads through normal entry points.

Store each experimental run under a separate identity with its seed, model version, initial state, load and time step. Preserve user-supplied videos locally and keep experiment resets scoped to the selected run.

## Recording, replay and export

Record actual time-stamped states and metadata, including model scope and the identity/value pairs required to reproduce the displayed neural activity. Choose one documented versioned recording format compatible with the existing telemetry. Use frame indices and simulation time to align streams.

Recorded replay must work with the Python server stopped. Bundle a short verified sample and its licensed assets into a static build. Seeking, pause, restart and playback speed should select the same sampled states and preserve repetition counts. Indicate LIVE or RECORDED plainly. In replay, a load control can select a precomputed scenario or ask to start a live run with that load.

Support CSV for the experiment and JSON/NDJSON for exact replay. Include provenance for every sample and a consistent time base. Provide one documented run command and one command for the static replay build. Test the static build under a repository subpath as well as at the root.

## Evaluation and verification

Use the existing test suites and add only tests that protect new behavior. Follow the acceptance gates in IMPLEMENTATION_PLAN.md. Capture the real UI at 1280×720 and 1920×1080, including workout, X-ray/selected neuron and replay. Exercise controls in a real browser. Record a short actual demo and inspect WebGL2 fallback in addition to available WebGPU.

Target fluid desktop rendering, with 30 FPS as the initial measured threshold at 1280×720 on the documented test machine. Report the machine, graphics backend, scene size and sampling interval. Use batching, bounded telemetry, a capped pixel ratio and a small selected skeleton group. Measure hot paths before changing the model. If no suitable GPU browser is available, report the graphics validation gap explicitly.

For the conference comparison, use a fixed-load bench task and compare the neural-drive condition with a periodic controller matched for period and commanded actuator impulse per cycle. Keep mechanics and initial state identical. Calibrate on a separate condition, then fix parameters before the load sweep. Export completed repetitions, achieved travel and positive mechanical work. Report deterministic conditions directly and distinguish model seeds from biological specimens.

## Deliverable for every milestone

Provide the runnable state, exact commands, actual check results, browser evidence, changes to the plan and any unresolved gap. Keep the next step concrete. A completed build includes the licensed rig, working controls, actual neural telemetry, replay without the backend, reproducible experiment output, methods/provenance, notices and tested startup instructions.

Start with P0 now, record its conclusions, then implement P1 within the same execution session if resources permit.
