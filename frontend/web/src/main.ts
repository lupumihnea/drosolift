import "./drosolift.css";
import "./demo-polish.css";
import "./training-ui.css";

import { Dashboard } from "./dashboard";
import { GymDashboard } from "./gym-dashboard";
import type { NeuronMap } from "./neuron-map";
import type { GymFrame,ExerciseKind } from "./gym-types";
import type { FlyScene } from "./fly-scene";
import type { CameraMode } from "./scene-camera";
import { SimulationClient } from "./simulation-client";
import type { FrameMessage, HelloMessage } from "./types";
import { NeuronHistory, sampleAt, type ControlMessage, type ControlState } from "./observatory-state";
import { parseRecording } from "./recording";
import {adjustWeight} from "./training-controls";
import {openPublicSession,publicEndpoints} from "./public-session";

const sceneContainer = document.getElementById("scene");
if (!sceneContainer) throw new Error("Missing Three.js scene container");

let client: SimulationClient;
const dashboard = new Dashboard(document, (value) => {
  commandErrorNotice=null;
  if(replayMode){if(value&&replayClock>=(replayFrames.at(-1)?.elapsed ?? Infinity)){replayClock=replayFrames[0]!.elapsed;history.samples=[];}replayPlaying=value;running=value;dashboard.setRunning(value);scene?.setRunning(value);}
  else client.setRunning(value);
});
const gym = new GymDashboard((count) => client.setPopulation(count), () => {history.samples=[];neuronMap?.resetHistory();lastLoadStation=null;renderGym();scene?.focusFly();});
let scene: FlyScene | null = null;
let neuronMap: NeuronMap | null = null;
let latestHello: HelloMessage | null = null;
let latestFrame: FrameMessage | null = null;
let latestGym: GymFrame | null = null;
let running = true;
let closed = false;
let controlState:ControlState|null=null;
const history=new NeuronHistory();
history.select(10783);
let xray=false;
const parameters=new URLSearchParams(location.search);
const requestedFly=parameters.get("fly");
if(requestedFly&&/^fly-([1-9]|10)$/.test(requestedFly))gym.selectedId=requestedFly;
let replayMode=parameters.get("replay")==="1" || (import.meta.env.VITE_DEMO_REPLAY==="1" && parameters.get("live")!=="1");
let replayPlaying=false;
let replayClock=0;
let replayFrames:GymFrame[]=[];
let replayHello:HelloMessage|null=null;
let replayMetadata:Record<string,unknown>={};
let replayLast=0;
let captured:GymFrame[]=[];
let lastRunId:string|null=null;
let runMetadata:Record<string,unknown>={};
let controlHistory:ControlMessage[]=[];
let connected=false;
let replayControls:ControlState[]=[];
let replayKind:ExerciseKind="bench_press";
let replayLoadGeneration=0;
let lastLoadStation:string|null=null;
let pendingNewFly:{id:string;kind:ExerciseKind}|null=null;
let observedFly:string|null=null;
let commandErrorNotice:string|null=null;
const publicMode=import.meta.env.VITE_PUBLIC_SESSIONS==="1";
const element=<T extends HTMLElement=HTMLElement>(id:string)=>document.getElementById(id) as T;
const exerciseButtons=Array.from(document.querySelectorAll<HTMLButtonElement>("[data-exercise]"));

