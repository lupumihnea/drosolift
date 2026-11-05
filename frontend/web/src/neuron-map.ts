import * as THREE from "three/webgpu";
import {OrbitControls} from "three/addons/controls/OrbitControls.js";
import {createGraphicsRenderer,reportGraphicsStatistics} from "./graphics-renderer";
import {parseAnatomy,type NeuronAnatomy} from "./neuron-anatomy";
import {filterNeuronReadings} from "./neuron-readings";
import {disposeScene} from "./scene-primitives";
import {createSkeletonGroup,updateSkeletonActivity,setSkeletonBrainCrop} from "./skeleton-view";
import {activityAppearance,atlasConnections,circuitLayout,GROUP_BY_BODY,NEURAL_GROUPS,summarizeGroups,type NeuralGroupId,type NeuralLink} from "./neural-activity";
import {neuralGlowTexture,neuralPointMaterial,neuralSprite} from "./neural-sprites";
import type {ActiveNeuron,FrameMessage} from "./types";
import {brainCropIncludes,cellGroupColor,NeuralRateHistory,rateColor} from "./neural-history";

const CAPACITY=256;
type Mode="atlas"|"circuit";

/** Source-backed atlas and circuit observer. Glow follows received rates, never render time. */
export class NeuronMap {
  private readonly scene=new THREE.Scene();
  private readonly camera=new THREE.PerspectiveCamera(35,1,.01,30);
  private readonly controls:OrbitControls;
  private readonly positions=new Map<number,readonly number[]>();
  private readonly authored=circuitLayout();
  private readonly texture=neuralGlowTexture();
  private readonly context=new THREE.Group();
  private readonly rateHistory=new NeuralRateHistory();
  private readonly historyIds=NEURAL_GROUPS.flatMap(group=>group.ids);
  private brainSomata=0;
  private brainOnly=true;
  private colorMode:"activity"|"cell-colors"="activity";
  private lastStep=0;
  private readonly nodeGeometry=new THREE.BufferGeometry();
  private readonly highlights:THREE.Points;
  private readonly halos:THREE.Points;
  private readonly visibleNodes=new THREE.Group();
  private readonly sprites:{core:THREE.Sprite;halo:THREE.Sprite}[]=[];
  private readonly selectionGeometry=new THREE.BufferGeometry();
  private readonly selectionMarker:THREE.Sprite;
  private readonly atlasLinks:THREE.LineSegments;
  private readonly circuitLinks:THREE.LineSegments;
  private readonly atlasEdges:NeuralLink[];
  private readonly diagramEdges:NeuralLink[];
  private readonly resizeObserver:ResizeObserver;
  private readonly intersectionObserver:IntersectionObserver;
  private readonly raycaster=new THREE.Raycaster();
  private readonly search=document.querySelector<HTMLInputElement>("#neuron-search")!;
  private readonly summary=document.querySelector<HTMLElement>("#anatomy-summary")!;
  private readonly selection=document.querySelector<HTMLElement>("#anatomy-selection")!;
  private readonly groupButtons=new Map<NeuralGroupId,HTMLButtonElement>();
  private mode:Mode="atlas";
  private focus:NeuralGroupId|null=null;
  private readings:readonly ActiveNeuron[]=[];
  private mapped:{neuron:ActiveNeuron;position:readonly number[]}[]=[];
  private selectedId:number|null=null;
  private skeletons:THREE.Group|null=null;
  private skeletonPromise:Promise<THREE.Group>|null=null;
  private elapsed=0;
  private visible=true;
  private disposed=false;
  private lastStatistics=0;

  static async create(container:HTMLElement,onFailure:()=>void):Promise<NeuronMap>{
    const response=await fetch(`${import.meta.env.BASE_URL}assets/neuron-positions.json`);
    if(!response.ok)throw new Error("Anatomy unavailable");
    const anatomy=parseAnatomy(await response.json());
    const {renderer,assertHealthy}=await createGraphicsRenderer(new URLSearchParams(location.search).get("renderer")==="webgl",onFailure);
    let view:NeuronMap|null=null;
    try{
      renderer.shadowMap.enabled=false;
      view=new NeuronMap(container,renderer,anatomy);
      await view.loadMorphology();
      await renderer.compileAsync(view.scene,view.camera);assertHealthy();
      await renderer.setAnimationLoop(()=>view?.render());assertHealthy();
      container.dataset.anatomy="ready";return view;
    }catch(error){if(view)await view.dispose();else await renderer.dispose();throw error;}
  }

