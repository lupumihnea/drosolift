import {GROUP_BY_BODY,NEURAL_GROUPS} from "./neural-activity";
import type {ActiveNeuron} from "./types";
export {rateColor} from "./neural-activity";

/** Authored observer crop in normalized native atlas Z; not an official anatomical ROI. */
export const BRAIN_CROP_Z=-.28;
export function brainCropIncludes(position:readonly number[]):boolean{return position[2]!<=BRAIN_CROP_Z;}

function linear(value:number):number{return value<=.04045?value/12.92:Math.pow((value+.055)/1.055,2.4);}
export function cellGroupColor(bodyId:number):[number,number,number]{
  const hex=NEURAL_GROUPS.find(group=>group.id===GROUP_BY_BODY.get(bodyId))?.color??"#426888";
  return [1,3,5].map(index=>linear(parseInt(hex.slice(index,index+2),16)/255)) as [number,number,number];
}

/** Received samples only. A repeated timestamp replaces its column; a backward seek clears it. */
export class NeuralRateHistory{
  readonly samples:{time:number;values:Map<number,number>}[]=[];
  constructor(readonly capacity=96){}
  record(time:number,readings:readonly ActiveNeuron[]):void{
    if(!Number.isFinite(time))return;
    if(time<(this.samples.at(-1)?.time??-Infinity))this.clear();
    const sample={time,values:new Map(readings.map(reading=>[reading.body_id,reading.activity]))};
    if(time===this.samples.at(-1)?.time)this.samples[this.samples.length-1]=sample;
    else this.samples.push(sample);
    if(this.samples.length>this.capacity)this.samples.splice(0,this.samples.length-this.capacity);
  }
  clear():void{this.samples.length=0;}
}