client = new SimulationClient({
  onConnection: (state) => { if(replayMode)return;connected=state==="open";dashboard.setConnection(state); gym.connection(state);if(!connected){pendingNewFly=null;controlState=null;commandErrorNotice=null;element<HTMLButtonElement>("apply-load").disabled=true;element<HTMLButtonElement>("remove-load").disabled=true;element("control-status").textContent=state==="incompatible"?"The model data is incompatible.":state==="reconnecting"?"Reconnecting to your training session…":"Connecting to your training session…";}syncExerciseControls();syncFlySelection(); },
  onHello: (message) => {
    latestHello = message;
    dashboard.updateHello(message);
    gym.configure(message);
    element("load-control").hidden=message.schema===1;
    document.querySelector<HTMLElement>(".exercise-selector")!.hidden=message.schema===1;
    document.querySelectorAll<HTMLElement>(".fly-selection,.training-summary,.metric-strip,.workout-status").forEach(node=>node.hidden=message.schema===1);
    if (message.schema === 1) latestGym = null;
    scene?.configure(message);
  },
  onFrame: (message) => {
    latestFrame = message;
    dashboard.updateFrame(message);
    neuronMap?.update(message);
    scene?.update(message);
    renderSummary(message);
  },
  onGymFrame: (message) => { latestGym = message; renderGym(); },
  onControl: handleControl,
  onPopulation: (count) => gym.acknowledge(count),
  onRunning: (value) => {
    running = value;
    dashboard.setRunning(value);
    scene?.setRunning(value);
  },
  onError: (code) => { pendingNewFly=null;dashboard.showCommandError();gym.commandError();commandErrorNotice=code==="exercise_unavailable"?"That equipment is occupied. Choose the other exercise.":`Could not update training: ${code}`;syncExerciseControls();syncFlySelection();if(controlState)renderLoadState(controlState);element("control-status").textContent=commandErrorNotice; },
  onSessionError:(message)=>{element("session-status").textContent=message;element("control-status").textContent=message;},
},publicMode?{
  endpoint:publicEndpoints(import.meta.env.VITE_BACKEND_URL??"",location.origin).websocket,
  beforeConnect:async()=>{
    element("session-status").textContent="Opening your saved profile…";
    const session=await openPublicSession(publicEndpoints(import.meta.env.VITE_BACKEND_URL??"",location.origin).bootstrap);
    element("session-status").textContent=session.resumed?"Saved profile restored":"Private profile · saved automatically";
    document.body.dataset.sessionMode="private";
  },
}:{});

document.addEventListener("visibilitychange", () => scene?.setVisible(!document.hidden));
window.addEventListener("beforeunload", () => {
  closed = true;
  client.disconnect();
  void scene?.dispose();
  void neuronMap?.dispose();
});
const cameraButtons: Record<CameraMode, HTMLButtonElement | null> = {
  overview: document.querySelector("#view-overview"),
  follow: document.querySelector("#view-fly"),
  eye: document.querySelector("#view-eye"),
};

for (const [mode, button] of Object.entries(cameraButtons)) {
  button?.addEventListener("click", () => selectCameraMode(mode as CameraMode));
}

if(replayMode)void enterReplay();else client.connect();

// Stream instruments immediately; asset downloads and shader compilation are asynchronous.
async function initializeScene(): Promise<void> {
  let graphicsFailed = false;
  try {
    const { FlyScene } = await import("./fly-scene");
    scene = await FlyScene.create(sceneContainer!, () => {
      graphicsFailed = true;
      dashboard.showWebGlError();
    });
    if (closed) { await scene.dispose(); return; }
    if (latestHello) scene.configure(latestHello);
    if (latestGym) renderGym();
    else if (latestFrame) scene.update(latestFrame);
    scene.setRunning(running);
    scene.setVisible(!document.hidden);
    scene.setXray(xray);
    if(controlState)scene.setControlState(controlState);
    if (!graphicsFailed) dashboard.setSceneReady(scene.backend);
  } catch (error) {
    console.error("3D initialization failed", error);
    dashboard.showWebGlError();
  }
}

void initializeScene();
void initializeAnatomy();

