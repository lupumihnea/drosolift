import { expect, test } from "bun:test";
import { parseControlMessage, sampleAt, NeuronHistory } from "./observatory-state";

test("load acknowledgements reject non-finite state and distinguish pending from effective steps", () => {
  expect(parseControlMessage({type:"command_ack", command_id:"a", command:"set_load", status:"pending", effective_step:null, run_id:"run"}).type).toBe("command_ack");
  expect(() => parseControlMessage({type:"command_ack", command_id:"a", command:"set_load", status:"applied", effective_step:null, run_id:"run"})).toThrow();
  expect(() => parseControlMessage({type:"control_state", protocol:1, run_id:"r", step:1, elapsed:NaN, loads:[]})).toThrow();
});
test("seeking selects the recorded state without inventing counts or interpolating telemetry", () => {
  const frames = [{elapsed:0,step:0},{elapsed:.1,step:1},{elapsed:.2,step:2}];
  expect(sampleAt(frames,.199)).toBe(frames[1]!);
  expect(sampleAt(frames,.2)).toBe(frames[2]!);
  expect(sampleAt(frames,-1)).toBe(frames[0]!);
  expect(sampleAt(frames,100)).toBe(frames[2]!);
});
test("selection follows identity across ranking changes and missing observations stay missing", () => {
  const history = new NeuronHistory();
  history.select(123);
  history.record(1,[{body_id:123,label:"selected",activity:0},{body_id:456,label:"other",activity:1}]);
  history.record(2,[{body_id:456,label:"other",activity:2},{body_id:123,label:"selected",activity:1e-12}]);
  history.record(3,[{body_id:456,label:"other",activity:2}]);
  expect(history.selectedId).toBe(123);
  expect(history.samples.map(p=>p.value)).toEqual([0,1e-12,null]);
  history.record(3,[{body_id:456,label:"other",activity:2}]);
  expect(history.samples.length).toBe(3);
  history.record(0,[{body_id:123,label:"selected",activity:0}]);
  expect(history.samples.length).toBe(1);
});

test("exercise setup and latched apparatus feedback preserve their exact acknowledged clock",()=>{
  const message={type:"control_state",protocol:1,run_id:"run",step:12,elapsed:1.2,loads:[],
    exercises:[{fly_id:"fly-1",kind:"bench_press",station_id:"station-1",pending_kind:"bicep_curl",pending_station_id:"station-2",pending_command_id:"change"}],
    feedback:[{fly_id:"fly-1",profile:"apparatus-visual-v1",indicator_left:.8,indicator_right:0,sample_step:12,sample_elapsed:1.2}]};
  const parsed=parseControlMessage(message);expect(parsed.type).toBe("control_state");
  if(parsed.type==="control_state")expect(parsed.feedback?.[0]?.indicator_right).toBe(0);
  expect(parseControlMessage({type:"command_ack",command_id:"change",command:"set_exercise",status:"applied",effective_step:13,run_id:"run"}).type).toBe("command_ack");
  expect(()=>parseControlMessage({...message,feedback:[{...message.feedback[0],indicator_left:NaN}]})).toThrow();
  expect(()=>parseControlMessage({...message,feedback:[{...message.feedback[0],sample_step:13}]})).toThrow();
  expect(()=>parseControlMessage({...message,exercises:[{...message.exercises[0],kind:"invented"}]})).toThrow();
  expect(()=>parseControlMessage({...message,feedback:[message.feedback[0],message.feedback[0]]})).toThrow();
});
