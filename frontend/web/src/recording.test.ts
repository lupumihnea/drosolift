import {expect,test} from "bun:test";
import {parseRecording} from "./recording";

test("recorded apparatus inputs remain on the same sampled model clock",async()=>{
  const document=await Bun.file(new URL("../public/samples/bench.json",import.meta.url)).json();
  const source={...document,metadata:{...document.metadata,control_history:[{type:"control_state",protocol:1,run_id:document.metadata.run_id,step:0,elapsed:0,loads:[],feedback:[{fly_id:"fly-1",profile:"apparatus-visual-v1",indicator_left:0,indicator_right:0,sample_step:0,sample_elapsed:0}]}]}};
  const parsed=parseRecording(source);expect(parsed.frames.length).toBe(201);expect(parsed.controls[0]!.feedback![0]!.indicator_left).toBe(0);
  const invalid=structuredClone(source);invalid.metadata.control_history[0].feedback[0].sample_step=5;
  expect(()=>parseRecording(invalid)).toThrow();
  const duplicate=structuredClone(source);duplicate.frames[1].elapsed=duplicate.frames[0].elapsed;
  expect(()=>parseRecording(duplicate)).toThrow();
});

test("both shipped exercise scenarios retain actual latched inputs and distinct source visual rates",async()=>{
  const bench=parseRecording(await Bun.file(new URL("../public/samples/demo-bench.json",import.meta.url)).json());
  const curl=parseRecording(await Bun.file(new URL("../public/samples/demo-curl.json",import.meta.url)).json());
  for(const recording of [bench,curl]){
    expect(recording.frames.length).toBe(201);expect(recording.controls.length).toBe(201);
    expect(recording.metadata.feedback_profile).toBe("apparatus-visual-v1");
    for(let i=1;i<recording.frames.length;i++){
      const frame=recording.frames[i]!,control=recording.controls[i]!;
      expect(control.step).toBe(frame.step);expect(control.elapsed).toBe(frame.elapsed);
      expect(control.feedback![0]!.sample_step).toBe(frame.step);
    }
  }
  const b=bench.frames[30]!.flies[0]!.frame.neural.active,c=curl.frames[30]!.flies[0]!.frame.neural.active;
  expect(b.find(n=>n.body_id===36800)!.activity).toBeGreaterThan(b.find(n=>n.body_id===63316)!.activity);
  expect(c.find(n=>n.body_id===63316)!.activity).toBeGreaterThan(c.find(n=>n.body_id===36800)!.activity);
});