  private constructor(private readonly container:HTMLElement,private readonly renderer:THREE.WebGPURenderer,anatomy:NeuronAnatomy){
    this.scene.background=new THREE.Color("#071319");
    const coordinates=new Float32Array(anatomy.points.length*3);
    const brain:number[]=[],other:number[]=[];
    anatomy.points.forEach(([id,x,y,z])=>{const position=[x,-y,z];this.positions.set(id,position);
      (brainCropIncludes(position)?brain:other).push(...position);});
    coordinates.set(brain,0);coordinates.set(other,brain.length);this.brainSomata=brain.length/3;
    const anatomyGeometry=new THREE.BufferGeometry().setAttribute("position",new THREE.BufferAttribute(coordinates,3));
    const surfaceMaterial=neuralPointMaterial(this.texture,.007,.085,false);surfaceMaterial.color.set("#2e77bc");
    const hazeMaterial=neuralPointMaterial(this.texture,.024,.006,false);hazeMaterial.color.set("#397cc6");
    this.context.add(new THREE.Points(anatomyGeometry,surfaceMaterial),new THREE.Points(anatomyGeometry,hazeMaterial));
    this.scene.add(this.context);
    this.nodeGeometry.setAttribute("position",new THREE.BufferAttribute(new Float32Array(CAPACITY*3),3));
    this.nodeGeometry.setAttribute("color",new THREE.BufferAttribute(new Float32Array(CAPACITY*3),3));
    this.nodeGeometry.setDrawRange(0,0);
    this.highlights=new THREE.Points(this.nodeGeometry,neuralPointMaterial(this.texture,.041,.45));
    this.halos=new THREE.Points(this.nodeGeometry,neuralPointMaterial(this.texture,.15,0));
    this.highlights.renderOrder=5;this.halos.renderOrder=4;this.scene.add(this.halos,this.highlights);
    this.selectionGeometry.setAttribute("position",new THREE.Float32BufferAttribute([0,0,0],3));
    this.selectionMarker=neuralSprite(this.texture,.21,.82);this.selectionMarker.material.color.set("#fff4bf");this.selectionMarker.visible=false;this.selectionMarker.renderOrder=6;this.scene.add(this.selectionMarker,this.visibleNodes);
    this.atlasEdges=atlasConnections(this.positions);this.diagramEdges=atlasConnections(this.authored.positions);
    this.atlasLinks=this.linkGeometry(this.atlasEdges,.32);this.circuitLinks=this.linkGeometry(this.diagramEdges,.92);
    this.scene.add(this.atlasLinks,this.circuitLinks);
    const canvas=renderer.domElement;canvas.tabIndex=0;
    canvas.setAttribute("aria-label","Official MaleCNS anatomy; drag to orbit, scroll to zoom, click a received cell or morphology to inspect");
    canvas.setAttribute("aria-describedby","anatomy-summary");container.prepend(canvas);
    this.controls=new OrbitControls(this.camera,canvas);this.controls.enablePan=false;this.controls.minDistance=.8;this.controls.maxDistance=8;
    canvas.addEventListener("pointermove",this.pick);canvas.addEventListener("click",this.selectPoint);canvas.addEventListener("keydown",this.keydown);
    this.search.addEventListener("input",this.refresh);
    document.querySelector("#view-atlas")?.addEventListener("click",this.showAtlas);
    document.querySelector("#view-circuit")?.addEventListener("click",this.showCircuit);
    document.querySelector("#neural-live")?.addEventListener("click",this.showLive);
    document.querySelector("#neural-cell-colors")?.addEventListener("click",this.showCellColors);
    document.querySelector("#neural-front")?.addEventListener("click",this.frontView);
    document.querySelector("#neural-vnc")?.addEventListener("click",this.toggleVnc);
    document.querySelector("#neural-rate-history")?.addEventListener("mousemove",this.inspectHistory);
    this.buildGroupControls();
    this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(container);
    this.intersectionObserver=new IntersectionObserver(([entry])=>{this.visible=entry?.isIntersecting??false;});this.intersectionObserver.observe(container);
    this.raycaster.params.Points={threshold:.025};this.raycaster.params.Line={threshold:.012};
    this.resize();this.setMode("atlas");
  }

