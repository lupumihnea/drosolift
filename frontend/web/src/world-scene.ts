import * as THREE from "three/webgpu";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

/** Deterministic original rubber/concrete grain; no downloaded surface assets. */
function stageGrain(): THREE.DataTexture {
  const pixels = new Uint8Array(128 * 128 * 4);
  for (let y = 0; y < 128; y++) for (let x = 0; x < 128; x++) {
    const value = 100 + (((x * 73856093) ^ (y * 19349663) ^ (x * y * 83492791)) >>> 0) % 58;
    pixels.set([value, value, value, 255], (y * 128 + x) * 4);
  }
  const texture = new THREE.DataTexture(pixels, 128, 128, THREE.RGBAFormat);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(22, 14); texture.needsUpdate = true;
  return texture;
}

/** The arena retains its physical top rectangle; studio architecture lies outside it. */
export function createWorldScene(): THREE.Group {
  const world = new THREE.Group();
  const grain = stageGrain();
  const rubber = new THREE.MeshStandardMaterial({color:"#030507",roughness:.96,metalness:.04,bumpMap:grain,bumpScale:.008});
  const edge = new THREE.MeshStandardMaterial({color:"#080c11",roughness:.78,metalness:.18});
  const wall = new THREE.MeshStandardMaterial({color:"#0b141c",roughness:.86,bumpMap:grain,bumpScale:.012});
  const ribs = new THREE.MeshStandardMaterial({color:"#15212b",roughness:.6,metalness:.4});
  const trim = new THREE.MeshStandardMaterial({color:"#455963",roughness:.4,metalness:.65});
  const black = new THREE.MeshStandardMaterial({color:"#030609",roughness:.96});
  const cyan = new THREE.MeshStandardMaterial({color:"#05383e",emissive:"#23aebd",emissiveIntensity:1.15,roughness:.5});
  const softbox = new THREE.MeshStandardMaterial({color:"#d7d6c8",emissive:"#e5e8e4",emissiveIntensity:2.0,roughness:.8});
  function box(name:string,size:[number,number,number],at:[number,number,number],material:THREE.Material):THREE.Mesh {
    const mesh=new THREE.Mesh(new THREE.BoxGeometry(...size),material);
    mesh.name=name; mesh.position.set(...at); mesh.castShadow=true;mesh.receiveShadow=true;world.add(mesh);return mesh;
  }
  box("physical-arena",[20,.6,12],[0,-.3,0],rubber);
  box("arena-plinth",[21,.7,13],[0,-.95,0],edge);
  // A low-contrast tile grid adds real scale without inventing physical obstacles.
  for(let x=-8;x<=8;x+=2)box("rubber-tile-seam",[.012,.002,12],[x,.001,0],black);
  for(let z=-4;z<=4;z+=2)box("rubber-tile-seam",[20,.002,.012],[0,.001,z],black);
  for(const z of [-6.08,6.08])box("arena-marking",[20.3,.08,.10],[0,.04,z],trim);
  for(const x of [-10.08,10.08])box("arena-marking",[.10,.08,12],[x,.04,0],trim);
  const ticks=new THREE.InstancedMesh(new THREE.BoxGeometry(.025,.008,.22),trim,38);
  const transform=new THREE.Matrix4();let index=0;
  for(const z of [-5.83,5.83])for(let x=-9;x<=9;x++)ticks.setMatrixAt(index++,transform.makeTranslation(x,.005,z));
  ticks.name="arena-marking";world.add(ticks);

  // Authored set dressing is outside the 20x12 simulated ground. It supplies
  // depth and light sources, and is neither a collision mesh nor new equipment.
  for(const side of [-1,1]) {
    const z=side*8.3;
    box("studio-back-wall",[27,8,.25],[0,2.6,z],wall);
    box("studio-wall-foot",[27,.3,.4],[0,-1.0,z-side*.12],black);
    for(let x=-12;x<=12;x+=3) {
      box("studio-wall-rib",[.12,7.7,.22],[x,2.6,z-side*.23],ribs);
      if(x%6===0) {
        box("studio-recess",[.16,2.8,.04],[x+.30,2.0,z-side*.18],black);
        box("studio-cyan-strip",[.022,2.5,.018],[x+.30,2.0,z-side*.205],cyan);
      }
    }
    for(const y of [.15,3.8])box("studio-horizontal-reveal",[27,.025,.08],[0,y,z-side*.20],black);
  }
  for(const x of [-11.7,11.7]) {
    box("studio-side-column",[.4,7,.45],[x,2.1,0],ribs);
    box("studio-side-beam",[.25,.25,17],[x,5.6,0],edge);
  }
  for(const x of [-7,0,7])for(const z of [-2.6,2.6]) {
    box("studio-light-housing",[3.2,.12,.65],[x,5.55,z],black);
    const panel=box("studio-softbox",[3.0,.015,.48],[x,5.48,z],softbox);panel.castShadow=false;
  }
  const surround=new THREE.Mesh(new THREE.PlaneGeometry(120,120),black);
  surround.name="studio-surround";surround.rotation.x=-Math.PI/2;surround.position.y=-1.35;surround.receiveShadow=true;world.add(surround);
  const batches=new Map<THREE.Material,THREE.Mesh[]>();
  for(const node of [...world.children]) {
    if(!(node instanceof THREE.Mesh) || node instanceof THREE.InstancedMesh || node.name==="arena-marking")continue;
    const material=node.material as THREE.Material,batch=batches.get(material)??[];batch.push(node);batches.set(material,batch);
  }
  for(const [material,meshes] of batches){
    const copies=meshes.map(mesh=>{mesh.updateMatrix();return mesh.geometry.clone().applyMatrix4(mesh.matrix);});
    const merged=mergeGeometries(copies);if(!merged)throw new Error("Studio static geometry could not be batched");
    copies.forEach(copy=>copy.dispose());
    const mesh=new THREE.Mesh(merged,material);mesh.name="authored-studio-batch";
    mesh.userData.features=meshes.map(node=>node.name);mesh.castShadow=true;mesh.receiveShadow=true;
    meshes.forEach(node=>{world.remove(node);node.geometry.dispose();});world.add(mesh);
  }
  world.userData.source="DrosoLift original procedural studio v2; decoration outside physical 20x12 arena";
  return world;
}

export function lightWorld(scene:THREE.Scene):void {
  scene.background=new THREE.Color("#050a10");
  scene.fog=new THREE.Fog("#050a10",14,42);
  scene.add(new THREE.HemisphereLight("#b7c7cf","#131012",.33));
  const key=new THREE.DirectionalLight("#ffe7c7",2.35);
  key.position.set(-3,12,-5);key.castShadow=true;
  key.shadow.mapSize.set(2048,2048);
  Object.assign(key.shadow.camera,{left:-16,right:16,top:14,bottom:-14,near:1,far:50});
  key.shadow.normalBias=.016;key.shadow.bias=-.00008;scene.add(key);
  const rim=new THREE.DirectionalLight("#b6d4e9",1.35);rim.position.set(3,6,8);scene.add(rim);
  const fill=new THREE.DirectionalLight("#6ba0b0",.48);fill.position.set(10,4,-7);scene.add(fill);
  const stripBounce=new THREE.PointLight("#20b8c8",2.3,18,2);stripBounce.position.set(-7,2.3,6.7);scene.add(stripBounce);
}
