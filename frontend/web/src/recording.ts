import type {GymFrame} from "./gym-types";
import type {HelloMessage} from "./types";
import {parseControlMessage,type ControlState} from "./observatory-state";
import {parseServerMessage} from "./snapshot";

export interface Recording {metadata:Record<string,unknown>;hello:HelloMessage;frames:GymFrame[];controls:ControlState[]}

/** Recorded geometry, rate values and apparatus inputs share one exact model clock. */
export function parseRecording(value:unknown):Recording{
  if(!value||typeof value!=="object")throw new Error("Missing recording");
  const source=value as Record<string,unknown>;
  if(source.format!=="drosolift-recording"||source.version!==1||!Array.isArray(source.frames)||!source.frames.length||source.frames.length>36001)throw new Error("Incompatible recording");
  const hello=parseServerMessage(source.hello);if(hello.type!=="hello")throw new Error("Missing recorded hello");
  const frames=source.frames.map(value=>{const frame=parseServerMessage(value);if(frame.type!=="gym_frame")throw new Error("Invalid recorded frame");return frame;});
  for(let index=0;index<frames.length;index++){
    const frame=frames[index]!;
    if(frame.step<0||frame.elapsed<0||(index>0&&(frame.step<=frames[index-1]!.step||frame.elapsed<=frames[index-1]!.elapsed)))throw new Error("Invalid recording clock");
    for(const fly of frame.flies)if(new Set(fly.frame.neural.active.map(n=>n.body_id)).size!==fly.frame.neural.active.length)throw new Error("Duplicate recorded neuron identity");
  }
  const metadata=source.metadata&&typeof source.metadata==="object"?source.metadata as Record<string,unknown>:{};
  const controls:ControlState[]=[];
  if(metadata.control_history!==undefined){
    if(!Array.isArray(metadata.control_history)||metadata.control_history.length>36001)throw new Error("Invalid recorded control history");
    for(const value of metadata.control_history){
      const control=parseControlMessage(value);if(control.type!=="control_state")continue;
      const previous=controls.at(-1);
      if(control.elapsed>frames.at(-1)!.elapsed+1e-8||(previous&&control.elapsed<previous.elapsed))throw new Error("Control history is outside its recorded clock");
      controls.push(control);
    }
  }
  return {metadata,hello,frames,controls};
}