  update(frame:FrameMessage):void{this.readings=frame.neural.active;this.elapsed=frame.elapsed;this.lastStep=frame.step;this.rateHistory.record(frame.elapsed,frame.neural.active);this.refresh();}
  resetHistory():void{this.rateHistory.clear();this.renderHistory();}
  select(id:number):void{this.selectedId=id;this.refresh();}
  /** Kept for older callers. Official morphology remains visible independently of body X-ray. */
  async setDetailed(_enabled:boolean):Promise<void>{await this.loadMorphology();this.refresh();}

  private async loadMorphology():Promise<void>{
    try{
      this.skeletonPromise??=createSkeletonGroup(this.texture).catch(error=>{this.skeletonPromise=null;throw error;});
      const group=await this.skeletonPromise;
      if(this.disposed){disposeScene(group);return;}
      if(!this.skeletons){this.skeletons=group;this.scene.add(group);}
      this.container.dataset.detail="official-skeletons";this.refresh();
    }catch{this.container.dataset.detail="soma-atlas";this.refresh();}
  }

  private linkGeometry(edges:readonly NeuralLink[],opacity:number):THREE.LineSegments{
    const positions=new Float32Array(edges.length*6);
    edges.forEach((edge,index)=>{positions.set(edge.from,index*6);positions.set(edge.to,index*6+3);});
    const geometry=new THREE.BufferGeometry().setAttribute("position",new THREE.BufferAttribute(positions,3))
      .setAttribute("color",new THREE.BufferAttribute(new Float32Array(edges.length*6),3));
    const line=new THREE.LineSegments(geometry,new THREE.LineBasicMaterial({vertexColors:true,transparent:true,opacity,depthTest:false,depthWrite:false,
      blending:THREE.NormalBlending,toneMapped:false}));line.renderOrder=2;return line;
  }

  private updateLinks(line:THREE.LineSegments,edges:readonly NeuralLink[]):void{
    const byId=new Map(this.readings.map(reading=>[reading.body_id,reading.activity]));
    const colors=line.geometry.getAttribute("color") as THREE.BufferAttribute;
    edges.forEach((edge,index)=>{
      const appearance=activityAppearance(byId.get(edge.pre));
      const activeGroup=!this.focus||GROUP_BY_BODY.get(edge.pre)===this.focus||GROUP_BY_BODY.get(edge.post)===this.focus;
      const amount=appearance.intensity*(activeGroup?1:.055);
      for(let point=0;point<2;point++)colors.setXYZ(index*2+point,appearance.color[0]*amount,appearance.color[1]*amount,appearance.color[2]*amount);
    });colors.needsUpdate=true;
  }

