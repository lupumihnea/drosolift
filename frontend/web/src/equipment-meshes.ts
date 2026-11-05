import { BoxGeometry, CylinderGeometry, Group, Mesh, MeshStandardMaterial, MeshPhysicalMaterial, DataTexture, RGBAFormat, RepeatWrapping, LatheGeometry, Vector2, TorusGeometry, SphereGeometry, InstancedMesh, Matrix4, Color } from "three/webgpu";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import type { EquipmentStation } from "./gym-types";

type Triple=[number,number,number];
/** Authored support surface for the existing imposed 0.55-radian curl posture. */
export function curlSupportHeight(x:number):number{return .525+Math.tan(.55)*x;}
/** Original deterministic surface patterns; appearance is authored, not model data. */
function surfaceGrain(brushed:boolean):DataTexture {
  const size=128,pixels=new Uint8Array(size*size*4);
  for(let y=0;y<size;y++)for(let x=0;x<size;x++){
    const noise=(((x*73856093)^(y*19349663)^(x*y*83492791))>>>0)%47;
    const value=brushed ? 100+((x*29)%34)+noise*.20 : 100+noise;
    pixels.set([value,value,value,255],(y*size+x)*4);
  }
  const texture=new DataTexture(pixels,size,size,RGBAFormat);texture.wrapS=texture.wrapT=RepeatWrapping;
  texture.repeat.set(brushed?3:8,brushed?1:4);texture.needsUpdate=true;return texture;
}
export function equipmentMaterials(){
  const leather=surfaceGrain(false),brush=surfaceGrain(true);
  return {
    steel:new MeshStandardMaterial({color:"#a0aab0",metalness:.91,roughness:.29,bumpMap:brush,bumpScale:.0012}),
    iron:new MeshStandardMaterial({color:"#202830",metalness:.68,roughness:.36,bumpMap:leather,bumpScale:.0015}),
    rubber:new MeshStandardMaterial({color:"#080c10",roughness:.98,bumpMap:leather,bumpScale:.004}),
    bench:new MeshPhysicalMaterial({color:"#090d11",roughness:.67,metalness:.02,clearcoat:.12,clearcoatRoughness:.5,bumpMap:leather,bumpScale:.0035}),
    piping:new MeshStandardMaterial({color:"#374047",roughness:.74}),
    curl:new MeshStandardMaterial({color:"#29343b",roughness:.42,metalness:.65}),
  };
}
type Materials=ReturnType<typeof equipmentMaterials>;
function box(group:Group,size:Triple,at:Triple,material:MeshStandardMaterial,bevel=0):void{
  const geometry=bevel>0?new RoundedBoxGeometry(...size,2,Math.min(bevel,Math.min(...size)/2)):new BoxGeometry(...size);
  const mesh=new Mesh(geometry,material);mesh.position.set(...at);mesh.castShadow=true;mesh.receiveShadow=true;group.add(mesh);
}
function cylinder(group:Group,radius:number,length:number,at:Triple,material:MeshStandardMaterial,segments=48):void{
  const mesh=new Mesh(new CylinderGeometry(radius,radius,length,segments),material);
  mesh.rotation.x=Math.PI/2;mesh.position.set(...at);mesh.castShadow=true;mesh.receiveShadow=true;group.add(mesh);
}
function bolt(group:Group,at:Triple,material:MeshStandardMaterial):void{
  const mesh=new Mesh(new CylinderGeometry(.024,.024,.014,6),material);
  mesh.rotation.z=Math.PI/2;mesh.position.set(...at);mesh.castShadow=true;group.add(mesh);
}
function plate(group:Group,radius:number,thickness:number,z:number,material:MeshStandardMaterial):void{
  const r=radius,t=thickness/2,bevel=Math.min(.014,thickness*.35);
  const profile=[[.065,-t],[r-.018,-t],[r,-t+bevel],[r,t-bevel],[r-.018,t],[.065,t],[.065,-t]].map(([x,y])=>new Vector2(x!,y!));
  const mesh=new Mesh(new LatheGeometry(profile,64),material);mesh.rotation.x=Math.PI/2;mesh.position.z=z;mesh.castShadow=true;mesh.receiveShadow=true;group.add(mesh);
  for(const side of [-1,1]){
    const ridge=new Mesh(new TorusGeometry(r*.77,Math.min(.0045,thickness*.16),4,64),material);ridge.position.z=z+side*(t+.002);group.add(ridge);
  }
}
/** Static apparatus batches by material. Dynamic indicator meshes are added later. */
function consolidate(group:Group):void{
  const batches=new Map<MeshStandardMaterial,Mesh[]>();
  for(const child of [...group.children] as Mesh[]){const material=child.material as MeshStandardMaterial;const batch=batches.get(material)??[];batch.push(child);batches.set(material,batch);}
  for(const [material,meshes] of batches){
    const geometries=meshes.map(mesh=>{mesh.updateMatrix();return (mesh.geometry.index?mesh.geometry.toNonIndexed():mesh.geometry.clone()).applyMatrix4(mesh.matrix);});
    const combined=mergeGeometries(geometries);if(!combined)throw new Error("Equipment geometry could not be merged");
    geometries.forEach(geometry=>geometry.dispose());meshes.forEach(mesh=>{group.remove(mesh);mesh.geometry.dispose();});
    const mesh=new Mesh(combined,material);mesh.castShadow=true;mesh.receiveShadow=true;group.add(mesh);
  }
}
export function equipmentFrame(station:EquipmentStation,materials:Materials):Group{
  const frame=new Group();
  box(frame,[2.8,.035,2.8],[-.05,.006,0],materials.rubber,.045);
  if(station.kind==="bench_press"){
    box(frame,[1.94,.22,.82],[-.22,.49,0],materials.bench,.065);
    box(frame,[1.94,.055,.83],[-.22,.395,0],materials.piping,.024);
    for(const z of [-.344,.344]){
      box(frame,[1.68,.006,.008],[-.22,.598,z],materials.piping,.002);
      for(let i=0;i<24;i++)box(frame,[.011,.004,.014],[-1.02+i*.07,.600,z],materials.piping,.001);
    }
    box(frame,[1.60,.10,.16],[-.22,.31,0],materials.iron,.016);
    for(const x of [-.90,.43]){
      box(frame,[.13,.40,.13],[x,.23,0],materials.steel,.016);
      box(frame,[.45,.09,.88],[x,.065,0],materials.iron,.026);
      for(const z of [-.34,.34])box(frame,[.22,.065,.20],[x,.042,z],materials.rubber,.02);
      for(const z of [-.15,.15])bolt(frame,[x+.077,.21,z],materials.steel);
    }
    const top=.90+station.travel+.15;
    for(const z of [-1.15,1.15]){
      box(frame,[.11,top,.11],[.32,top/2,z],materials.steel,.012);
      box(frame,[.92,.10,.28],[.26,.065,z],materials.iron,.025);
      for(const x of [-.10,.60])box(frame,[.19,.055,.25],[x,.035,z],materials.rubber,.018);
      box(frame,[.34,.055,.17],[.28,.865,z],materials.iron,.013);
      box(frame,[.052,.14,.17],[.43,.895,z],materials.iron,.014);
      for(let y=.36;y<top-.15;y+=.14){
        const hole=new Mesh(new CylinderGeometry(.014,.014,.008,12),materials.rubber);hole.rotation.z=Math.PI/2;hole.position.set(.38,y,z);frame.add(hole);
      }
      bolt(frame,[.388,.20,z],materials.iron);bolt(frame,[.388,.31,z],materials.iron);
      box(frame,[.10,.09,.19],[.32,top+.02,z],materials.iron,.015);
    }
  }else{
    // Authored supports do not add force, obstacles or an exercise trajectory.
    box(frame,[1.12,.10,1.25],[-.14,.075,0],materials.iron,.05);
    for(const z of [-1.02,1.02]){
      const x=-.36,thickness=.055;
      const support=new Mesh(new RoundedBoxGeometry(.74,thickness,.34,2,.016),materials.rubber);
      support.rotation.z=.55;support.position.set(x,curlSupportHeight(x)-thickness/(2*Math.cos(.55)),z);
      support.castShadow=true;support.receiveShadow=true;frame.add(support);
      for(const postX of [-.56,-.16]){
        const height=curlSupportHeight(postX)-.055;
        box(frame,[.07,height,.22],[postX,height/2+.025,z],materials.steel,.012);
        box(frame,[.24,.05,.37],[postX,.043,z],materials.iron,.012);
      }
    }
    for(const z of [-.5,.5]){
      box(frame,[.12,.47,.12],[.45,.255,z],materials.steel,.012);
      box(frame,[.40,.07,.42],[.45,.49,z],materials.iron,.018);
      box(frame,[.55,.08,.46],[.45,.055,z],materials.iron,.026);
      box(frame,[.19,.07,.23],[.65,.51,z],materials.iron,.018);
      bolt(frame,[.519,.28,z],materials.iron);
    }
  }
  consolidate(frame);
  // Independent materials remain outside static batches; emission is set only
  // from received apparatus feedback. Neutral grey means unobserved.
  const lampY=station.kind==="bench_press"?.90+station.travel+.19:.55;
  const lampZ=station.kind==="bench_press"?1.15:.50;
  const lampX=station.kind==="bench_press"?.39:.67;
  for(const [index,name] of ["left","right"].entries()){
    const material=new MeshStandardMaterial({color:"#24313a",emissive:"#000000",emissiveIntensity:0,roughness:.24,metalness:.12});
    const lamp=new Mesh(new SphereGeometry(.034,16,10),material);lamp.name=`indicator-${name}`;
    lamp.position.set(lampX,lampY,index===0?-lampZ:lampZ);lamp.userData.observation="unobserved";frame.add(lamp);
  }
  return frame;
}
/** One disc per 0.2 applied model units, bounded to 15 per stack. Not a kg scale. */
export function visualPlateCount(load:number):number{
  if(!Number.isFinite(load)||load<=0)throw new Error("Invalid visual load");
  return Math.max(1,Math.min(15,Math.ceil((load-1e-9)/.2)));
}
interface WeightRig {kind:EquipmentStation["kind"];plates:InstancedMesh;collars:InstancedMesh;shafts:Mesh[];count:number}
const weightRigs=new WeakMap<Group,WeightRig>();
export interface WeightVisualization {load:number;platesPerStack:number;totalPlates:number;stacks:number}

