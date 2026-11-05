# Actual browser verification — 4 November 2026

The final native-GPU live browser checks passed. The recorded build also passed
without a Python simulation backend, at the root and under `/conference/`.
The normal live server remains at `http://127.0.0.1:8000`; the documented portable
recorded server is running at `http://127.0.0.1:8010`.

## Reproduce the checks

From the implementation checkout, with the normal gym server on port 8000 and
the documented `scripts/serve_replay.py` server on port 8010:

```powershell
.venv/Scripts/python.exe scripts/check_drosolift_browser.py --url http://127.0.0.1:8000 --live-only --output docs/drosolift/evidence/native
.venv/Scripts/python.exe scripts/check_drosolift_browser.py --static-only --software --output docs/drosolift/evidence/offline
.venv/Scripts/python.exe -m scripts.check_drosolift_extras --resources
```

The first command uses ordinary installed Chrome and the available GPU. The
second explicitly checks the software WebGL2 fallback and creates temporary
static servers; it never connects to the simulation. For the actual backend-off
acceptance check, the earlier full check ran with `--stop-backend-pid 32764`,
terminated that known test server after live verification and confirmed `/health`
was unreachable. All subsequent root/subpath offline checks ran while that
backend remained stopped. A fresh live server was started afterward for review.

The browser QA helpers use Playwright with installed Google Chrome. Playwright's
FFmpeg helper records the actual app, rather than generating an illustrative
video. These are acceptance scripts, not a source of model state. Their only
protocol probe retries an exact command originally sent by the UI. A separate
probe closes a real paused WebSocket and observes the normal reconnect.

## Observed behavior

Final native results: [`evidence/native/browser-results.json`](evidence/native/browser-results.json).

- All **91 received neural rows** matched the real WebSocket body ID, label and
  full numerical value. Selected official body **10783** remained selected and
  showed **28 distinct received rates in 96 samples**. A real full return stroke
  advanced repetitions **15 → 16**. Exact sample evidence is in
  [`browser-telemetry.json`](evidence/native/browser-telemetry.json).
- Pause acknowledged at **step 656**, elapsed **65.60000000000055 s**, joint
  **0.20693576086853105**. The full received state stayed identical for the
  600 ms pause check and through three camera modes, neuron selection and X-ray.
  Four rapid X-ray toggles returned to the official morphology mode consistently.
- Load **0.6 → 0.8** remained pending during a paused incomplete stroke. Retrying
  the exact UI command was duplicate-safe; it applied at **step 705**. Reload
  restored the same paused run, joint and counters at **step 821**.
- At **390 px** and **320 px**, connection and controls remained visible with no
  horizontal overflow. With all graphics contexts deliberately unavailable,
  91 numerical readings still arrived, pause worked and load remained reachable.
  The normal live check produced **zero page errors**.
- The production static server on port 8010 opened directly in **RECORDED** mode,
  served JavaScript with the correct MIME type and opened **zero WebSockets**.
  Its replay load input is hidden. A local-file test used the actual app demo as
  its fixture; no athlete video is supplied or implied. Manual offset **2 s**
  aligned the video to **6.52 s**, exactly matching the shared playhead.
- Closing the paused real WebSocket reconnected to the same complete snapshot,
  run identity and station loads. Population setup **1 → 10 → 1** preserved model
  steps while paused. Selecting fly-2 and its camera preserved state; after an
  explicit resume established its grip, the chamber identified the bicep curl
  and displayed station-2's actual **0.4** load. The final population is one and
  the live model is resumed. Extra outcomes are in
  [`extras-results.json`](evidence/native/extras-results.json).

  Previously removed identities retain physical state and recovery. Readding one
  does not promise a new grip; repeated checks inspect a station readout only
  when that identity is actually attached. The initial station-2 curl/load
  inspection and the paused population controls were exercised separately.

Offline results: [`evidence/offline/browser-results.json`](evidence/offline/browser-results.json).
Both root and `/conference/` selected the exact recorded **step 100** when
seeking. Quarter-speed playback advanced **four recorded steps over 1.2 s** while
preserving sampled states. JSON exports reproduced all frames exactly; CSV had
**201 rows** and the same final repetition count. Restart returned to the first
sample. The dedicated `dist-replay` build opened in RECORDED mode without a
`replay=1` query at both paths. These checks produced no page errors.

## Graphics and bounded resources

