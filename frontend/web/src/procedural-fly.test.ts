import { expect, test } from "bun:test";
import { Box3, InstancedMesh, Mesh, Vector3 } from "three/webgpu";
import { loadFlyModel } from "./fly-model";
import { AnimatedFly } from "./animated-fly";

test("the shipped fly has redistributable original geometry and six articulated legs", async () => {
  const source = await loadFlyModel();
  expect(source.scene.userData.license).toBe("Apache-2.0");
  expect(source.scene.userData.source).toBe("DrosoLift procedural fly v1");
  for (const side of ["L", "R"]) {
    for (const leg of [1, 2, 3]) {
      for (const joint of ["Upper", "Lower", "Foot"]) {
        expect(source.scene.getObjectByName(`Leg${leg}${joint}${side}`)?.type).toBe("Bone");
      }
    }
  }
  expect(source.scene.getObjectByName("EyeL")).toBeDefined();
  expect(source.scene.getObjectByName("WingR")).toBeDefined();
  let triangles = 0;
  source.scene.traverse((node) => {
    if (node instanceof Mesh) triangles += (node.geometry.index?.count ?? node.geometry.getAttribute("position").count) / 3 * (node instanceof InstancedMesh ? node.count : 1);
  });
  expect(triangles).toBeLessThan(60000);
  expect(new Box3().setFromObject(source.scene).getSize(new Vector3()).z).toBeGreaterThan(1);
});

test("replacement rig keeps bench/curl grips at both endpoints and independent pose state", async () => {
  const source = await loadFlyModel();
  const fly = new AnimatedFly(source);
  const other = new AnimatedFly(source);
  const untouched = other.group.getObjectByName("Leg1UpperL")!.quaternion.clone();
  for (const kind of ["bench_press", "bicep_curl"] as const) for (const q of [0, 1, .5, 0]) {
    const bench = kind === "bench_press";
    const x = bench ? .32 : .45 + .15 * Math.sin(Math.PI * q) - .10 * q;
    const y = bench ? .90 + .70 * q : .62 + .55 * q;
    const z = bench ? -.55 : .50;
    const grips: [Vector3, Vector3] = [new Vector3(x,y,z), new Vector3(x,y,-z)];
    fly.sample(0, false, 10, {station_id:"station-1", kind, phase:"lifting", joint_position:q,
      joint_velocity:0,repetitions:0,completed_sets:0,rep_in_set:0,recovery_remaining:0,
      body_elevation:bench ? 1.5 : .5,body_pitch:bench ? 0 : .55,body_roll:bench ? Math.PI : 0}, grips);
    for (const [index, side] of ["L", "R"].entries()) {
      expect(fly.group.getObjectByName(`Leg1Foot${side}`)!.getWorldPosition(new Vector3()).distanceTo(grips[index]!)).toBeLessThan(.001);
    }
  }
  expect(other.group.getObjectByName("Leg1UpperL")!.quaternion.equals(untouched)).toBe(true);
  expect(fly.group.position.toArray()).toEqual([0, 0, 0]);
  fly.dispose(); other.dispose();
});

test("the shipped replacement walks from received displacement and shares only immutable mesh resources", async () => {
  const source = await loadFlyModel();
  const fly = new AnimatedFly(source), other = new AnimatedFly(source);
  const firstMesh=fly.group.getObjectByName("Thorax") as Mesh;
  const otherMesh=other.group.getObjectByName("Thorax") as Mesh;
  expect(firstMesh.geometry).toBe(otherMesh.geometry);
  expect(firstMesh.material).toBe(otherMesh.material);
  fly.sample(.25,false,1);
  const bone=fly.group.getObjectByName("Leg1UpperL")!;
  const pose=bone.quaternion.clone();
  fly.sample(.25,false,99);
  expect(bone.quaternion.equals(pose)).toBe(true);
  fly.sample(.6,false,99);
  expect(bone.quaternion.equals(pose)).toBe(false);
  expect(other.group.getObjectByName("Leg1UpperL")!.quaternion.equals(pose)).toBe(false);
  fly.dispose(); other.dispose();
});

test("authored bench support folds four resting legs toward the pad and restores wings off the bench", async () => {
  const fly=new AnimatedFly(await loadFlyModel());
  const restWing=fly.group.getObjectByName("WingL")!.position.clone();
  const grips:[Vector3,Vector3]=[new Vector3(.32,1.3,-.55),new Vector3(.32,1.3,.55)];
  fly.sample(0,false,10,{station_id:"station-1",kind:"bench_press",phase:"lifting",joint_position:.5,
    joint_velocity:0,repetitions:0,completed_sets:0,rep_in_set:0,recovery_remaining:0,
    body_elevation:1.5,body_pitch:0,body_roll:Math.PI},grips);
  for(const leg of [2,3]) for(const side of ["L","R"]){
    const foot=fly.group.getObjectByName(`Leg${leg}Foot${side}`)!.getWorldPosition(new Vector3());
    const hip=fly.group.getObjectByName(`Leg${leg}Upper${side}`)!.getWorldPosition(new Vector3());
    expect(foot.y).toBeLessThan(hip.y);
    expect(Math.abs(foot.z)).toBeGreaterThan(Math.abs(hip.z));
  }
  expect(fly.group.getObjectByName("WingL")!.position.y).toBeLessThan(restWing.y);
  fly.sample(0,false,11);
  expect(fly.group.getObjectByName("WingL")!.position.toArray()).toEqual(restWing.toArray());
  fly.dispose();
});
