# Official morphology and rate display — visual revision 2

The reference UI revision 3 appendix below supersedes the default framing,
palette and rate-history presentation in this revision-2 record. Official
sources, cache checksums and native coordinate transforms remain unchanged.

The default workout neural view now includes eight official MaleCNS v1.0
morphologies, measured soma context and inspectable model groups. The initial
two-cell cache is superseded; historical P0–P5 evidence describes that earlier
build. No whole-CNS morphology or biological exercise specialization is claimed.

## Source, license and bounded cache

Verified against the official [MaleCNS download guide](https://male-cns.janelia.org/download/).
Its neuPrint API route requires a token; the documented public native-SWC route
used here does not:

`https://storage.googleapis.com/flyem-male-cns/v1.0/segmentation/skeletons-malecns/skeletons-swc/{body_id}.swc`

All eight downloaded successfully. The official guide's dataset license link
resolves to [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Credit: MaleCNS / FlyEM (HHMI Janelia), University of Cambridge, MRC Laboratory
of Molecular Biology and Google Research. No account, third-party morphology or
invented branch geometry was used. Every row below is an existing official ID
in the pinned compact gym runtime.

| Body ID | Official type | Existing model grouping | Source bytes | SWC nodes | SHA-256 |
| --- | --- | --- | ---: | ---: | --- |
| 10783 | DNp09 | Descending readout | 373,551 | 10,956 | `b702c072f0a2ae0ce5531e14a4b7e197f8d13b39ac864ad7fa2c601d129e0d50` |
| 11177 | DNp09 | Descending readout | 390,438 | 11,459 | `df374c15104b8ed60c454a1f4f21d352da0ed2c21d4a33055d89c391d068ae16` |
| 36800 | L2 | Left visual input | 3,401 | 103 | `d2cffd75c247833252b3f9ce71f59827bfe9fff3d032a70e13d8f166b8cfcdd1` |
| 63316 | L2 | Right visual input | 2,133 | 62 | `ecfac3f0cedfdf5a7a7b50f01194ec0df97c065f48d10c02f887764bbd635075` |
| 201965 | ORN_DM2 | Synthetic gym cue | 16,852 | 525 | `56efbce74bbde158d5e037ebe837fc3a1449d209a889cfe5278934474247e7c2` |
| 80841 | ORN_DM2 | Synthetic gym cue | 18,350 | 565 | `92b82db8cd96d23eb81299b42a0af1dadc56faafc23f2b7f960f2669c868f396` |
| 10702 | M_l2PNl20 | Compact relay | 348,761 | 10,276 | `1dd54734c3e9edd9cb5bca7a1dd76d2d4539a5c8b44e47dabdeb36e2a3466f97` |
| 67052 | lLN2T_b | Compact relay | 627,402 | 17,994 | `f83d5c4c6dd69922fc6cd9d20e9947f305bb4abbb4fd477c92ff93822ceafb2c` |

`frontend/web/public/assets/selected-skeletons.json` is **2,275,156 bytes**, SHA-256
`d6d21b0a206f3790b98b12e51ba639bf24def5a92527fc0eda4f2025ec1e75f2`.
It preserves **51,940 original nodes and 51,931 original parent edges**. The
nine source roots/forest components are retained. Each body is capped at 20,000
nodes; the display collection is capped at eight bodies. Raw files remain under
ignored `data/raw/malecns/v1.0/skeletons/`, and the verified annotation table is
also ignored. Rebuild with:

```powershell
.venv/Scripts/python.exe scripts/export_selected_skeletons.py
```

The exporter checks annotation and SWC SHA-256, official runtime membership,
finite SWC columns, unique node IDs and parent references. It preserves all seven
numeric SWC columns and every source parent edge; source comments are omitted.
There is no morphology simplification in the cache. The glow-point layer takes
at most 1,800 original node coordinates per body; it does not add neurite nodes.

## Native coordinates and observer views

Native SWC coordinates use **8 nm units**, as documented by the official guide.
The same normalization as the measured soma overview is recomputed from the
pinned official annotation table:

```text
center = [48068.0, 36877.0, 72342.5]  # native 8 nm units
scale = 1.608014343487944e-5         # display units / native coordinate unit
display = [(x-center_x)*scale, -(y-center_y)*scale, (z-center_z)*scale]
```

Atlas axes and relative soma/skeleton placement are preserved. The default
observer camera looks along the atlas Y axis, with -Z up, exposing the long
brain-to-VNC axis rather than viewing it end-on. This changes the camera, not
the coordinates or model. Neither individual skeleton fitting nor registration
to the displayed fly is performed. A cell with no measured soma receives no
substitute soma. Its measured SWC can still appear at its native coordinates.

The Anatomy view contains the 139,659 measured somata as dim, uniform anatomical
context, the eight source morphologies and received-cell sprites only at measured
soma coordinates. Uniform context color is not an activity estimate. Morphology
segments join only original SWC parent nodes. Sparse, dim inter-cell chords join
measured soma endpoints only where the pinned runtime supplies a structural edge;
these straight chords are a connectivity abstraction, not measured axon paths.

The separate Circuit view uses an explicitly **authored layered layout** for
all 91 official runtime cells and 92 source structural edges. No schematic
coordinate enters the anatomical atlas. Link brightness uses the received
presynaptic cell's rate; it does not depict propagation, delay or a spike event.

## Functional model groups and exact observation scope

Six chips partition the runtime IDs without overlap, directly from
`gym-v1-runtime.json`: Visual L (six official L2 cells), Visual R (six L2), gym
cue DM2 (eight), food odor DM1 (eight), descending readout (six), and the remaining
57 compact relays. Every group exposes its member IDs, observation count, exact
mean and simulation timestamp in its inspectable title/data attributes. Means
include only received values; an unobserved member is not silently counted as
zero. All twelve current visual input cells are officially **L2**, not L1.

These labels describe inputs/readouts in this engineered compact model. The
apparatus-visual-v1 experiment supplies synthetic indicator feedback to existing
visual inputs; bench/curl differences are authored apparatus cues, not evidence
of biological bench-press or curl-specific brain regions. The biological source,
rate dynamics and authored sensory/mechanical mapping remain separate.

## Display calibration and compatibility

Activity is rate-like model output, not Hz or spike events. Let
`a = sqrt(clamp(received_rate, 0, 1))`. Positive-rate display intensity is
`I = 0.16 + 0.84*a`, with saturated coral linear-RGB color
`[1, 0.10 - 0.045*a, 0.03 - 0.018*a]`. Received zero uses cyan and intensity 0.14;
unobserved morphology uses muted graphite and intensity 0.035. Exact unclipped
received values remain in the numerical inspector and exported recording.
The transfer deliberately expands small received rates for legibility and is
not a biological calibration. Core sprite opacity follows I (minimum 0.18);
halo opacity is 0.3*I; morphology line opacity is 0.62*I. Group focus dims unrelated
geometry as an observer aid; it never changes a reading or the simulation.

`neural-sprites.ts` generates an original analytic 64x64 radial alpha texture.
Actual camera-facing Sprite geometry, shared by the bounded received-cell
markers, preserves radial UVs on WebGPU and WebGL2. The anatomical context and
sampled morphology nodes use untextured one-pixel Points: Three.js's WebGPU
Points primitive cannot honor an enlarged point size, and mapped Points caused
the first attempted halo rendering to disappear. Normal blending prevents dense
branches from washing the received-rate colors toward white. The texture and
all resources are disposed through the shared scene resource owner.

No render-clock firing animation, fabricated anatomical edge, unobserved-cell
activity fill or validated within-body registration is introduced. The fly's
optional motor-routing overlay is a separate authored illustration of the
engineered command-to-actuator mapping; official atlas anatomy remains at right.

## Verification

The new grouping/observation tests were first observed failing because their
module did not exist. They now verify the exact official-ID partition, observed
means, zero versus missing, monotonic rate transfer, measured-endpoint links and
explicit schematic registration. The eight-body cache test was observed failing
against the old two-cell cache and then passed after the verified export.
Final focused result: **six tests, 30 assertions passed**, plus a successful
strict TypeScript check. Real WebGPU/WebGL2 screenshot and resource evidence for
the final visual revision is recorded by the integrating QA under
`docs/drosolift/evidence/demo-v2/`.

## Reference UI revision 3 — 5 November 2026

The supplied phone screenshot guides composition, framing and blue/cyan/yellow
color balance only. Its FlyWire IDs, traced-cell count, spike labels and readout
numbers are not imported or presented as MaleCNS measurements.

The default front view shows a large frontal brain crop. This is an **authored
display crop**, not an official anatomical ROI: normalized native atlas Z must
be at most **-0.28**. It contains **124,294 measured soma positions** from the same
139,659-position source cache. The camera looks along native Y with -Z up,
target Z=-0.64; no source position is moved or fitted. VNC toggles the full CNS
back on; Front view resets only the observer camera. Skeleton buffers retain
all 51,931 parent edges, partitioned into crop-first draw ranges. A segment is
shown in the crop only when both original endpoints pass the cutoff; crossing
segments are omitted rather than replaced with invented boundary vertices.
No new geometry or source download is allocated when VNC is toggled.

Live activity uses blue anatomical context and **cyan → yellow** positive-rate
colors. The existing intensity transfer remains `I=0.16+0.84*a`, where
`a=sqrt(clamp(rate,0,1))`; the revision-3 linear RGB color is
`[0.015+0.97*a*a, 0.45+0.50*a, 0.02+0.95*(1-a)]`. Received zero is blue/cyan with
intensity 0.14; absent observations remain muted blue with intensity 0.035.
The source value is never changed by this display transfer and remains fully
inspectable numerically. Uniform blue background context is anatomy, not a
whole-brain activity field. Structural edge diagrams remain in the explicitly
authored advanced Circuit view, rather than crossing the frontal anatomy crop.

**Cell colors** uses a stable six-group palette derived from the model's existing
input/readout membership. It encodes identity/grouping, not activity. Its legend
changes to Model groups / 6 groups; Live activity is labeled Received rate /
0–1. Neither mode claims biological exercise-specialized brain regions. The
same official cell selection and exact numeric inspector work in both modes.

The new sample plot is a **received-rate heatmap, not a spike raster**. It stores
at most **96 sampled timestamps × 91 official model IDs**. Rows have stable
source-ID order grouped by the existing model roles. Every populated pixel is
derived from a received rate at its actual simulation time; missing observations
and received zero are distinct. Duplicate timestamps replace their column, a
backward seek clears the buffer, and `resetHistory()` clears it when the observed
fly/run changes. It never advances on render time while paused. The canvas
exposes sample count, ordered body IDs, last step and elapsed time; hovering a
populated sample exposes its exact historical ID, timestamp and rate. Cell
colors mode does not recolor this plot: it continues to show actual rates.

Two new focused tests were observed failing before their module existed, then
passed. They protect timestamp/zero/missing preservation, bounded samples,
duplicate replacement, backward seek/reset, source-coordinate cropping and
stable non-activity cell colors. The final focused suite passed **8 tests /
43 assertions** and strict TypeScript verification passed. Actual first-pass
screenshots are under `evidence/reference-ui/` and the integrating final browser
evidence is under `evidence/demo-v3/`. This observer-only change introduces no
neural injection, fabricated spikes or changes to exercise mechanics.
