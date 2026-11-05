import { expect, test } from "bun:test";
import * as THREE from "three/webgpu";
import { disposeScene } from "./scene-primitives";

test("disposes shared point-cloud geometry and material exactly once", () => {
  const scene = new THREE.Group();
  const geometry = new THREE.BufferGeometry();
  const material = new THREE.PointsMaterial();
  let geometryDisposals = 0;
  let materialDisposals = 0;
  geometry.addEventListener("dispose", () => geometryDisposals++);
  material.addEventListener("dispose", () => materialDisposals++);
  scene.add(new THREE.Points(geometry, material), new THREE.Points(geometry, material));

  disposeScene(scene);

  expect(geometryDisposals).toBe(1);
  expect(materialDisposals).toBe(1);
});

test("deduplicates resources shared by points, meshes, and lines", () => {
  const scene = new THREE.Group();
  const geometry = new THREE.BufferGeometry();
  const material = new THREE.ShaderMaterial();
  let geometryDisposals = 0;
  let materialDisposals = 0;
  geometry.addEventListener("dispose", () => geometryDisposals++);
  material.addEventListener("dispose", () => materialDisposals++);
  scene.add(
    new THREE.Points(geometry, [material, material]),
    new THREE.Mesh(geometry, material),
    new THREE.Line(geometry, material),
  );

  disposeScene(scene);

  expect(geometryDisposals).toBe(1);
  expect(materialDisposals).toBe(1);
});

test("shared procedural surface textures are released exactly once",()=>{
  const scene=new THREE.Group();const texture=new THREE.DataTexture();let disposals=0;
  texture.addEventListener("dispose",()=>disposals++);
  scene.add(new THREE.Mesh(new THREE.BoxGeometry(),new THREE.MeshStandardMaterial({bumpMap:texture,roughnessMap:texture})),new THREE.Mesh(new THREE.BoxGeometry(),new THREE.MeshStandardMaterial({map:texture})));
  disposeScene(scene);expect(disposals).toBe(1);
});

test("shared neural sprite geometry, materials and glow texture are released once",()=>{
  const scene=new THREE.Group(),texture=new THREE.DataTexture();
  const material=new THREE.SpriteMaterial({map:texture});
  const core=new THREE.Sprite(material),halo=new THREE.Sprite(material);
  let geometries=0,materials=0,textures=0;
  core.geometry.addEventListener("dispose",()=>geometries++);
  material.addEventListener("dispose",()=>materials++);
  texture.addEventListener("dispose",()=>textures++);
  scene.add(core,halo);disposeScene(scene);
  expect(geometries).toBe(1);expect(materials).toBe(1);expect(textures).toBe(1);
});

test('instance buffers are released per object while shared geometry/material dispose only once',()=>{
 const scene=new THREE.Group(),geometry=new THREE.SphereGeometry(.1,6,4),material=new THREE.MeshBasicMaterial();
 const first=new THREE.InstancedMesh(geometry,material,3),second=new THREE.InstancedMesh(geometry,material,5);
 let firstObjects=0,secondObjects=0,geometries=0,materials=0;
 first.addEventListener('dispose',()=>firstObjects++);second.addEventListener('dispose',()=>secondObjects++);
 geometry.addEventListener('dispose',()=>geometries++);material.addEventListener('dispose',()=>materials++);
 scene.add(first,second);disposeScene(scene);
 expect(firstObjects).toBe(1);expect(secondObjects).toBe(1);expect(geometries).toBe(1);expect(materials).toBe(1);
});