  private readonly refresh=():void=>{
    const positions=this.mode==="atlas"?this.positions:this.authored.positions;
    this.mapped=filterNeuronReadings(this.readings,this.search.value).flatMap(neuron=>{
      const position=positions.get(neuron.body_id);return position&&(this.mode!=="atlas"||!this.brainOnly||brainCropIncludes(position))?[{neuron,position}]:[];
    }).slice(0,CAPACITY);
    const vertex=this.nodeGeometry.getAttribute("position") as THREE.BufferAttribute;
    const colors=this.nodeGeometry.getAttribute("color") as THREE.BufferAttribute;
    this.mapped.forEach(({neuron,position},index)=>{
      vertex.setXYZ(index,position[0]!,position[1]!,position[2]!);
      const appearance=activityAppearance(neuron.activity);
      const displayColor=this.colorMode==="cell-colors"?cellGroupColor(neuron.body_id):appearance.color;
      const intensity=appearance.intensity*((this.focus&&GROUP_BY_BODY.get(neuron.body_id)!==this.focus)? .08:1);
      colors.setXYZ(index,displayColor[0]*intensity,displayColor[1]*intensity,displayColor[2]*intensity);
      let pair=this.sprites[index];
      if(!pair){pair={core:neuralSprite(this.texture,.078,.9),halo:neuralSprite(this.texture,.22,.3)};
        pair.core.renderOrder=5;pair.halo.renderOrder=4;this.visibleNodes.add(pair.halo,pair.core);this.sprites.push(pair);}
      for(const sprite of [pair.core,pair.halo]){sprite.visible=true;sprite.position.set(position[0]!,position[1]!,position[2]!);sprite.material.color.fromArray(displayColor);sprite.userData.body_id=neuron.body_id;}
      pair.core.material.opacity=this.colorMode==="cell-colors"?.85:Math.max(.18,intensity);pair.halo.material.opacity=(this.colorMode==="cell-colors"?.65:intensity)*.3;
    });vertex.needsUpdate=true;colors.needsUpdate=true;this.nodeGeometry.setDrawRange(0,this.mapped.length);this.nodeGeometry.computeBoundingSphere();
    for(let index=this.mapped.length;index<this.sprites.length;index++){this.sprites[index]!.core.visible=false;this.sprites[index]!.halo.visible=false;}
    this.context.visible=this.mode==="atlas";this.atlasLinks.visible=false;this.circuitLinks.visible=this.mode==="circuit";
    for(const child of this.context.children){if(child instanceof THREE.Points)child.geometry.setDrawRange(0,this.brainOnly?this.brainSomata:Infinity);}
    if(this.skeletons){this.skeletons.visible=this.mode==="atlas";setSkeletonBrainCrop(this.skeletons,this.brainOnly);updateSkeletonActivity(this.skeletons,this.readings,this.focus,this.colorMode);}
    this.updateLinks(this.atlasLinks,this.atlasEdges);this.updateLinks(this.circuitLinks,this.diagramEdges);
    const selected=positions.get(this.selectedId??-1);this.selectionMarker.visible=Boolean(selected&&(this.mode!=="atlas"||!this.brainOnly||brainCropIncludes(selected)));
    if(selected)this.selectionMarker.position.set(selected[0]!,selected[1]!,selected[2]!);
    this.container.dataset.observed=String(this.mapped.length);this.container.dataset.positive=String(this.mapped.filter(point=>point.neuron.activity>0).length);
    this.container.dataset.mode=this.mode;this.container.dataset.focus=this.focus??"all";
    this.container.dataset.colorMode=this.colorMode;this.container.dataset.crop=this.brainOnly?"brain":"cns";this.container.dataset.brainSomata=String(this.brainSomata);
    const colorLabel=document.querySelector("#neural-color-label"),colorRange=document.querySelector("#neural-color-range");
    if(colorLabel)colorLabel.textContent=this.colorMode==="cell-colors"?"Model groups":"Received rate";
    if(colorRange)colorRange.textContent=this.colorMode==="cell-colors"?"6 groups":"0–1";
    const missing=this.readings.filter(neuron=>!this.positions.has(neuron.body_id)).length;
    this.summary.textContent=this.mode==="atlas"?`${(this.brainOnly?this.brainSomata:this.positions.size).toLocaleString("en-US")} measured somata in ${this.brainOnly?"display crop":"CNS"} · ${this.mapped.length}/${this.readings.length} readings shown`
      :`${this.authored.positions.size} official model cells · ${this.diagramEdges.length} source edges · authored circuit layout`;
    const note=document.querySelector("#neural-mode-note");
    if(note)note.textContent=this.mode==="atlas"?(this.colorMode==="activity"?"Blue anatomy · Cyan → yellow = received rate · No spike events":"Cell colors = model input/readout groups · Colors do not encode activity")
      :"MODEL CIRCUIT · Authored layout · Source structural edges; brightness = pre-cell rate";
    const reading=this.readings.find(neuron=>neuron.body_id===this.selectedId);
    this.selection.textContent=reading?`${reading.label} · ${reading.body_id} · ${reading.activity} rate` : "Select a group, cell or official morphology";
    for(const group of summarizeGroups(this.readings)){
      const button=this.groupButtons.get(group.id);if(!button)continue;
      button.setAttribute("aria-pressed",String(group.id===this.focus));button.dataset.observed=String(group.observed);button.dataset.mean=group.mean===null?"":String(group.mean);
      button.querySelector(".group-rate")!.textContent=group.mean===null?"—":group.mean.toFixed(3);
      (button.querySelector(".group-meter > i") as HTMLElement).style.width=`${group.mean===null?0:Math.max(0,Math.min(1,group.mean))*100}%`;
      button.title=`${group.detail}. Received ${group.observed}/${group.total}; mean ${group.mean??"UNOBSERVED"}; t=${this.elapsed}s. Body IDs: ${group.ids.join(", ")}`;
    }
    this.renderHistory();
  };

