import { NormalBlending, BufferGeometry, Color, Float32BufferAttribute, Group, LineBasicMaterial, LineSegments, Points, type DataTexture, type PointsMaterial } from "three/webgpu";
import type { ActiveNeuron } from "./types";
import {activityAppearance,GROUP_BY_BODY,type NeuralGroupId} from "./neural-activity";
import {neuralGlowTexture,neuralPointMaterial} from "./neural-sprites";
import {brainCropIncludes,cellGroupColor} from "./neural-history";

type SWCNode = [number, number, number, number, number, number, number];
interface AtlasTransform {center:[number,number,number];scale:number;display_y_sign:-1}
interface Skeleton {body_id:number;sha256:string;nodes:SWCNode[]}
interface SkeletonCache {schema:1;dataset:"male-cns:v1.0";coordinate_units_nm:8;transform:AtlasTransform;skeletons:Skeleton[]}
const SOURCES: Record<number,string> = {
  10783:"b702c072f0a2ae0ce5531e14a4b7e197f8d13b39ac864ad7fa2c601d129e0d50",
  11177:"df374c15104b8ed60c454a1f4f21d352da0ed2c21d4a33055d89c391d068ae16",
  36800:"d2cffd75c247833252b3f9ce71f59827bfe9fff3d032a70e13d8f166b8cfcdd1",
  63316:"ecfac3f0cedfdf5a7a7b50f01194ec0df97c065f48d10c02f887764bbd635075",
  201965:"56efbce74bbde158d5e037ebe837fc3a1449d209a889cfe5278934474247e7c2",
  80841:"92b82db8cd96d23eb81299b42a0af1dadc56faafc23f2b7f960f2669c868f396",
  10702:"1dd54734c3e9edd9cb5bca7a1dd76d2d4539a5c8b44e47dabdeb36e2a3466f97",
  67052:"f83d5c4c6dd69922fc6cd9d20e9947f305bb4abbb4fd477c92ff93822ceafb2c",
};

/** Fail closed on malformed or unversioned morphology; never substitute authored branches. */
export function parseSkeletonCache(value: unknown): SkeletonCache {
  if (!value || typeof value !== "object") throw new Error("Missing skeleton cache");
  const record=value as Record<string,unknown>;
  const transform=record.transform as AtlasTransform | undefined;
  if(record.schema!==1 || record.dataset!=="male-cns:v1.0" || record.coordinate_units_nm!==8 ||
    !transform || !Array.isArray(transform.center) || transform.center.length!==3 ||
    !transform.center.every(Number.isFinite) || !Number.isFinite(transform.scale) || transform.scale<=0 ||
    transform.display_y_sign!==-1 || !Array.isArray(record.skeletons) || record.skeletons.length>8) {
    throw new Error("Incompatible skeleton provenance or transform");
  }
  const bodies=new Set<number>();
  for(const item of record.skeletons as Skeleton[]) {
    if(!item || !Number.isSafeInteger(item.body_id) || bodies.has(item.body_id) || SOURCES[item.body_id]!==item.sha256 ||
      !Array.isArray(item.nodes) || item.nodes.length>20000) throw new Error("Unverified skeleton source");
    bodies.add(item.body_id);
    const ids=new Set<number>();
    for(const node of item.nodes) {
      if(!Array.isArray(node) || node.length!==7 || !Number.isSafeInteger(node[0]) || node[0]<=0 ||
        ids.has(node[0]) || !node.every(v=>typeof v==="number" && Number.isFinite(v) && Math.abs(v)<=1e8) ||
        !Number.isSafeInteger(node[6]) || node[5]<0) throw new Error("Malformed skeleton node");
      ids.add(node[0]);
    }
    for(const node of item.nodes) if(node[6]!==-1 && (!ids.has(node[6]) || node[6]===node[0])) throw new Error("Broken skeleton parent");
  }
  return record as unknown as SkeletonCache;
}

/** Exact parent edges in the same centered/scaled atlas frame as the soma overview. */
export function skeletonCoordinates(skeleton: Skeleton, transform: AtlasTransform): number[] {
  const nodes=new Map(skeleton.nodes.map(node=>[node[0],node]));
  const result:number[]=[];
  for(const node of skeleton.nodes) {
    if(node[6]===-1) continue;
    const parent=nodes.get(node[6])!;
    for(const endpoint of [parent,node]) {
      for(let axis=0;axis<3;axis++) {
        const value=(endpoint[axis+2]!-transform.center[axis]!)*transform.scale;
        result.push(axis===1 ? -value : value);
      }
    }
  }
  return result;
}