function renderGym(): void {
  if (!latestGym) return;
  if(pendingNewFly&&latestGym.flies.some(f=>f.id===pendingNewFly!.id)){
    const next=pendingNewFly;pendingNewFly=null;gym.selectedId=next.id;
    // An old parked fly's original station may now be occupied. Python reserves
    // a free apparatus rather than letting this setup steal another grip.
    client.setExercise(next.id,next.kind);
  }
  const selected = gym.update(latestGym);
  if(observedFly!==selected.id){observedFly=selected.id;history.samples=[];neuronMap?.resetHistory();lastLoadStation=null;const viewURL=new URL(location.href);viewURL.searchParams.set("fly",selected.id);window.history.replaceState(null,"",viewURL);}
  latestFrame = selected.frame;
  dashboard.updateFrame(selected.frame);
  neuronMap?.update(selected.frame);
  scene?.updateGym(latestGym, gym.selectedId);
  renderSummary(selected.frame);
  const e=selected.exercise;
  element("neural-context").textContent=`${e?.kind==="bicep_curl"?"CURL":e?.kind==="bench_press"?"BENCH":"FREE"} / ${(e?.phase ?? "waiting").toUpperCase()}`;
  element("chamber-title").textContent=e?.kind==="bicep_curl"?"The bicep curl":"The bench press";
  element("hero-reps").textContent=String(e?.repetitions ?? 0).padStart(2,"0");
  element("hero-sets").textContent=String(selected.training.sets);
  element("hero-phase").textContent=e?.phase ?? "Free";
  element("work-value").textContent=selected.training.total_work.toFixed(3);
  element("joint-value").textContent=((e?.joint_position ?? 0)*100).toFixed(1);
  element("drive-value").textContent=selected.frame.motor.forward.toFixed(3);
  element("training-strength").textContent=`${selected.training.fitness.toFixed(3)}×`;
  element("training-gain").textContent=`+${((selected.training.fitness-1)*100).toFixed(1)}% this run`;
  element("training-fatigue").textContent=`${Math.round(selected.training.fatigue*100)}%`;
  element<HTMLMeterElement>("training-fatigue-meter").value=selected.training.fatigue;
  element("training-set-progress").textContent=`${e?.rep_in_set ?? 0} / 3 reps`;
  document.querySelector<HTMLElement>(".training-summary")!.dataset.fly=selected.id;
  syncFlySelection();
  if(!replayMode&&controlState){renderLoadState(controlState);renderTaskState(controlState);}
  syncExerciseControls();
  if(!replayMode){
    if(captured.at(-1)?.step===latestGym.step)captured[captured.length-1]=latestGym;else captured.push(latestGym);
    const max=Math.floor(1200/latestGym.flies.length);if(captured.length>max)captured.splice(0,captured.length-max);
  }
}

async function initializeAnatomy(): Promise<void> {
  const container = document.querySelector<HTMLElement>("#neuron-map")!;
  const loading = document.querySelector<HTMLElement>("#anatomy-loading")!;
  let failed = false;
  const failure = () => {
    failed = true;
    container.dataset.anatomy = "failed";
    loading.hidden = false;
    loading.textContent = "Atlas unavailable; exact readings remain below.";
  };
  try {
    const { NeuronMap } = await import("./neuron-map");
    neuronMap = await NeuronMap.create(container, failure);
    if (closed) { await neuronMap.dispose(); return; }
    if (latestFrame) neuronMap.update(latestFrame);
    if(history.selectedId!==null)neuronMap.select(history.selectedId);
    if (!failed) loading.hidden = true;
  } catch (error) { console.error("Anatomical view failed", error); failure(); }
}

function renderSummary(frame:FrameMessage):void{
  history.record(frame.elapsed,frame.neural.active);
  const selected=frame.neural.active.find(n=>n.body_id===history.selectedId);
  element("model-scope").textContent=`${frame.neural.active.length} received cells`;
  element("neural-active-count").textContent=String(frame.neural.active.filter(n=>n.activity>0).length);
  element("neural-observed-count").textContent=String(frame.neural.active.length);
  element("neural-mean-rate").textContent=frame.neural.active.length?(frame.neural.active.reduce((sum,n)=>sum+n.activity,0)/frame.neural.active.length).toFixed(3):"—";
  element("selected-id").textContent=history.selectedId===null?"—":String(history.selectedId);
  element("selected-label").textContent=selected?.label ?? "No observation in this frame";
  element("selected-value").textContent=selected ? `${selected.activity} rate` : "UNOBSERVED";
  element("selected-time").textContent=`t = ${frame.elapsed.toFixed(3)} s`;
  const first=history.samples[0]?.time ?? 0,last=history.samples.at(-1)?.time ?? first;
  const segments:string[]=[];let points:string[]=[];
  for(const p of history.samples){if(p.value===null){if(points.length)segments.push(points.join(" "));points=[];continue;}points.push(`${(p.time-first)/Math.max(.1,last-first)*400},${38-Math.max(0,Math.min(1,p.value))*35}`);}
  if(points.length)segments.push(points.join(" "));
  element("neuron-trace").replaceChildren(...segments.map(points=>{const line=document.createElementNS("http://www.w3.org/2000/svg","polyline");line.setAttribute("points",points);return line;}));
  document.querySelectorAll<HTMLElement>(".neuron-row").forEach(row=>row.setAttribute("aria-selected",String(Number(row.dataset.bodyId)===history.selectedId)));
}