  private buildGroupControls():void{
    const container=document.querySelector("#neural-groups");if(!container)return;
    for(const group of NEURAL_GROUPS){
      const button=document.createElement("button");button.type="button";button.className="neural-group";button.dataset.group=group.id;button.dataset.ids=group.ids.join(",");button.style.setProperty("--group-color",group.color);
      const label=document.createElement("span");label.className="group-label";label.textContent=group.label;
      const rate=document.createElement("span");rate.className="group-rate";rate.textContent="—";
      const meter=document.createElement("span");meter.className="group-meter";meter.setAttribute("aria-hidden","true");meter.append(document.createElement("i"));
      button.append(label,rate,meter);
      button.addEventListener("click",()=>{
        this.focus=this.focus===group.id?null:group.id;
        if(this.focus&&!group.ids.includes(this.selectedId??-1)){
          const received=this.readings.filter(neuron=>group.ids.includes(neuron.body_id)).sort((a,b)=>b.activity-a.activity||a.body_id-b.body_id)[0];
          if(received)document.dispatchEvent(new CustomEvent("neuron-select",{detail:received.body_id}));
        }
        this.refresh();
      });container.append(button);this.groupButtons.set(group.id,button);
    }
  }

  private readonly showAtlas=():void=>this.setMode("atlas");
  private readonly showCircuit=():void=>this.setMode("circuit");
  private readonly showLive=():void=>{this.colorMode="activity";this.setMode("atlas");};
  private readonly showCellColors=():void=>{this.colorMode="cell-colors";this.setMode("atlas");};
  private readonly frontView=():void=>{this.fitCamera();this.controls.update();};
  private readonly toggleVnc=():void=>{this.brainOnly=!this.brainOnly;document.querySelector("#neural-vnc")?.setAttribute("aria-pressed",String(!this.brainOnly));this.fitCamera();this.controls.update();this.refresh();};
  private setMode(mode:Mode):void{
    this.mode=mode;this.camera.up.set(0,mode==="atlas"?0:1,mode==="atlas"?-1:0);
    this.fitCamera();this.controls.update();
    document.querySelector("#view-atlas")?.setAttribute("aria-pressed",String(mode==="atlas"));
    document.querySelector("#view-circuit")?.setAttribute("aria-pressed",String(mode==="circuit"));this.refresh();
    document.querySelector("#neural-live")?.setAttribute("aria-pressed",String(mode==="atlas"&&this.colorMode==="activity"));
    document.querySelector("#neural-cell-colors")?.setAttribute("aria-pressed",String(mode==="atlas"&&this.colorMode==="cell-colors"));
  }

  private fitCamera():void{
    const height=this.mode==="atlas"?(this.brainOnly?.88:2.16):2.36,width=this.mode==="atlas"?1.72:2.65;
    const distance=Math.max(height,width/Math.max(.25,this.camera.aspect))/(2*Math.tan(THREE.MathUtils.degToRad(this.camera.fov/2)));
    const centerZ=this.mode==="atlas"&&this.brainOnly?-.64:0;
    this.controls.target.set(0,0,centerZ);
    this.camera.position.set(0,this.mode==="atlas"?-distance:0,this.mode==="atlas"?centerZ:distance);this.camera.lookAt(0,0,centerZ);
  }

  private renderHistory():void{
    const canvas=document.querySelector<HTMLCanvasElement>("#neural-rate-history");if(!canvas)return;
    const rows=this.historyIds.length;canvas.width=this.rateHistory.capacity;canvas.height=rows;
    const context=canvas.getContext("2d");if(!context)return;
    const image=context.createImageData(canvas.width,rows),offset=canvas.width-this.rateHistory.samples.length;
    const srgb=(value:number)=>Math.round(255*(value<=.0031308?12.92*value:1.055*Math.pow(value,1/2.4)-.055));
    for(let row=0;row<rows;row++)for(let column=0;column<canvas.width;column++){
      const value=this.rateHistory.samples[column-offset]?.values.get(this.historyIds[row]!);
      const color=value===undefined?[.003,.008,.018]:value===0?[.012,.05,.15]:rateColor(value);
      const index=(row*canvas.width+column)*4;image.data[index]=srgb(color[0]!);image.data[index+1]=srgb(color[1]!);image.data[index+2]=srgb(color[2]!);image.data[index+3]=255;
    }context.putImageData(image,0,0);
    canvas.dataset.samples=String(this.rateHistory.samples.length);canvas.dataset.bodyIds=this.historyIds.join(",");canvas.dataset.lastStep=String(this.lastStep);canvas.dataset.lastElapsed=String(this.elapsed);
    canvas.setAttribute("aria-label",`Received rate heatmap, ${rows} official model cells, ${this.rateHistory.samples.length} sampled timestamps; not spikes`);
    const first=this.rateHistory.samples[0]?.time,last=this.rateHistory.samples.at(-1)?.time;
    const note=document.querySelector("#neural-rate-history-note");if(note)note.textContent=first===undefined?"Waiting for received rate samples":`${rows} model cells · ${first.toFixed(1)}–${last!.toFixed(1)} s · sampled rate, not spikes`;
  }
  private readonly inspectHistory=(event:Event):void=>{
    const canvas=event.currentTarget as HTMLCanvasElement,mouse=event as MouseEvent,rect=canvas.getBoundingClientRect();
    const column=Math.floor((mouse.clientX-rect.left)/rect.width*canvas.width),row=Math.floor((mouse.clientY-rect.top)/rect.height*canvas.height);
    const sample=this.rateHistory.samples[column-(canvas.width-this.rateHistory.samples.length)],id=this.historyIds[row];
    if(sample&&id!==undefined)canvas.title=`Body ${id} · t=${sample.time}s · ${sample.values.has(id)?sample.values.get(id):"UNOBSERVED"} rate`;
  };