/** Public selected SWCs, with no within-body registration and no invented edges. */
export async function createSkeletonGroup(texture:DataTexture=neuralGlowTexture()): Promise<Group> {
  const response=await fetch(`${import.meta.env.BASE_URL}assets/selected-skeletons.json`);
  if(!response.ok) throw new Error("Selected morphology unavailable");
  const cache=parseSkeletonCache(await response.json());
  const group=new Group();group.name="MaleCNS-native-skeletons";
  group.userData={dataset:cache.dataset,coordinate_units_nm:8,registration:"native MaleCNS atlas; same soma normalization; display Y inverted",source:"selected-skeletons.json"};
  for(const skeleton of cache.skeletons) {
    const source=skeletonCoordinates(skeleton,cache.transform),brain:number[]=[],rest:number[]=[];
    for(let index=0;index<source.length;index+=6){const segment=source.slice(index,index+6);
      (brainCropIncludes(segment)&&brainCropIncludes(segment.slice(3))?brain:rest).push(...segment);}
    const geometry=new BufferGeometry().setAttribute("position",new Float32BufferAttribute([...brain,...rest],3));
    const line=new LineSegments(geometry,new LineBasicMaterial({color:"#456066",transparent:true,opacity:.38,depthWrite:false,depthTest:false,blending:NormalBlending,toneMapped:false}));
    line.name=`body-${skeleton.body_id}`;line.userData={body_id:skeleton.body_id,sha256:skeleton.sha256,brainVertexCount:brain.length/3};
    group.add(line);
    const step=Math.max(1,Math.ceil(skeleton.nodes.length/1800)),samples:number[]=[];
    for(let index=0;index<skeleton.nodes.length;index+=step){const node=skeleton.nodes[index]!;
      samples.push((node[2]-cache.transform.center[0])*cache.transform.scale,
        -(node[3]-cache.transform.center[1])*cache.transform.scale,(node[4]-cache.transform.center[2])*cache.transform.scale);}
    const brainSamples:number[]=[],otherSamples:number[]=[];
    for(let index=0;index<samples.length;index+=3){const point=samples.slice(index,index+3);(brainCropIncludes(point)?brainSamples:otherSamples).push(...point);}
    const glow=new Points(new BufferGeometry().setAttribute("position",new Float32BufferAttribute([...brainSamples,...otherSamples],3)),neuralPointMaterial(texture,.046,.5,false));
    glow.name=`body-${skeleton.body_id}-glow`;glow.userData={body_id:skeleton.body_id,sha256:skeleton.sha256,layer:"morphology-glow",brainVertexCount:brainSamples.length/3};glow.renderOrder=3;group.add(glow);
  }
  updateSkeletonActivity(group,[]);
  return group;
}

/** Crop draw ranges only; all source coordinates and full parent-edge buffers remain intact. */
export function setSkeletonBrainCrop(group:Group,brainOnly:boolean):void{
  group.traverse(node=>{if(node instanceof LineSegments||node instanceof Points){
    node.geometry.setDrawRange(0,brainOnly?node.userData.brainVertexCount:Infinity);
  }});
}

/** Rate-colored static branches; absent observations and received zeros stay distinct. */
export function updateSkeletonActivity(group: Group, readings: readonly ActiveNeuron[],focus:NeuralGroupId|null=null,colorMode:"activity"|"cell-colors"="activity"): void {
  const byId=new Map(readings.map(reading=>[reading.body_id,reading]));
  group.traverse(node=>{
    if(!(node instanceof LineSegments || node instanceof Points)) return;
    const reading=byId.get(node.userData.body_id);
    const material=node.material as LineBasicMaterial|PointsMaterial;
    const activity=reading?.activity;
    const observed=activity!==undefined;
    const positive=observed && activity>0;
    const appearance=activityAppearance(activity);
    material.color.copy(new Color().fromArray(colorMode==="cell-colors"?cellGroupColor(node.userData.body_id):appearance.color));
    const emphasis=(focus&&GROUP_BY_BODY.get(node.userData.body_id)!==focus) ? .06 : 1;
    material.opacity=(node instanceof Points ? .42 : .62)*(colorMode==="cell-colors"?.66:appearance.intensity)*emphasis;
    node.userData.observation=positive ? "positive" : observed ? "zero" : "unobserved";
    node.userData.activity=activity ?? null;
  });
}
