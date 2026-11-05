# Source audit and implementation decisions

Read-only audit performed on 4 November 2026. The handoff includes the three reference images and original implementation instructions. It does not contain copied application code. Upstream execution is the first implementation milestone.

## Recommended base

**tiredbooy/Fruit-Fly**, pinned at commit **2c5a03aa90f01048f011e13546b4d7fffc693945**. The repository identifies its own code and project-produced media as Apache-2.0. Preserve LICENSE, NOTICE and THIRD_PARTY_NOTICES.md when deriving the implementation.

The inspected project already has Python/aiohttp, TypeScript, Three.js, Vite and Bun scripts, an articulated gym and a compact connectome-derived model. The current gym server explicitly requires the compact backend. Its readout is rate-like activity and its motor-to-force mapping is an authored gym mechanic. The source reports its own checks in its documentation. Re-run those checks in the target environment.

[Repository](https://github.com/tiredbooy/Fruit-Fly) · [Pinned revision](https://github.com/tiredbooy/Fruit-Fly/commit/2c5a03aa90f01048f011e13546b4d7fffc693945) · [License and asset notices](https://github.com/tiredbooy/Fruit-Fly/blob/main/THIRD_PARTY_NOTICES.md)

## Files inspected or resolved in the source tree

| Capability | Existing paths |
| --- | --- |
| Run and build entry points | `Makefile`, `main.py`, `requirements.txt`, `frontend/web/package.json` |
| Gym composition and signals | `simulation/gym.py`, `simulation/gym_signals.py` |
| Equipment mechanics | `world/equipment.py`, `docs/science/equipment.md` |
| Gym commands and telemetry | `frontend/gym_server.py`, `frontend/gym_telemetry.py`, `frontend/telemetry.py` |
| 3D equipment and front legs | `frontend/web/src/equipment-scene.ts`, `equipment-meshes.ts`, `foreleg-pose.ts` |
| Rendering and anatomical view | `frontend/web/src/graphics-renderer.ts`, `neuron-map.ts`, `neuron-inspector.ts` |
| Existing browser verification | `scripts/check_equipment_browser.py`, `scripts/check_gym_browser.py` |
| Compact circuit and provenance | `data/circuits/gym-v1-runtime.json`, `data/circuits/gym-v1-learning.json`, `data/malecns/v1.0/source-manifest.json` |
| Soma positions | `frontend/web/public/assets/neuron-positions.json` |
| Body-asset source record | `frontend/web/src/assets/fly/ATTRIBUTION.md` |

Paths after the first frontend prefix in a cell remain relative to that same directory. Resolve them in the checked-out revision before editing.

## Asset decision

The file `walking-fly.glb` has permission recorded for its author's local reuse, with no standalone public redistribution license supplied. Replace it in the redistributable build unless suitable permission is established.

The separate `drosophila.glb` is a static CT-derived surface with CC BY 4.0 attribution. It has no animation skeleton. Its source is Zenodo **10.5281/zenodo.14838021**, and it represents a female specimen. It can be the documented visual source for a newly authored rig. Keep its credit and describe the body/connectome combination accurately.

[Asset notices](https://github.com/tiredbooy/Fruit-Fly/blob/main/THIRD_PARTY_NOTICES.md) · [CT asset attribution](https://github.com/tiredbooy/Fruit-Fly/blob/main/frontend/web/src/assets/fly/ATTRIBUTION.md) · [CT source](https://doi.org/10.5281/zenodo.14838021)

## Anatomical data

Use MaleCNS v1.0 IDs and the upstream provenance records. Measured soma coordinates support an anatomical point cloud. Skeleton morphology and within-body registration require their own source and transforms. The official guide documents a neuPrint API-token route for skeletons and points to raw data and template transforms. Public exports may offer an alternative for selected cells.

[MaleCNS](https://male-cns.janelia.org/) · [Access and morphology](https://male-cns.janelia.org/download/) · [Article](https://doi.org/10.1016/j.cell.2026.08.015)

## Additional references

| Source | Role in this build |
| --- | --- |
| [FalinX/fly-brain](https://github.com/FalinX/fly-brain) | Reference for simultaneous task, anatomy and telemetry display. Check individual files and license before copying. |
| [NeuroMechFly / FlyGym](https://github.com/NeLy-EPFL/flygym) | Optional later biomechanical work. Inspect asset-specific rights if reusing meshes. |
| [Pugliese et al. code](https://github.com/smpuglie/Pugliese_2026) | Optional separate study of rhythmic motor circuits. Keep its model/version identifiable if integrated. |
| [Three.js documentation](https://threejs.org/docs/) | Renderer, materials, animation, batching and compatible postprocessing. |
| [Playwright visual comparisons](https://playwright.dev/docs/test-snapshots) | Browser evidence and reproducible visual checks. |
| [Current model guidance](https://learn.chatgpt.com/docs/models) | Model availability and reasoning choices. |
| [OpenAI selection guide](https://developers.openai.com/api/docs/guides/model-selection) | Workload-based model comparisons. |
| [Claude Code model configuration](https://code.claude.com/docs/en/model-config) | Opus/Sonnet aliases and opusplan behavior. |
| [Claude Code best practices](https://code.claude.com/docs/en/best-practices) | Explicit verification and iteration practices. |

The generated PNGs are visual references from the user's conversation. They supply the artistic direction and contain illustrative anatomy/activity. The replay athlete is a generic placeholder. The implementation must compute the values it displays and keep source-backed data distinguishable in its methods.