  private hit(event:MouseEvent|PointerEvent):ActiveNeuron|undefined{
    const rect=this.renderer.domElement.getBoundingClientRect();
    this.raycaster.setFromCamera(new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,1-(event.clientY-rect.top)/rect.height*2),this.camera);
    const index=this.raycaster.intersectObject(this.highlights)[0]?.index;
    if(index!==undefined&&this.mapped[index])return this.mapped[index]!.neuron;
    if(this.mode==="atlas"&&this.skeletons){
      const hit=this.raycaster.intersectObjects(this.skeletons.children,false)[0];
      if(hit)return this.readings.find(neuron=>neuron.body_id===hit.object.userData.body_id);
    }return undefined;
  }
  private readonly pick=(event:PointerEvent):void=>{const neuron=this.hit(event);if(neuron)this.selection.textContent=`${neuron.label} · ${neuron.body_id} · ${neuron.activity} rate`;};
  private readonly selectPoint=(event:MouseEvent):void=>{const neuron=this.hit(event);if(neuron)document.dispatchEvent(new CustomEvent("neuron-select",{detail:neuron.body_id}));};
  private readonly keydown=(event:KeyboardEvent):void=>{
    if(!["ArrowLeft","ArrowRight","+","=","-"].includes(event.key))return;event.preventDefault();
    if(event.key.startsWith("Arrow"))this.camera.position.applyAxisAngle(this.camera.up,event.key==="ArrowLeft"?.12:-.12);
    else this.camera.position.multiplyScalar(event.key==="-"?1.1:.9).clampLength(.8,8);this.controls.update();
  };
  private resize():void{
    const width=Math.max(1,this.container.clientWidth),height=Math.max(1,this.container.clientHeight);
    this.camera.aspect=width/height;this.camera.updateProjectionMatrix();this.fitCamera();this.controls.update();this.renderer.setSize(width,height,false);
  }
  private render():void{
    if(this.disposed||!this.visible||document.hidden)return;
    this.renderer.render(this.scene,this.camera);
    const now=performance.now();if(now-this.lastStatistics>1000){reportGraphicsStatistics(this.container,this.renderer);this.lastStatistics=now;}
  }
  async dispose():Promise<void>{
    if(this.disposed)return;this.disposed=true;this.resizeObserver.disconnect();this.intersectionObserver.disconnect();this.controls.dispose();
    this.search.removeEventListener("input",this.refresh);this.renderer.domElement.removeEventListener("pointermove",this.pick);this.renderer.domElement.removeEventListener("click",this.selectPoint);this.renderer.domElement.removeEventListener("keydown",this.keydown);
    document.querySelector("#view-atlas")?.removeEventListener("click",this.showAtlas);document.querySelector("#view-circuit")?.removeEventListener("click",this.showCircuit);
    document.querySelector("#neural-live")?.removeEventListener("click",this.showLive);document.querySelector("#neural-cell-colors")?.removeEventListener("click",this.showCellColors);
    document.querySelector("#neural-front")?.removeEventListener("click",this.frontView);document.querySelector("#neural-vnc")?.removeEventListener("click",this.toggleVnc);
    document.querySelector("#neural-rate-history")?.removeEventListener("mousemove",this.inspectHistory);
    for(const button of this.groupButtons.values())button.remove();
    await this.renderer.setAnimationLoop(null);disposeScene(this.scene);this.renderer.domElement.remove();await this.renderer.dispose();
  }
}
