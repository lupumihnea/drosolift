# Runtime fly asset decision

P0 audit: `fly-model.ts` imported only `walking-fly.glb`. Its upstream notice
records local reuse permission but supplies no standalone public redistribution
license. The static CT GLB is CC BY 4.0 and has no articulated skeleton. A
redistributable runtime therefore needs a replacement; no raw archive download
is required to build the first workout screen.

P1 uses the original `frontend/web/src/procedural-fly.ts` generator. Its source
and generated geometry are project contributions licensed under Apache-2.0.
It imports no third-party meshes, textures, animation data or skeleton geometry.
The handoff PNGs were inspected for color, silhouette and wing/eye emphasis;
their pixels are not part of the runtime asset. The restricted upstream GLB
remains in preserved upstream source/history but is not imported or emitted by
the production application. Do not offer it as an Apache-2.0 asset.

## Reproduction and transformations

`loadFlyModel()` builds the same parametric geometry on every load, with no random
numbers, network requests, Blender installation or additional package. The
generator returns the existing GLTF-compatible scene interface. Original geometry
uses +Z forward and +Y up. `AnimatedFly` rotates +Z onto the scene's +X and
normalizes the authored longitudinal bounds to 2.2 display units. Python's
received body pose and equipment joint position still determine the physical
root, supination and two front-leg grip targets. Six separate three-joint bone
chains retain independent per-fly transforms while cloned mesh geometry and
materials are shared.

The adjacent `assets/fly/procedural-source.json` records the generator SHA-256,
coordinate transforms and measured scene budget: 18,932 triangles, 50 mesh
objects, 3 line objects and 20 bones per fly before instancing/cloning.

The red faceted eyes, ochre segmented abdomen, thorax stripes, bristles and
translucent veined wing pair are original illustrations. Walk rotation clips
depend on received ground distance; the feeding clip depends on received eating
state. Neither clip advances a gym weight or manufactures repetitions. Foreleg
IK reuses the upstream two-segment solver against the actual bar grip targets.

This is a stylized fly of unspecified sex, not a CT-derived rig, a measured
MaleCNS specimen or a biomechanical anatomy reconstruction. Bone lengths,
proportions, segmentation, eye facets, wing veins, pigments, materials and
body registration are authored display choices. Compared with reference 01,
the mesh has less surface realism and fine detail. Detailed CT-derived rigging
remains optional art work; the displayed procedural asset is already licensed
and reproducible rather than a permission-dependent temporary mesh.

Screenshot-guided correction: the upstream supinated body pose made the walking
rest pose point four free legs upward and hid the folded wings against the pad.
`bench-support-pose.ts` now folds mid/hind legs outward toward the cushion and
fans the wing membranes laterally above it. This bench-only authored display
pose restores on detachment/curl; it does not change limb lengths, physical root,
front grip IK, load, joint state or counters. Finer original eye faceting was
added after the real screenshots. The new support-pose regression first failed
with an upward foot at y=1.479 versus hip y=1.001, then passed after the pose fix.

## Preserved upstream asset rights

