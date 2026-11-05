import { prepareFlyAsset } from "./animated-fly";
import { createProceduralFly } from "./procedural-fly";

/** Reproducible original geometry avoids redistributing the restricted upstream rig. */
export async function loadFlyModel() {
  return prepareFlyAsset(createProceduralFly());
}