function handleControl(message:ControlMessage):void{
  if(message.type==="control_state"){
    if(lastRunId!==message.run_id){captured=[];controlHistory=[];runMetadata={};history.samples=[];neuronMap?.resetHistory();lastLoadStation=null;commandErrorNotice=null;lastRunId=message.run_id;}
    if(message.metadata)runMetadata=message.metadata;
    controlHistory.push(message);if(controlHistory.length>6000)controlHistory.shift();
    controlState=message;
    renderLoadState(message);
    renderTaskState(message);
    element("run-metadata").textContent=`LIVE run ${message.run_id}. ${JSON.stringify(runMetadata)}`;
  }else if(message.command==="set_running" && message.status==="applied")element("control-status").textContent=running?"Training in progress · 3 full reps build fitness":"Training paused";
  else if(message.command==="set_exercise")element("exercise-pending").textContent=message.status==="applied"?`Apparatus ready · step ${message.effective_step}`:"Waiting for the next rack boundary…";
}
function renderLoadState(state:ControlState):void{
  const station=latestGym?.flies.find(f=>f.id===gym.selectedId)?.exercise?.station_id;
  const load=state.loads.find(s=>s.station_id===station);
  const changingExercise=state.exercises?.find(row=>row.fly_id===gym.selectedId)?.pending_kind;
  if(load){
    element("current-load").textContent=load.load.toFixed(2);
    element<HTMLInputElement>("load-value").value=(load.pending_load??load.load).toFixed(2);lastLoadStation=station!;
    element<HTMLButtonElement>("apply-load").disabled=replayMode||!connected||Boolean(changingExercise)||load.pending_load!==null||load.load>=3;
    element<HTMLButtonElement>("remove-load").disabled=replayMode||!connected||Boolean(changingExercise)||load.pending_load!==null||load.load<=.1;
    element("control-status").textContent=replayMode?"Recorded session · exact sampled training":load.pending_load!==null?`Weight ${load.pending_load.toFixed(2)} queued · changes after this rep finishes`:changingExercise?"Exercise changes after this rep finishes":`Weight ${load.load.toFixed(2)} · add weight for more resistance`;
  }else{
    element("current-load").textContent="—";element<HTMLButtonElement>("apply-load").disabled=true;element<HTMLButtonElement>("remove-load").disabled=true;
  }
  if(commandErrorNotice)element("control-status").textContent=commandErrorNotice;
}
function syncExerciseControls():void{
  const setup=controlState?.exercises?.find(row=>row.fly_id===gym.selectedId);
  const actual=latestGym?.flies.find(fly=>fly.id===gym.selectedId)?.exercise?.kind;
  const station=latestGym?.flies.find(fly=>fly.id===gym.selectedId)?.exercise?.station_id;
  const changingWeight=controlState?.loads.find(row=>row.station_id===station)?.pending_load!=null;
  for(const button of exerciseButtons){
    const kind=button.dataset.exercise;
    button.setAttribute("aria-pressed",String(kind===actual));
    button.dataset.pending=String(!replayMode&&setup?.pending_kind===kind);
    button.disabled=replayMode?false:!connected||!setup||setup.pending_kind!==null||changingWeight;
  }
  if(setup?.pending_kind&&!replayMode)element("exercise-pending").textContent=`Next rack: ${setup.pending_kind==="bicep_curl"?"dumbbell curl":"bench press"}`;
  else element("exercise-pending").textContent="";
}
function renderTaskState(state:ControlState):void{
  scene?.setControlState(state);
  const feedback=state.feedback?.find(row=>row.fly_id===gym.selectedId);
  element("feedback-profile").textContent=feedback?.profile==="apparatus-visual-v1"?"Apparatus visual feedback · synthetic input":feedback?.profile==="none"?"Baseline model · apparatus feedback off":"No apparatus feedback observation";
  element("cue-left").textContent=feedback?feedback.indicator_left.toFixed(3):"—";
  element("cue-right").textContent=feedback?feedback.indicator_right.toFixed(3):"—";
  syncExerciseControls();
  syncFlySelection();
}
for(const button of exerciseButtons)button.addEventListener("click",()=>{
  commandErrorNotice=null;
  const kind=button.dataset.exercise as ExerciseKind;
  if(replayMode){void enterReplay(kind);return;}
  client.setExercise(gym.selectedId,kind);
  element("exercise-pending").textContent="Requesting apparatus setup…";
});
function changeWeight(direction:1|-1):void{
  const station=latestGym?.flies.find(f=>f.id===gym.selectedId)?.exercise?.station_id;
  const load=controlState?.loads.find(row=>row.station_id===station);
  if(replayMode||!connected||!station||!load||load.pending_load!==null||controlState?.exercises?.find(row=>row.fly_id===gym.selectedId)?.pending_kind)return;
  const next=adjustWeight(load.load,direction);if(next===load.load)return;
  commandErrorNotice=null;
  client.setLoad(station,next);element<HTMLButtonElement>("apply-load").disabled=true;element<HTMLButtonElement>("remove-load").disabled=true;
  element("control-status").textContent=`Preparing weight ${next.toFixed(2)} · changes after this rep finishes`;
}
element("apply-load").addEventListener("click",()=>changeWeight(1));
element("remove-load").addEventListener("click",()=>changeWeight(-1));
function syncFlySelection():void{
  const select=element<HTMLSelectElement>("training-fly");
  const flies=latestGym?.flies??[];
  if(Array.from(select.options).map(o=>o.value).join(",")!==flies.map(f=>f.id).join(","))select.replaceChildren(...flies.map(f=>new Option(`Fly ${f.id.slice(4).padStart(2,"0")}`,f.id)));
  select.value=gym.selectedId;select.disabled=flies.length===0||pendingNewFly!==null;
  element<HTMLButtonElement>("add-training-fly").disabled=replayMode||!connected||!controlState||pendingNewFly!==null||flies.length===0||flies.length>=10;
}
element("training-fly").addEventListener("change",()=>{
  const id=element<HTMLSelectElement>("training-fly").value;if(latestGym?.flies.some(f=>f.id===id))gym.select(id);
});
element("add-training-fly").addEventListener("click",()=>{
  if(replayMode||!connected||pendingNewFly||!latestGym||latestGym.flies.length>=10)return;
  const count=latestGym.flies.length+1,kind=latestGym.flies.find(f=>f.id===gym.selectedId)?.exercise?.kind??"bench_press";
  commandErrorNotice=null;pendingNewFly={id:`fly-${count}`,kind};syncFlySelection();client.setPopulation(count);
  element("control-status").textContent=`Preparing Fly ${String(count).padStart(2,"0")}…`;
});
function setXray(value:boolean):void{xray=value;scene?.setXray(value);document.body.classList.toggle("xray-mode",value);element("xray-toggle").setAttribute("aria-pressed",String(value));element("xray-toggle").textContent=value?"◇ X-RAY ON":"◇ X-RAY";}
element("xray-toggle").addEventListener("click",()=>setXray(!xray));
document.addEventListener("neuron-select",event=>{history.select((event as CustomEvent<number>).detail);neuronMap?.select(history.selectedId!);if(latestFrame)renderSummary(latestFrame);});
const dialog=element("methods-dialog");
element("open-methods").addEventListener("click",()=>{dialog.hidden=false;element("close-methods").focus();});
element("close-methods").addEventListener("click",()=>{dialog.hidden=true;element("open-methods").focus();});
document.addEventListener("keydown",event=>{if(event.key==="Escape"&&!dialog.hidden){dialog.hidden=true;element("open-methods").focus();}});

