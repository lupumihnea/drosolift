import { ACESFilmicToneMapping, PCFShadowMap, WebGPURenderer } from "three/webgpu";

/** Native WebGPU when available; Three.js performs adapter-failure WebGL2 fallback. */
export async function createGraphicsRenderer(forceWebGL: boolean, onFailure: () => void) {
  const renderer = new WebGPURenderer({ antialias: true, alpha: false, forceWebGL });
  let initialized=false;
  let failure: Error | null = null;
  const markFailed = () => {
    if (failure) return;
    failure = new Error("Graphics backend failed");
    onFailure();
    // Initialization may still be pending; stopping is best-effort on a failed backend.
    void renderer.setAnimationLoop(null).catch(() => {});
  };
  const assertHealthy = () => { if (failure) throw failure; };
  const originalDeviceLost = renderer.onDeviceLost.bind(renderer);
  const originalError = renderer.onError.bind(renderer);
  renderer.onDeviceLost = (info) => {
    // Three's handler also sets its internal lost-device guard; do not replace it.
    originalDeviceLost(info);
    markFailed();
  };
  renderer.onError = (error) => { originalError(error); markFailed(); };
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.25;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFShadowMap;
  try {
    await renderer.init();
    initialized=true;
    assertHealthy();
    return { renderer, assertHealthy };
  } catch (error) {
    // Three r186's dispose() calls setAnimationLoop(), which retries a failed
    // init without awaiting its rejection. An uninitialized renderer has no
    // initialized managers/animation loop to dispose; its detached canvas is GC'd.
    if(initialized)await renderer.dispose();
    throw error;
  }
}

export function graphicsBackend(renderer: WebGPURenderer): "WebGPU" | "WebGL2" {
  return "isWebGPUBackend" in renderer.backend ? "WebGPU" : "WebGL2";
}

/** Optional QA observation: renderer object counts and estimates, not driver VRAM. */
export function reportGraphicsStatistics(container:HTMLElement,renderer:WebGPURenderer):void{
  if(!new URLSearchParams(location.search).has("diagnostics"))return;
  container.dataset.graphicsStats=JSON.stringify({backend:graphicsBackend(renderer),
    geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,
    estimatedBytes:renderer.info.memory.total,drawCalls:renderer.info.render.drawCalls,
    triangles:renderer.info.render.triangles,points:renderer.info.render.points,lines:renderer.info.render.lines});
}