export function equipmentWeight(station:EquipmentStation,materials:Materials):Group{
  const weights=new Group(),bench=station.kind==="bench_press";
  const template=new Group();plate(template,bench?.35:.185,bench?.025:.012,0,materials.iron);consolidate(template);
  const geometry=(template.children[0] as Mesh).geometry;
  const stacks=bench?2:4;
  const plates=new InstancedMesh(geometry,materials.iron,15*stacks);plates.name="applied-load-discs";
  plates.castShadow=true;plates.receiveShadow=true;plates.frustumCulled=false;weights.add(plates);
  const collars=new InstancedMesh(new CylinderGeometry(bench?.070:.055,bench?.070:.055,.045,12).rotateX(Math.PI/2),materials.steel,stacks);
  collars.name="applied-load-collars";collars.castShadow=true;collars.frustumCulled=false;weights.add(collars);
  const shafts:Mesh[]=[];
  for(const center of bench?[0]:[-.5,.5]){
    const shaft=new Mesh(new CylinderGeometry(.035,.035,1,32),materials.steel);
    shaft.rotation.x=Math.PI/2;shaft.position.z=center;shaft.name="load-bar-shaft";shaft.castShadow=true;weights.add(shaft);shafts.push(shaft);
    cylinder(weights,.038,bench?.27:.17,[0,0,bench?-.55:center],materials.iron);
    if(bench)cylinder(weights,.038,.27,[0,0,.55],materials.iron);
  }
  weightRigs.set(weights,{kind:station.kind,plates,collars,shafts,count:0});
  updateEquipmentLoad(weights,station.load);return weights;
}

