import type { ActiveNeuron } from "./types";
import type { ExerciseKind } from "./gym-types";

export interface ExerciseSetup {fly_id:string;kind:ExerciseKind|null;station_id:string|null;pending_kind:ExerciseKind|null;pending_station_id:string|null;pending_command_id:string|null}
export interface ApparatusFeedback {fly_id:string;profile:"none"|"apparatus-visual-v1";indicator_left:number;indicator_right:number;sample_step:number;sample_elapsed:number}
export interface ControlState {type:"control_state";protocol:1;run_id:string;step:number;elapsed:number;metadata?:Record<string,unknown>;loads:{station_id:string;load:number;pending_load:number|null;pending_command_id:string|null}[];exercises?:ExerciseSetup[];feedback?:ApparatusFeedback[]}
export interface CommandAck {type:"command_ack";command_id:string;command:"set_load"|"set_running"|"set_exercise";status:"pending"|"applied";effective_step:number|null;run_id:string}
export type ControlMessage = ControlState | CommandAck;
const finite = (x:unknown):x is number => typeof x === "number" && Number.isFinite(x);
const step = (x:unknown):x is number => finite(x) && Number.isSafeInteger(x) && x >= 0;
const id = (x:unknown):x is string => typeof x === "string" && x.length > 0 && x.length <= 128;
const kind=(x:unknown):x is ExerciseKind=>x==="bench_press"||x==="bicep_curl";
const station=(x:unknown):x is string=>typeof x==="string"&&/^station-([1-9]|10)$/.test(x);
const fly=(x:unknown):x is string=>typeof x==="string"&&/^fly-([1-9]|10)$/.test(x);
/** Extensions are negotiated; strict upstream schema-1/2/3 messages stay unchanged. */
export function parseControlMessage(value: unknown): ControlMessage {
  if (!value || typeof value !== "object") throw new Error("Invalid controls");
  const m = value as Record<string,unknown>;
  if (!id(m.run_id)) throw new Error("Missing run identity");
  if (m.type === "command_ack" && id(m.command_id) && ["set_load","set_running","set_exercise"].includes(String(m.command)) &&
      ["pending","applied"].includes(String(m.status)) && (m.status === "pending" ? m.effective_step === null : step(m.effective_step))) return m as unknown as CommandAck;
  if (m.type === "control_state" && m.protocol === 1 && step(m.step) && finite(m.elapsed) && m.elapsed >= 0 && Array.isArray(m.loads) && m.loads.length <= 10) {
    const seen = new Set<string>();
    for (const row of m.loads) {
      if (!row || typeof row !== "object" || !/^station-([1-9]|10)$/.test(row.station_id) || seen.has(row.station_id) ||
          !finite(row.load) || row.load < .1 || row.load > 3 ||
          (row.pending_load !== null && (!finite(row.pending_load) || row.pending_load < .1 || row.pending_load > 3)) ||
          (row.pending_command_id !== null && !id(row.pending_command_id))) throw new Error("Invalid load state");
      seen.add(row.station_id);
    }
    if(m.exercises!==undefined){
      if(!Array.isArray(m.exercises)||m.exercises.length>10)throw new Error("Invalid exercise setup");
      const seenFlies=new Set<string>();
      for(const row of m.exercises){
        if(!row||!fly(row.fly_id)||seenFlies.has(row.fly_id)||
          (row.kind!==null&&!kind(row.kind))||(row.station_id!==null&&!station(row.station_id))||
          ((row.kind===null)!==(row.station_id===null))||
          (row.pending_kind!==null&&!kind(row.pending_kind))||(row.pending_station_id!==null&&!station(row.pending_station_id))||
          (row.pending_command_id!==null&&!id(row.pending_command_id))||
          ((row.pending_kind===null)!==(row.pending_station_id===null))||
          ((row.pending_kind===null)!==(row.pending_command_id===null)))throw new Error("Invalid exercise setup");
        seenFlies.add(row.fly_id);
      }
    }
    if(m.feedback!==undefined){
      if(!Array.isArray(m.feedback)||m.feedback.length>10)throw new Error("Invalid apparatus feedback");
      const seenFlies=new Set<string>();
      for(const row of m.feedback){
        if(!row||!fly(row.fly_id)||seenFlies.has(row.fly_id)||!["none","apparatus-visual-v1"].includes(row.profile)||
          !finite(row.indicator_left)||row.indicator_left<0||row.indicator_left>1||
          !finite(row.indicator_right)||row.indicator_right<0||row.indicator_right>1||
          !step(row.sample_step)||row.sample_step>m.step||!finite(row.sample_elapsed)||row.sample_elapsed<0||row.sample_elapsed>m.elapsed+1e-8)throw new Error("Invalid apparatus feedback");
        seenFlies.add(row.fly_id);
      }
    }
    return m as unknown as ControlState;
  }
  throw new Error("Invalid control response");
}

/** Replay samples are exact left-continuous states; only the visual pose may smooth. */
export function sampleAt<T extends {elapsed:number}>(frames: readonly T[], time: number): T {
  if (!frames.length || !Number.isFinite(time)) throw new Error("Invalid playhead");
  let low=0,high=frames.length-1;
  while(low<high){const mid=Math.ceil((low+high)/2);if(frames[mid]!.elapsed<=time)low=mid;else high=mid-1;}
  return frames[low]!;
}
export class NeuronHistory {
  selectedId:number|null=null;
  samples:{time:number;value:number|null}[]=[];
  select(id:number):void {if(this.selectedId!==id){this.selectedId=id;this.samples=[];}}
  record(time:number, readings:readonly ActiveNeuron[]):void {
    if(this.selectedId===null && readings.length)this.select(readings[0]!.body_id);
    if(time < (this.samples.at(-1)?.time ?? -Infinity))this.samples=[];
    if(time === this.samples.at(-1)?.time)return;
    this.samples.push({time,value:readings.find(n=>n.body_id===this.selectedId)?.activity ?? null});
    if(this.samples.length>300)this.samples.shift();
  }
}