`drosophila.glb` and its source manifest/attribution remain unchanged under
CC BY 4.0: Orestis Katsamenis, Pieterjan De Boose, Herman Wijnen and Arno Thielens,
Zenodo [record 14838021](https://zenodo.org/records/14838021),
[DOI 10.5281/zenodo.14838021](https://doi.org/10.5281/zenodo.14838021).
It depicts a female surface and is not currently loaded by the application.
The CT credit and original walking-asset permission notice remain in
`THIRD_PARTY_NOTICES.md` and `frontend/web/src/assets/fly/`.

## Focused verification

Before the loader replacement, `bun test procedural-fly.test.ts` failed both new
tests (the GLB loader needed browser ProgressEvent and timed out in Bun).
After replacement, both pass: 34 assertions cover the original-asset license,
six articulated chains, eyes/wings, a 60,000-triangle bound, distinct cloned pose
state, and front-leg contact within 0.001 display units at q=0, 0.5 and 1.
The complete browser unit suite passed 37 tests / 214 assertions.
`bun --bun run typecheck` passed. The `--bun` flag is needed on this machine
because its global Node 18 cannot run the upstream extensionless TypeScript 7
entry point. Browser composition, material/contact screenshots and regression
results are recorded in the milestone evidence by the integrating agent.

## Visual revision 2 — studio and articulated fly

The second visual pass keeps the same original Apache-2.0 generator and the
same bone names, joint lengths, +Z/+Y source frame and 2.2-unit longitudinal
normalization. The generator now supplies a smooth tapered abdominal shell with
surface pigment bands, a narrower head/frons, 2,048 shallow hexagonal eye facets,
cuticle micrograin, limb setae, branched aristae and curved translucent wings with
branched veins. All surface patterns are deterministic original DataTextures;
no outside mesh, texture, image pixels or animation was imported. The source
compatibility identifier remains `DrosoLift procedural fly v1`; `artRevision: 2`
and the refreshed source SHA256 identify this artwork revision.

The current source has **50 mesh objects, 18 line objects, 20 bones and seven
shared mesh geometries**. Counting each mesh geometry once gives **36,936
triangles**; counting every instanced eye facet gives **49,212 rendered triangles
per fly**, below the retained 60,000-triangle regression bound. The eye facets
use flat hexagonal surfaces rather than small extruded cylinders, avoiding hard
horizontal specular bands and reducing the instance-aware triangle total. The
regression was first observed failing at 71,356 triangles, then passed after this
correction. Two generated 128x256 RGBA textures supply cuticle/pigment detail.

`world-scene.ts` adds original dark wall panels, shallow floor seams, ribs,
recessed cyan strips and visible overhead softbox housings. The studio walls
lie outside the physical 20x12 arena; they are set dressing, not new collision
geometry. Static decoration is batched by material. Warm key and cooler rim/fill
lighting, rounded padding, seams, brushed steel, beveled plate profiles and rack
bolts replace the earlier plain floor and sharp-edged blocks. The selected
observer camera is closer and more lateral, with a 0.75-unit target height;
these changes never move the model root or advance the simulation.

Bench padding now has a 0.60 display-unit top surface to meet the authored
supinated body. For the existing curl posture (body elevation 0.5, pitch 0.55),
two sloped rubber supports at lateral z = +/-1.02 meet the four free feet. Their
surface is `y = 0.525 + tan(0.55)*x`, matching measured rendered foot coordinates
near (-0.256, 0.368) and (-0.482, 0.229). These are authored support geometry for
an already imposed pose, not new contact/force mechanics. Front-leg IK and all
Python load, root, clock and repetition behavior are unchanged.

Two independent per-station indicator meshes, `indicator-left` and
`indicator-right`, remain outside static geometry batches. Their initial grey
appearance means unobserved; the application colors them only from received
synthetic apparatus feedback. Their signal meaning and calibration are in the
control/model methods, not inferred from the decorative material.

Real preview captures at 1920x1080 and 1280x720 were made after actual WebSocket
frames and ordinary exercise-button actions. The bench capture received step
3064 / q=0.12042747823862777 (lowering); the curl capture received step 3090 /
q=0.2787394935664679 (lifting). Both were inspected: full apparatus, held grips,
bench contact and curl foot support are visible. The preview emitted zero page
errors. Evidence is under `evidence/visual-revision/` and includes `art-check.json`.
The final integrated captures supersede these preview screenshots for the last
small eye/frons refinement and neural-view changes.

## Visual revision 2 — neural display assets and registration

The default neural view uses eight official MaleCNS SWCs under CC BY 4.0. The
bounded cache is 2,275,156 bytes, SHA-256
`d6d21b0a206f3790b98b12e51ba639bf24def5a92527fc0eda4f2025ec1e75f2`;
it preserves 51,940 source nodes and 51,931 parent edges. Sources, body IDs,
transforms and exact rate-display calibration are in [MORPHOLOGY.md](MORPHOLOGY.md).
No source meshes, inferred neurites or activity values are generated to fill
unobserved cells. Anatomy uses source coordinates; Circuit uses a separate,
explicitly authored layout of official runtime IDs and edges.

`neural-sprites.ts` creates an original analytic 64x64 radial alpha texture under
the project's Apache-2.0 contribution license. Its camera-facing sprites sit at
measured somata in Anatomy and authored diagram coordinates in Circuit. The
background soma cloud has a uniform muted anatomical-context color, not an
activity field. Received rate controls the separate cell/morphology color and
opacity through a documented square-root display transfer; exact values remain
inspectable. No traveling pulse or spike animation is used.

The optional fly-body motor-routing overlay is an authored explanation of the
engineered command-to-foreleg mapping. It is not a registered MaleCNS anatomical
reconstruction inside the fly. The official native atlas and source morphology
remain separately inspectable in the right-hand neural view.

## Reference UI revision 3 — neural presentation

The eight-cell morphology cache and all asset/source licenses are unchanged.
The new frontal brain-only view is an authored native-coordinate display crop
(`Z <= -0.28`), with the full VNC available as an observer toggle. It moves no
source coordinate and fabricates no boundary vertex. The cool-blue background
uses 124,294 measured somata inside that crop; it is anatomical context rather
than an activity map of unobserved cells. Actual received cells/morphologies use
the documented cyan-to-yellow rate palette, while Cell colors explicitly shows
stable model-group colors. The supplied phone reference contributes no source
pixels, FlyWire data, neuron counts, spike events or functional biological claims.

The rate-history heatmap is drawn locally from actual sampled IDs, timestamps
and values, bounded to 96 columns × 91 model cells. It is not a spike raster.
The radial sprite kernel remains the original analytic Apache-2.0 display asset.
Native coordinates, exact crop, palette transfer, identity-color mode, history
reset behavior and validation are detailed in [MORPHOLOGY.md](MORPHOLOGY.md).

Focused checks passed **six tests / 103 assertions**: actual instanced geometry
budget, independent clone pose, displacement-driven walking, bench/curl grips
at q=0,0.5,1, bench support restoration and curl support contact. The new curl
support test was observed failing before its helper existed; all four free feet
then matched the support surface within 0.005 display units while both foreleg
endpoints remained within 0.001 of received grip targets. This is still authored
illustrative anatomy and a studio rendering, not photogrammetry or a validated
biomechanical reconstruction.

## X-ray and applied plate visualization — 5 November 2026

The body X-ray now includes an original bilateral blue envelope illustration,
compact circuit markers and structural links. The envelope and within-head
layout are authored display geometry; they are not measured morphology, atlas
registration or a claim that the compact cells occupy those body locations.
The scientific panel retains its independent measured atlas and official SWCs.
The visible caption reads "Received neural activity · illustrative placement".

`motor-overlay.ts` derives its stable marker IDs from the pinned runtime's
model groups (91 cells), and its 92 structural edge triples come directly from
that same runtime JSON. Each marker resolves to a received body ID, exact rate,
step and elapsed time. A missing observation remains null and uses the subdued
blue missing-data appearance; received zero stays distinct. The shared static
blue/cyan-to-yellow rate transfer is applied with a 0.75 body-overlay display
gain. Fixed-radius 0.0095-unit markers and structural-edge opacity 0.12 avoid
an overexposed white cluster. The envelope is a static blue illustration, not
additional neurons. The separate authored actuator routes still follow actual
rig joints and received `motor.forward`. No timed firing, traveling pulse or
unmodeled propagation event is introduced.

X-ray fades cuticle to opacity 0.09, eyes to 0.18, and wing membranes to at most
0.08 while retaining their original colors and recognizable silhouette. It
restores each material's original opacity, transparency and depth-write state.
The body overlay is rooted to the current selected Head transform, and its
neural and engineering metadata retain the received step/time. Selecting a fly
isolates its visual mesh and apparatus in the workout camera; other active
identities continue receiving and sampling their own trajectories.

Applied loads now have a visible, bounded plate representation on both kinds
of equipment. Its explicit authored calibration is

```text
n = clamp(ceil((applied_load - 1e-9) / 0.2), 1, 15) discs per stack
```

The tiny tolerance prevents floating-point representations of 0.6 becoming
four discs. The supported model load range remains 0.1..3.0 virtual force units;
this is not a conversion to kilograms. Bench presses have two symmetric stacks,
so 0.6 -> 0.8 adds two discs total (three -> four per end). The two dumbbells have
four stacks, so 0.4 -> 0.6 adds four discs total (two -> three per end). Disc
radii are 0.35 for bench plates and 0.185 for curl plates; axial thickness/pitch
are 0.025/0.032 and 0.012/0.017 display units respectively. At most 30 bench or
60 curl discs are rendered, using a single instanced plate mesh per station.
Collars and shafts extend along the same bar axis to contain the visible stack;
the bar's received joint position and both grip targets are unchanged.

`EquipmentScene.setLoad(id, load)` accepts only finite actual applied values in
the declared range and preserves the input station records. `FlyScene` passes
`control_state.loads[].load`; it never passes `pending_load` to the geometry.
Retrying an unchanged applied load does not rebuild geometry. Rendering uses
instancing with bounded counts, rather than allocating new plate geometry on
every control update. The scene exposes applied load, discs per stack, total
disc count and registration/observation counts for actual browser verification.

Targeted regressions were first observed failing on the missing plate API and
old motor-only overlay. They then passed: nine focused tests / 142 assertions
cover applied symmetric disc changes, finite/bounded/retried loads, unchanged
q/grip/root transforms, real neural IDs/values/edge triples, zero/missing state,
repeatable colors without time pulses, and the retained articulated rig/support
checks. The whole TypeScript check passed. The observer-only native browser
preview showed actual curl load 0.4, two discs per stack/eight total, and 91
observed body-overlay cells, with no page errors and no model commands sent.
See `evidence/training-review/xray-weight-browser-preview.json`; the final
integrated captures supersede that preview for the final small opacity tune.