/** Only the applied authoritative load changes the discs; joint/grip transforms stay outside this function. */
export function updateEquipmentLoad(weights:Group,load:number):WeightVisualization|undefined{
  const rig=weightRigs.get(weights);if(!rig||!Number.isFinite(load)||load<.1||load>3)return;
  const n=visualPlateCount(load),bench=rig.kind==="bench_press",stacks=bench?2:4;
  const inner=bench?1.19:.17,pitch=bench?.032:.017,thickness=bench?.025:.012;
  const outer=inner+(n-1)*pitch+thickness/2;
  const matrix=new Matrix4(),color=new Color();let index=0;
  for(let i=0;i<n;i++)for(const center of bench?[0]:[-.5,.5])for(const side of [-1,1]){
    rig.plates.setMatrixAt(index,matrix.makeTranslation(0,0,center+side*(inner+i*pitch)));
    color.set(i%2===0?"#879ba7":"#596f80");rig.plates.setColorAt(index,color);index++;
  }
  rig.plates.count=index;rig.plates.instanceMatrix.needsUpdate=true;if(rig.plates.instanceColor)rig.plates.instanceColor.needsUpdate=true;
  let collar=0;
  for(const center of bench?[0]:[-.5,.5])for(const side of [-1,1])rig.collars.setMatrixAt(collar++,matrix.makeTranslation(0,0,center+side*(outer+.032)));
  rig.collars.instanceMatrix.needsUpdate=true;
  for(const shaft of rig.shafts)shaft.scale.y=2*(outer+.085);
  rig.count=n;
  const state={load,platesPerStack:n,totalPlates:index,stacks};
  Object.assign(weights.userData,state,{calibration:"one disc per 0.2 applied virtual force units per stack; ceil(load/0.2), capped at15; not kilograms"});
  return state;
}
