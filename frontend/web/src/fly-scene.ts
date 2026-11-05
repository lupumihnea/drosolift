import * as THREE from "three/webgpu";
import { createFood, createOdorHalo, createTrail, disposeScene } from "./scene-primitives";
import { createWorldScene, lightWorld } from "./world-scene";
import { loadFlyModel } from "./fly-model";
import { FlyPopulation } from "./fly-population";
import { createGymStation } from "./gym-scene";
import { EquipmentScene } from "./equipment-scene";
import { createGraphicsRenderer, graphicsBackend,reportGraphicsStatistics } from "./graphics-renderer";
import { SceneCamera } from "./scene-camera";
import { odorHaloScale, worldToScene } from "./scene-math";
import type { FrameMessage, HelloMessage } from "./types";
import type { GymFrame } from "./gym-types";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";
import {RoomEnvironment} from "three/addons/environments/RoomEnvironment.js";
import {MotorOverlay} from "./motor-overlay";
import type {ControlState} from "./observatory-state";

export class FlyScene {
  private readonly scene = new THREE.Scene();
  private readonly cameraRig: SceneCamera;
  private readonly population: FlyPopulation;
  private readonly food = createFood();
  private readonly odor = createOdorHalo();
  private readonly trail = createTrail();
  private readonly resizeObserver: ResizeObserver;
  private readonly motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
  private world = { width: 20, height: 12 };
  private station: THREE.Group | null = null;
  private visible = !document.hidden;
  private running = true;
  private disposed = false;
  private lastTime = 0;
  private lastStatistics=0;
  private focused = false;
  private selectedStation:string|null=null;
  private gymMode=false;
  private readonly stage=createWorldScene();
  private environment:THREE.RenderTarget|null=null;
  private readonly motorOverlay=new MotorOverlay();
  private selectedFrame:FrameMessage|null=null;
  private controlState:ControlState|null=null;

  static async create(container: HTMLElement, onFailure: () => void): Promise<FlyScene> {
    const { renderer, assertHealthy } = await createGraphicsRenderer(new URLSearchParams(location.search).get("renderer") === "webgl", onFailure);
    let scene: FlyScene | null = null;
    try {
      const asset = await loadFlyModel(); assertHealthy();
      scene = new FlyScene(container, renderer, asset);
      await renderer.compileAsync(scene.scene, scene.cameraRig.camera); assertHealthy();
      await renderer.setAnimationLoop((time) => scene?.render(time)); assertHealthy();
      container.dataset.renderer = graphicsBackend(renderer);
      container.dataset.model = "authored-rig";
      return scene;
    } catch (error) {
      if (scene) await scene.dispose(); else await renderer.dispose();
      throw error;
    }
  }