Test machine: Windows 10 build 19045; AMD64 Family 23 Model 113 Stepping 0,
12 logical CPUs; installed Chrome **157.0.8103.15**; NVIDIA **GeForce GTX 1060
6GB**, ANGLE Direct3D11. Device pixel ratio was 1. The overall viewport was
**1280 × 720**, with the workout canvas **749 × 354** and the neural panel
rendering the official 139,659-soma atlas beside it.

After 1.5 s additional warm-up, a **10.0004 s** observation saw **1,437 callbacks
per Three.js renderer loop**, corresponding to **143.59 callbacks/s**, with a
maximum interval of **7.1 ms**. This exceeds the initial 30 FPS target on the
documented native GPU. It measures actual presentation/render-loop cadence;
GPU completion time and display scanout are not measured. The explicitly forced
SwiftShader diagnostic measured **3.43 callbacks/s** and does not meet that
target. These two results must not be presented as interchangeable hardware.

The unforced application initialized **WebGPU** on this machine; a real WebGPU
replay screenshot was also captured on port 8010. Forced **WebGL2** passed all
live interaction checks. WebGPU's frame cadence was not separately benchmarked.

Optional `?diagnostics=1` observations after warming both visual modes showed:

| View | Geometry objects | Textures | Estimated bytes | Draw calls | Scene content |
| --- | ---: | ---: | ---: | ---: | --- |
| Workout | 89 | 9 | 45,758,411 | 121 | 42,907 rendered triangles; 128 line segments |
| Neural detail | 5 | 2 | 3,349,121 | 5 | 139,723 rendered points; 22,413 official skeleton segments |

Geometry/texture counts and estimated bytes remained unchanged through **five
additional off/on X-ray cycles**, saved in
[`resource-switching-results.json`](evidence/native/resource-switching-results.json).
These are renderer object/byte estimates,
not driver-reported VRAM. The original fly has 18,932 unique authored triangles;
render counts include equipment and passes. The selected morphology cache is
978,668 bytes and retains only two official SWCs.

## Reviewable artifacts and fixes from inspection

Final screenshots:

- Workout: [1280 × 720](evidence/native/workout-1280x720.png),
  [1920 × 1080](evidence/native/workout-1920x1080.png).
- Selected neuron / X-ray with official morphology:
  [1280 × 720](evidence/native/neurons-xray-1280x720.png),
  [1920 × 1080](evidence/native/neurons-xray-1920x1080.png).
- Recorded replay: [1280 × 720](evidence/native/replay-1280x720.png),
  [1920 × 1080](evidence/native/replay-1920x1080.png).

Actual screen recording:
[`drosolift-live-demo.webm`](evidence/native/drosolift-live-demo.webm),
**23.08 s**, VP9, 1280 × 720, encoded at 25 FPS, 4,222,289 bytes. The 20.094 s
interaction portion includes real repetitions **18, 19, 20 and 21**, workout and
X-ray views. SHA-256:
`afcbd660014da5656741d44fd91a86bfceca00de78df91774dc2ee60de5de2c1`.

Actual initial screenshots prompted camera changes, darker padding, finer eyes,
folded support legs and visible lateral wings. A native screenshot confirmed the
fixes. An initial static-server check exposed this Windows installation's `.js`
MIME registration as `text/plain`; explicit MIME mapping in the shipped static
server fixes it. A later population check found a stale normal build after the
curl title change; rebuilding it resolved the discrepancy. The preserved first
software attempt is labeled `browser-results-live-attempt1.json`; the final
native and offline results above supersede it.

A focused portable-navigation regression initially showed that clicking NEURONS
left recorded mode. Observer tabs now preserve RECORDED status, the nonzero
playhead (**step 78** through NEURONS → WORKOUT → REPLAY) and zero-WebSocket
operation; returning to live is explicit. The final aggregate is
[`evidence/browser-results.json`](evidence/browser-results.json).

Remaining limitations: the original fly and studio are stylized compared with
the photoreal reference. Some far limbs are naturally occluded in the selected
view, while the six chains and both foreleg grip endpoints are regression tested.
The neural overview is measured somata with two selected official morphologies,
not full-CNS morphology or validated within-body registration. No athlete video
is bundled. WebGPU performance, GPU completion times and driver VRAM remain
unmeasured; the explicitly tested software path is slower than the desktop goal.
