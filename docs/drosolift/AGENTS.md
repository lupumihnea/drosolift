# DrosoLift implementation rules

These are proposed project instructions for the implementation checkout. Preserve applicable upstream instructions when adopting them.

## Outcome

Deliver an interactive gym scene with a licensed articulated fruit fly, an inspectable neural model and synchronized replay. The reference PNGs in docs/drosolift/references guide the composition, materials and emphasis.

## Existing project

- Start from the revision recorded in SOURCES.md and preserve upstream history, license and notices.
- Read the existing brain, world, simulation, frontend and tests code before modifying their interfaces.
- Keep the source's Python/aiohttp and TypeScript/Three.js stack where it supports the task.
- Reuse existing equipment mechanics, model representations, telemetry parsing, anatomical positions and inspector behavior.
- Keep the ordinary project entry points runnable after each milestone.
- Make small cohesive commits when local author configuration permits, and keep user changes intact.

## Data and model behavior

- Python owns the model state, equipment motion, model clock and repetition counters.
- Use stable official body IDs and versioned source metadata.
- Derive activity colors from recorded/received values. Present unobserved and zero values distinctly.
- Describe rate activity as rate activity. Render spike events only when the model exposes those events.
- Keep compact model scope visible and preserve exact numerical inspection.
- Record the engineered motor-to-force mapping and the calibration used for the display.
- Use finite bounded input validation and an acknowledged effective step for model-changing commands.
- Make run resets, command retries, pause and reconnect consistent.
- Keep visual interpolation and model state independently testable.

## Assets and visual quality

- Follow the asset rights and provenance decisions in SOURCES.md.
- Give each redistributed asset a source, license and transformation record.
- Preserve six legs and use front-leg grip targets tied to the actual bar pose.
- Use atlas coordinates in the scientific viewer. Record and qualify authored within-body overlays.
- Review real screenshots and fix framing, intersections, unreadable text and material failures.
- Inspect compatible WebGL2 rendering and the available WebGPU path.
- Preserve useful numerical/HTML controls when the 3D renderer is unavailable.
- Keep GLB assets, textures and selected skeleton caches reasonably bounded.

## Work and evidence

- Read the current milestone and acceptance gate before editing.
- Run relevant existing checks and focused regressions for changed behavior.
- Exercise new controls through the same browser flow used by the audience.
- Keep protocol, recording and scientific metadata inspectable.
- Record exact commands, measured results and unresolved gaps.
- Keep experiment data and large downloaded source archives outside git.
- Produce a self-contained recorded demo for conference use.
