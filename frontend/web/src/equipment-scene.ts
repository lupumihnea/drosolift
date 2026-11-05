import { Group, Vector3,Mesh,MeshStandardMaterial } from "three/webgpu";
import type { EquipmentStation } from "./gym-types";
import { equipmentFrame, equipmentMaterials, equipmentWeight, updateEquipmentLoad, type WeightVisualization } from "./equipment-meshes";
import { worldToScene } from "./scene-math";

interface Apparatus {
  station: EquipmentStation;
  root: Group;
  weight: Group;
  grips: [Vector3,Vector3];
}

/** Geometry and grip targets share one stroke; no autonomous animation clock. */
export class EquipmentScene {
  readonly group = new Group();
  private readonly apparatus = new Map<string,Apparatus>();

  constructor(stations: readonly EquipmentStation[], world: {width:number;height:number}) {
    const materials = equipmentMaterials();
    for (const station of stations) {
      const root = new Group(); root.name = station.id;
      const center = worldToScene(station.x,station.y,world.width,world.height);
      root.position.set(center.x,0,center.z); root.rotation.y = station.heading;
      const weight = equipmentWeight(station,materials); weight.name = `${station.id}-weight`;
      root.add(equipmentFrame(station,materials),weight); this.group.add(root);
      this.apparatus.set(station.id,{station,root,weight,grips:[new Vector3(),new Vector3()]});
      this.sample(station.id,0);
    }
  }

  sample(id: string, position: number): readonly [Vector3,Vector3] | undefined {
    const apparatus = this.apparatus.get(id);
    if (!apparatus) return;
    const {station,root,weight,grips} = apparatus;
    const q = Math.min(1,Math.max(0,position));
    const bench = station.kind === "bench_press";
    const x = bench ? .32 : .45 + .15*Math.sin(Math.PI*q) - .10*q;
    const height = (bench ? .90 : .62) + station.travel*q;
    weight.position.set(x,height,0);
    root.updateWorldMatrix(true,true);
    const side = bench ? -.55 : .50;
    grips[0].set(x,height,side); grips[1].set(x,height,-side);
    root.localToWorld(grips[0]); root.localToWorld(grips[1]);
    return grips;
  }

  /** Absolute received load; pending requests do not enter the visual apparatus. */
  setLoad(id:string,load:number):boolean {
    const apparatus=this.apparatus.get(id);
    if(!apparatus||!Number.isFinite(load)||load<.1||load>3)return false;
    if(apparatus.station.load===load)return true;
    if(!updateEquipmentLoad(apparatus.weight,load))return false;
    apparatus.station={...apparatus.station,load};return true;
  }
  visualLoad(id:string):WeightVisualization|undefined {
    const weight=this.apparatus.get(id)?.weight;if(!weight)return;
    const {load,platesPerStack,totalPlates,stacks}=weight.userData;
    return {load,platesPerStack,totalPlates,stacks};
  }

  resetUnoccupied(occupied: ReadonlySet<string>): void {
    for (const id of this.apparatus.keys()) if (!occupied.has(id)) this.sample(id,0);
  }

  /** Observation filtering never changes station motion or grip transforms. */
  focus(id:string|null):void {
    for(const [key,{root}] of this.apparatus)root.visible=id===null || key===id;
  }

  /** Visible apparatus lamps reflect the exact latched Python sensor input. */
  setFeedback(id:string,left:number|null,right:number|null):void{
    const apparatus=this.apparatus.get(id);if(!apparatus)return;
    for(const [name,value,color] of [["indicator-left",left,"#44dff2"],["indicator-right",right,"#ba9aff"]] as const){
      const lamp=apparatus.root.getObjectByName(name);
      if(!(lamp instanceof Mesh)||!(lamp.material instanceof MeshStandardMaterial))continue;
      const observed=value!==null&&Number.isFinite(value)&&value>=0&&value<=1;
      lamp.userData.receivedValue=observed?value:null;
      lamp.userData.observation=observed?(value>0?"positive":"zero"):"unobserved";
      lamp.material.color.set(observed?color:"#26353e");
      lamp.material.emissive.set(observed?color:"#000000");
      lamp.material.emissiveIntensity=observed?value*3.5:0;
    }
  }

  clearFeedback():void{for(const id of this.apparatus.keys())this.setFeedback(id,null,null);}
}