  private constructor(private readonly container: HTMLElement, private readonly renderer: THREE.WebGPURenderer, asset: GLTF) {
    this.cameraRig = new SceneCamera(renderer.domElement, this.motionPreference.matches);
    this.population = new FlyPopulation(asset);
    this.container.prepend(renderer.domElement);
    lightWorld(this.scene);
    const room=new RoomEnvironment(),pmrem=new THREE.PMREMGenerator(renderer);
    this.environment=pmrem.fromScene(room,.04);this.scene.environment=this.environment.texture;this.scene.environmentIntensity=.3;room.dispose();pmrem.dispose();
    this.scene.add(this.stage, this.population.group, this.food, this.odor, this.trail,this.motorOverlay.group);
    this.food.visible = false; this.odor.visible = false;
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container); this.resize();
  }

  get backend(): string { return graphicsBackend(this.renderer); }

  configure(message: HelloMessage): void {
    this.world = message.world;
    this.controlState=null;
    this.gymMode=message.schema!==1;
    this.stage.traverse(node=>{if(node.name==="arena-marking")node.visible=message.schema===1;});
    if (this.station) { this.scene.remove(this.station); disposeScene(this.station); this.station = null; }
    this.population.equipment = null;
    if (message.schema === 3) {
      const equipment = new EquipmentScene(message.equipment!,this.world);
      this.population.equipment = equipment; this.station = equipment.group;
      this.scene.add(this.station);
    } else if (message.schema === 2) {
      this.station = createGymStation(message.station, this.world); this.scene.add(this.station);
    }
  }

  update(frame: FrameMessage): void {
    this.selectedFrame=frame;
    this.population.update([{id: "fly-1", frame}], this.world);
    this.updateSelected(frame);
  }
  updateGym(message: GymFrame, selectedId: string): void {
    const beforeStation=this.selectedStation;
    this.population.selectedId = selectedId;
    this.population.update(message.flies.map((fly) => ({...fly, distance: fly.training.distance})), this.world);
    this.updateSelected(message.flies.find((fly) => fly.id === this.population.selectedId)!.frame);
    this.container.dataset.population = String(message.flies.length);
    this.container.dataset.selectedFly = this.population.selectedId;
    this.selectedStation=message.flies.find(f=>f.id===selectedId)?.exercise?.station_id ?? null;
    this.selectedFrame=message.flies.find(f=>f.id===selectedId)?.frame ?? null;
    if(!this.focused){this.population.render(1,false);this.focusFly();this.focused=true;}
    if(this.cameraRig.mode === "follow")this.population.equipment?.focus(this.selectedStation);
    if(beforeStation!==this.selectedStation&&this.focused&&this.cameraRig.mode==="follow"){this.population.render(1,false);this.focusFly();}
  }

  setRunning(running: boolean): void { this.running = running; }
  setVisible(visible: boolean): void { this.visible = visible; this.lastTime = 0; }
  showOverview(): void { this.cameraRig.overview(); this.population.equipment?.focus(null); this.population.render(1, false); }
  focusFly(): void { if (this.population.selected) this.cameraRig.focusFly(this.population.selected.position); this.population.equipment?.focus(this.selectedStation); this.population.render(1, false); }
  setXray(enabled:boolean):void {
    this.motorOverlay.setEnabled(enabled);
    this.population.group.traverse(node=>{
      if(!(node instanceof THREE.Mesh))return;
      const materials=Array.isArray(node.material)?node.material:[node.material];
      for(const material of materials){
        if(material.userData.baseOpacity===undefined){material.userData.baseOpacity=material.opacity;material.userData.baseTransparent=material.transparent;material.userData.baseDepthWrite=material.depthWrite;}
        const opacity=node.name.startsWith("Eye")?.18:node.name.startsWith("Wing")?Math.min(.08,material.userData.baseOpacity):.09;
        material.opacity=enabled?opacity:material.userData.baseOpacity;
        material.transparent=enabled||material.userData.baseTransparent;
        material.depthWrite=enabled?false:material.userData.baseDepthWrite;
        material.needsUpdate=true;
      }
    });
    this.container.dataset.overlayRegistration=this.motorOverlay.group.userData.registration;
  }
  setControlState(state:ControlState):void{
    this.controlState=state;
    const equipment=this.population.equipment;if(!equipment)return;
    for(const load of state.loads)equipment.setLoad(load.station_id,load.load);
    equipment.clearFeedback();
    for(const feedback of state.feedback ?? []){
      const setup=state.exercises?.find(row=>row.fly_id===feedback.fly_id);
      if(setup?.station_id&&feedback.profile==="apparatus-visual-v1")equipment.setFeedback(setup.station_id,feedback.indicator_left,feedback.indicator_right);
    }
    this.updateVisualMetadata();
  }
  private updateVisualMetadata():void{
    const load=this.selectedStation?this.population.equipment?.visualLoad(this.selectedStation):undefined;
    this.container.dataset.appliedLoad=load?String(load.load):"";
    this.container.dataset.plateCount=String(load?.platesPerStack??0);
    this.container.dataset.totalPlateCount=String(load?.totalPlates??0);
    this.container.dataset.weightVisualization=JSON.stringify({station_id:this.selectedStation,...load});
    this.container.dataset.overlayObserved=String(this.motorOverlay.group.userData.observed??0);
    this.container.dataset.overlayPositive=String(this.motorOverlay.group.userData.positive??0);
    this.container.dataset.overlayRegistration=this.motorOverlay.group.userData.registration;
  }
  showEyeView(): void {
    const fly = this.population.selected;
    if (fly) this.cameraRig.eyeView(fly.position, fly.rotation.y, this.population.selectedEye);
    this.population.render(1, true);
  }
  resize(): void {
    const width = Math.max(1, this.container.clientWidth), height = Math.max(1, this.container.clientHeight);
    this.cameraRig.resize(width / height); this.renderer.setSize(width, height, false);
  }
  async dispose(): Promise<void> {
    if (this.disposed) return;
    this.disposed = true; this.resizeObserver.disconnect(); this.cameraRig.dispose();
    await this.renderer.setAnimationLoop(null);
    this.population.dispose(); disposeScene(this.scene);
    this.environment?.dispose();
    this.renderer.domElement.remove(); await this.renderer.dispose();
  }

  private updateSelected(frame: FrameMessage): void {
    this.food.visible = frame.food !== null; this.odor.visible = frame.food !== null;
    if (frame.food) {
      const point = worldToScene(frame.food.x, frame.food.y, this.world.width, this.world.height);
      const ground = Math.abs(point.x) <= 10 && Math.abs(point.z) <= 6 ? 0 : -1.3;
      this.food.position.set(point.x, ground, point.z); this.food.scale.setScalar(frame.food.radius);
      this.odor.position.set(point.x, ground + 0.02, point.z);
      this.odor.scale.setScalar(odorHaloScale(Math.max(frame.sensory.smell_left, frame.sensory.smell_right)));
    }
    const positions = this.trail.geometry.getAttribute("position") as THREE.BufferAttribute;
    frame.trail.forEach(([x, y], index) => { const point = worldToScene(x, y, this.world.width, this.world.height); positions.setXYZ(index, point.x, 0.032, point.z); });
    positions.needsUpdate = true; this.trail.geometry.setDrawRange(0, frame.trail.length);
  }

  private render(time: number): void {
    if (this.disposed || !this.visible) return;
    const dt = this.lastTime ? Math.min((time - this.lastTime) / 1000, 0.1) : 0;
    this.lastTime = time;
    // Overview looks through the outer studio shell; remove that authored set
    // dressing so the arena/equipment remain visible from outside the room.
    for(const node of this.stage.children){
      const features=node.userData.features as string[]|undefined;
      if(features?.some(name=>name.startsWith("studio-")))node.visible=this.cameraRig.mode!=="overview";
    }
    this.population.render(this.motionPreference.matches || !this.running ? 1 : 1 - Math.exp(-14 * dt), this.cameraRig.mode === "eye");
    // Actor selection is visual only: all active rigs above still sample their
    // received trajectories, while the chosen station is isolated for review.
    if(this.cameraRig.mode!=="overview")for(const actor of this.population.group.children)if(actor.name!==this.population.selectedId)actor.visible=false;
    this.motorOverlay.update(this.cameraRig.mode!=="eye"&&this.selectedStation?this.population.selected ?? null:null,this.selectedFrame);
    this.updateVisualMetadata();
    if(this.gymMode && this.cameraRig.mode!=="overview"){this.food.visible=false;this.odor.visible=false;this.trail.visible=false;}else this.trail.visible=true;
    const fly = this.population.selected;
    if (fly) this.cameraRig.update(fly.position, fly.rotation.y, this.cameraRig.mode === "eye" ? this.population.selectedEye : undefined);
    this.renderer.render(this.scene, this.cameraRig.camera);
    if(time-this.lastStatistics>1000){reportGraphicsStatistics(this.container,this.renderer);this.lastStatistics=time;}
  }
}
