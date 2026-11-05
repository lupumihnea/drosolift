import runtime from "../../../data/circuits/gym-v1-runtime.json";
import type { ActiveNeuron } from "./types";

export const NEURAL_RUNTIME = runtime;
export type NeuralGroupId = "visual-left"|"visual-right"|"gym-cue"|"food-odor"|"descending"|"relay";
export interface NeuralGroup {id:NeuralGroupId;label:string;detail:string;ids:number[];color:string}
const input = runtime.sensory_inputs;
const motor=[...new Set(Object.values(runtime.motor_roles))].sort((a,b)=>a-b);
const ids=[...new Set(runtime.edges.flatMap(edge=>[edge.body_pre,edge.body_post]))].sort((a,b)=>a-b);
const sensory=[...input.vision_left,...input.vision_right,...input.gym_left,...input.gym_right,...input.smell_left,...input.smell_right];
const assigned=new Set([...sensory,...motor]);

/** These are model input/readout groups, not claims of exercise-specific brain regions. */
export const NEURAL_GROUPS:readonly NeuralGroup[] = [
  {id:"visual-left",label:"Visual L · L2",detail:"Official L2 cells assigned to the model's left visual input",ids:input.vision_left,color:"#5be9ed"},
  {id:"visual-right",label:"Visual R · L2",detail:"Official L2 cells assigned to the model's right visual input",ids:input.vision_right,color:"#72b6ff"},
  {id:"gym-cue",label:"Gym cue · DM2",detail:"Official ORN_DM2 cells receiving the synthetic apparatus odor cue",ids:[...input.gym_left,...input.gym_right],color:"#efbd7c"},
  {id:"food-odor",label:"Food odor · DM1",detail:"Official ORN_DM1 cells receiving the existing food odor input",ids:[...input.smell_left,...input.smell_right],color:"#cb96ed"},
  {id:"descending",label:"Descending output",detail:"Official descending cells used by the engineered motor readout",ids:motor,color:"#ff977e"},
  {id:"relay",label:"Compact relays",detail:"Remaining official runtime cells connected by the pinned structural edges",ids:ids.filter(id=>!assigned.has(id)),color:"#67d6b9"},
];
export const GROUP_BY_BODY = new Map(NEURAL_GROUPS.flatMap(group=>group.ids.map(id=>[id,group.id] as const)));

export function summarizeGroups(readings:readonly ActiveNeuron[]){
  const received=new Map(readings.map(reading=>[reading.body_id,reading.activity]));
  return NEURAL_GROUPS.map(group=>{
    const values=group.ids.flatMap(id=>received.has(id)?[received.get(id)!]:[]);
    return {...group,total:group.ids.length,observed:values.length,positive:values.filter(value=>value>0).length,
      mean:values.length?values.reduce((sum,value)=>sum+value,0)/values.length:null,
      maximum:values.length?Math.max(...values):null};
  });
}

/** Static rate transfer, not an event or temporal pulse. Exact values stay in the inspector. */
export function rateColor(value:number):[number,number,number]{
  const amount=Math.sqrt(Math.max(0,Math.min(1,value)));
  return [.015+.97*amount*amount,.45+.50*amount,.02+.95*(1-amount)];
}
export interface ActivityAppearance {observation:"unobserved"|"zero"|"positive";intensity:number;color:readonly[number,number,number]}
export function activityAppearance(value:number|undefined):ActivityAppearance{
  if(value===undefined || !Number.isFinite(value))return{observation:"unobserved" as const,intensity:.035,color:[.025,.08,.16] as const};
  if(value===0)return{observation:"zero" as const,intensity:.14,color:[.02,.26,.5] as const};
  const amount=Math.sqrt(Math.max(0,Math.min(1,value)));
  return{observation:"positive" as const,intensity:.16+.84*amount,
    color:rateColor(value)};
}

export interface NeuralLink {pre:number;post:number;weight:number;from:readonly number[];to:readonly number[]}
/** Straight soma-to-soma structural links, not measured neurite trajectories. */
export function atlasConnections(positions:ReadonlyMap<number,readonly number[]>):NeuralLink[]{
  return runtime.edges.flatMap(edge=>{
    const from=positions.get(edge.body_pre),to=positions.get(edge.body_post);
    return from&&to?[{pre:edge.body_pre,post:edge.body_post,weight:edge.weight,from,to}]:[];
  });
}

/** Stable layered circuit arrangement; no authored coordinate enters the atlas. */
export function circuitLayout(){
  const layers=new Map<number,number>(sensory.map(id=>[id,0]));
  for(let pass=0;pass<5;pass++)for(const edge of runtime.edges){
    const pre=layers.get(edge.body_pre);
    if(pre!==undefined){const candidate=Math.min(4,pre+1);if(!layers.has(edge.body_post)||candidate<layers.get(edge.body_post)!)layers.set(edge.body_post,candidate);}
  }
  for(const id of motor)layers.set(id,5);
  const positions=new Map<number,readonly number[]>();
  for(let layer=0;layer<=5;layer++){
    const cells=ids.filter(id=>(layers.get(id)??2)===layer);
    cells.forEach((id,index)=>positions.set(id,[cells.length===1?0:(index/(cells.length-1)-.5)*2.35,1.05-layer*.42,0]));
  }
  return{registration:"authored circuit layout; not atlas anatomy" as const,positions};
}