document.querySelectorAll<HTMLButtonElement>(".tabs button").forEach(button=>button.addEventListener("click",()=>{
  const tab=button.dataset.tab;
  document.querySelectorAll(".tabs button").forEach(b=>b.setAttribute("aria-selected",String(b===button)));
  if(tab==="replay"){
    document.body.classList.remove("recorded-observer");
    if(!replayMode || !replayFrames.length)void enterReplay();
    return;
  }
  if(replayMode)document.body.classList.add("recorded-observer");
  setXray(tab==="neurons");
}));

// Returning to live is explicit; observer navigation must preserve a recording.
const liveReturn=document.createElement("button");liveReturn.textContent="Go live";
liveReturn.hidden=import.meta.env.VITE_DEMO_REPLAY==="1";
liveReturn.addEventListener("click",()=>{location.href="./?live=1";});
document.querySelector(".replay-tools")!.append(liveReturn);

async function enterReplay(kind:ExerciseKind="bench_press"):Promise<void>{
  const opening=!replayMode||!replayFrames.length;
  const generation=++replayLoadGeneration;
  client?.setRunning(false);client?.disconnect();replayMode=true;replayPlaying=false;running=false;
  gym.recorded();
  connected=false;
  document.body.classList.add("replay-mode");
  document.body.classList.add("recorded-observer");
  element("recording-tools").hidden=false;
  if(opening)document.querySelectorAll<HTMLButtonElement>(".tabs button").forEach(b=>b.setAttribute("aria-selected",String(b.dataset.tab==="workout")));
  element("connection-label").textContent="RECORDED";element("connection-dot").dataset.state="open";
  element<HTMLButtonElement>("running-toggle").disabled=false;
  dashboard.setRunning(false);scene?.setRunning(false);
  element("exercise-pending").textContent="Loading recorded scenario…";
  try{
    if(!replayFrames.length||replayKind!==kind){
      const name=kind==="bicep_curl"?"demo-curl":"demo-bench";
      const response=await fetch(`${import.meta.env.BASE_URL}samples/${name}.json`);if(!response.ok)throw new Error("Sample unavailable");
      const recording=parseRecording(await response.json());
      if(generation!==replayLoadGeneration)return;
      replayHello=recording.hello;replayFrames=recording.frames;replayMetadata=recording.metadata;replayControls=recording.controls;replayKind=kind;
    }
    if(generation!==replayLoadGeneration)return;
    latestHello=replayHello;dashboard.updateHello(replayHello!);gym.configure(replayHello!);gym.recorded();scene?.configure(replayHello!);
    replayClock=replayFrames[0]!.elapsed;history.samples=[];showReplayFrame();
    element("current-load").textContent=Number(replayMetadata.load ?? .6).toFixed(2);
    element("run-metadata").textContent=JSON.stringify(replayMetadata,null,2);
    element("control-status").textContent="RECORDED · Exact sampled states · Python backend not required";
  }catch(error){element("control-status").textContent=`Replay could not load: ${error instanceof Error?error.message:error}`;}
}
function showReplayFrame():void{
  if(!replayFrames.length)return;
  latestGym=sampleAt(replayFrames,replayClock);renderGym();
  if(replayControls.length){controlState=sampleAt(replayControls,latestGym.elapsed);renderTaskState(controlState);renderLoadState(controlState);}
  else{scene?.setControlState({type:"control_state",protocol:1,run_id:"unobserved-recording",step:latestGym.step,elapsed:latestGym.elapsed,loads:[]});element("feedback-profile").textContent="Baseline recording · apparatus feedback off";element("cue-left").textContent="—";element("cue-right").textContent="—";}
  const start=replayFrames[0]!.elapsed,duration=replayFrames.at(-1)!.elapsed-start;
  element<HTMLInputElement>("replay-seek").value=String((replayClock-start)/Math.max(.001,duration));
  syncVideo();
}
function replayTick(now:number):void{
  const delta=replayLast?Math.min(.2,(now-replayLast)/1000):0;replayLast=now;
  if(replayMode&&replayPlaying&&replayFrames.length){replayClock=Math.min(replayFrames.at(-1)!.elapsed,replayClock+delta*Number(element<HTMLSelectElement>("replay-speed").value));showReplayFrame();if(replayClock>=replayFrames.at(-1)!.elapsed){replayPlaying=false;running=false;dashboard.setRunning(false);scene?.setRunning(false);}}
  if(!closed)requestAnimationFrame(replayTick);
}
requestAnimationFrame(replayTick);
element("replay-restart").addEventListener("click",()=>{replayClock=replayFrames[0]?.elapsed ?? 0;history.samples=[];showReplayFrame();});
element("replay-seek").addEventListener("input",()=>{if(!replayFrames.length)return;replayClock=replayFrames[0]!.elapsed+Number(element<HTMLInputElement>("replay-seek").value)*(replayFrames.at(-1)!.elapsed-replayFrames[0]!.elapsed);showReplayFrame();});
const video=element<HTMLVideoElement>("replay-video");let videoURL:string|null=null;
const userPanel=document.createElement("section");userPanel.className="user-set";userPanel.setAttribute("aria-label","User-selected local workout video");
const userHeading=document.createElement("h2");userHeading.textContent="Your set";userPanel.append(userHeading,document.querySelector(".video-row")!);element("recording-tools").append(userPanel);video.hidden=true;
element("user-video").addEventListener("change",()=>{const file=element<HTMLInputElement>("user-video").files?.[0];if(!file)return;if(videoURL)URL.revokeObjectURL(videoURL);videoURL=URL.createObjectURL(file);video.src=videoURL;element("video-placeholder").hidden=true;video.hidden=false;video.addEventListener("loadedmetadata",syncVideo,{once:true});});
element("video-offset").addEventListener("input",syncVideo);
function syncVideo():void{if(!videoURL || !Number.isFinite(video.duration))return;const offset=Number(element<HTMLInputElement>("video-offset").value);if(!Number.isFinite(offset)||offset<0||offset>86400)return;const time=Math.min(video.duration,Math.max(0,replayClock-(replayFrames[0]?.elapsed ?? 0)+offset));if(Math.abs(video.currentTime-time)>.04)video.currentTime=time;}
function download(name:string,content:string,type:string):void{const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
element("export-json").addEventListener("click",()=>{
  const frames=replayMode?replayFrames:captured;if(!frames.length)return;
  const offset=Number(element<HTMLInputElement>("video-offset").value);
  const metadata=replayMode?replayMetadata:{...runMetadata,run_id:lastRunId,dataset:"male-cns:v1.0",capture:"received snapshots; bounded to latest 1200 fly snapshots",control_state:controlState,control_history:controlHistory};
  download("drosolift-run.json",JSON.stringify({format:"drosolift-recording",version:1,metadata:{...metadata,video_alignment:{offset_seconds:Number.isFinite(offset)&&offset>=0&&offset<=86400?offset:0,recording_start_seconds:frames[0]!.elapsed,convention:"video time = simulation playhead - recording start + offset; video remains local"}},hello:latestHello,frames}),"application/json");
});
element("export-csv").addEventListener("click",()=>{
  const frames=replayMode?replayFrames:captured;
  const rows=["step,elapsed,fly_id,joint_position,repetitions,completed_sets,positive_work,forward_drive",...frames.flatMap(f=>f.flies.map(a=>[f.step,f.elapsed,a.id,a.exercise?.joint_position ?? 0,a.exercise?.repetitions ?? 0,a.training.sets,a.training.total_work,a.frame.motor.forward].join(",")))];download("drosolift-run.csv",rows.join("\n"),"text/csv");
});

function selectCameraMode(mode: CameraMode): void {
  if (!scene) return;
  if (mode === "overview") scene.showOverview();
  if (mode === "follow") scene.focusFly();
  if (mode === "eye") scene.showEyeView();
  sceneContainer!.dataset.cameraMode = mode;
  sceneContainer!.setAttribute("aria-describedby", mode === "eye" ? "camera-approximation" : "camera-instructions");
  for (const [buttonMode, button] of Object.entries(cameraButtons)) {
    button?.setAttribute("aria-pressed", String(buttonMode === mode));
  }
}
