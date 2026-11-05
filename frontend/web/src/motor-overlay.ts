import {AdditiveBlending,BufferAttribute,BufferGeometry,Color,Group,InstancedMesh,LineBasicMaterial,LineSegments,Matrix4,Mesh,MeshBasicMaterial,Object3D,SphereGeometry,Vector3} from "three/webgpu";
import {NEURAL_GROUPS,NEURAL_RUNTIME,activityAppearance,GROUP_BY_BODY} from "./neural-activity";
import type {FrameMessage} from "./types";

const NAMES=["Head","Thorax","Leg1UpperL","Leg1LowerL","Leg1FootL","Leg1UpperR","Leg1LowerR","Leg1FootR"];
const LINKS=[[0,1],[1,2],[2,3],[3,4],[1,5],[5,6],[6,7]];
const BODY_IDS=[...new Set(NEURAL_GROUPS.flatMap(group=>group.ids))].sort((a,b)=>a-b);

/** A stable illustrative head layout. These positions are not measured somata or registered anatomy. */
function bodyLayout(id:number):Vector3{
  const group=GROUP_BY_BODY.get(id),side=group==="visual-left"?-1:group==="visual-right"?1:id%2?-1:1;
  const angle=(id%997)*2.3999632297,phase=((id*13)%97)/97;
  const center=group==="gym-cue"?new Vector3(0,-.06,.065):group==="food-odor"?new Vector3(0,.04,.08):group==="descending"?new Vector3(0,-.115,-.025):new Vector3(side*.085,.025,-.018);
  return center.add(new Vector3(Math.cos(angle)*.044,Math.sin(angle)*.064,(phase-.5)*.095));
}

/** Actual compact rates and official structural edges on an explicitly authored body overlay. */
export class MotorOverlay{
  readonly group=new Group();
  readonly positions=new BufferGeometry();
  private readonly lineMaterial=new LineBasicMaterial({color:"#78dff7",transparent:true,opacity:.65,depthTest:false,depthWrite:false,blending:AdditiveBlending,toneMapped:false});
  private readonly markerMaterial=new MeshBasicMaterial({color:"#83e8ff",transparent:true,opacity:.8,depthTest:false,depthWrite:false,blending:AdditiveBlending,toneMapped:false});
  private readonly markerGeometry=new SphereGeometry(.018,8,6);
  private readonly markers:Mesh[]=[];
  private readonly points=NAMES.map(()=>new Vector3());
  private readonly brain=new Group();
  private readonly ganglion:Mesh;
  private readonly shellGeometry=new SphereGeometry(1,24,16);
  private readonly shellMaterial=new MeshBasicMaterial({color:"#1679d3",transparent:true,opacity:.22,depthTest:false,depthWrite:false,blending:AdditiveBlending,toneMapped:false});
  private readonly cellGeometry=new SphereGeometry(.0095,8,6);
  private readonly cellMaterial=new MeshBasicMaterial({color:"#ffffff",depthTest:false,depthWrite:false,toneMapped:false});
  private readonly cells=new InstancedMesh(this.cellGeometry,this.cellMaterial,BODY_IDS.length);
  private readonly neuralGeometry=new BufferGeometry();
  private readonly neuralMaterial=new LineBasicMaterial({vertexColors:true,transparent:true,opacity:.12,depthTest:false,depthWrite:false,blending:AdditiveBlending,toneMapped:false});
  private readonly layout=new Map(BODY_IDS.map(id=>[id,bodyLayout(id)]));
  private readonly worldCells=new Map(BODY_IDS.map(id=>[id,new Vector3()]));
  private readonly matrix=new Matrix4();
  private readonly color=new Color();
  private enabled=false;

  constructor(){
    this.group.name="received-neural-body-overlay";
    this.group.userData.registration="authored body placement of compact cells and actuator routes; not measured or validated anatomical registration";
    this.group.userData.structuralEdges=NEURAL_RUNTIME.edges.map(edge=>[edge.body_pre,edge.body_post,edge.weight]);
    this.group.userData.scope=BODY_IDS.length;
    this.group.userData.displayGain=.75;
    this.positions.setAttribute("position",new BufferAttribute(new Float32Array(LINKS.length*6),3));
    const routes=new LineSegments(this.positions,this.lineMaterial);routes.name="engineered-actuator-routes";routes.frustumCulled=false;routes.renderOrder=10;this.group.add(routes);
    for(let i=0;i<NAMES.length;i++){const marker=new Mesh(this.markerGeometry,this.markerMaterial);marker.renderOrder=11;this.markers.push(marker);this.group.add(marker);}
    this.brain.name="illustrative-brain-envelope";this.brain.matrixAutoUpdate=false;
    this.brain.userData.note="Original bilateral envelope illustration; not specimen morphology or simulated neuron positions";
    for(const side of [-1,1]){const lobe=new Mesh(this.shellGeometry,this.shellMaterial);lobe.position.set(side*.093,.02,-.01);lobe.scale.set(.12,.14,.11);lobe.renderOrder=7;this.brain.add(lobe);}
    const bridge=new Mesh(this.shellGeometry,this.shellMaterial);bridge.scale.set(.052,.10,.075);bridge.renderOrder=7;this.brain.add(bridge);this.group.add(this.brain);
    this.ganglion=new Mesh(this.shellGeometry,this.shellMaterial);this.ganglion.scale.set(.07,.045,.09);this.ganglion.renderOrder=7;this.group.add(this.ganglion);
    this.cells.name="compact-rate-cells";this.cells.frustumCulled=false;this.cells.renderOrder=12;this.cells.userData.bodyIds=BODY_IDS;this.group.add(this.cells);
    this.neuralGeometry.setAttribute("position",new BufferAttribute(new Float32Array(NEURAL_RUNTIME.edges.length*6),3));
    this.neuralGeometry.setAttribute("color",new BufferAttribute(new Float32Array(NEURAL_RUNTIME.edges.length*6),3));
    const edges=new LineSegments(this.neuralGeometry,this.neuralMaterial);edges.name="official-edges-authored-body-layout";edges.frustumCulled=false;edges.renderOrder=9;this.group.add(edges);
    this.group.visible=false;
  }
  setEnabled(value:boolean):void{this.enabled=value;if(!value)this.group.visible=false;}

  update(rig:Object3D|null,frame:FrameMessage|null):void{
    this.group.visible=this.enabled&&rig!==null&&frame!==null;
    const drive=frame?.motor.forward??null;
    Object.assign(this.group.userData,{sourceStep:frame?.step??null,sourceElapsed:frame?.elapsed??null,activity:drive,observation:drive===null?"unobserved":drive>0?"positive":"zero",observed:0,positive:0});
    if(!this.group.visible||!rig||!frame)return;
    rig.updateWorldMatrix(true,true);
    for(let i=0;i<NAMES.length;i++){
      const joint=rig.getObjectByName(NAMES[i]!);if(!joint){this.group.visible=false;return;}
      joint.getWorldPosition(this.points[i]!);this.markers[i]!.position.copy(this.points[i]!);
    }
    const head=rig.getObjectByName("Head")!;this.brain.matrix.copy(head.matrixWorld);this.brain.matrixWorldNeedsUpdate=true;this.ganglion.position.copy(this.points[1]!);
    const byId=new Map(frame.neural.active.map(reading=>[reading.body_id,reading.activity]));
    const readings=BODY_IDS.map((id,index)=>{
      const point=this.worldCells.get(id)!.copy(this.layout.get(id)!);head.localToWorld(point);
      this.cells.setMatrixAt(index,this.matrix.makeTranslation(point.x,point.y,point.z));
      const value=byId.get(id),appearance=activityAppearance(value);
      this.color.setRGB(appearance.color[0]!,appearance.color[1]!,appearance.color[2]!).multiplyScalar(appearance.intensity*.75);this.cells.setColorAt(index,this.color);
      if(value!==undefined){this.group.userData.observed++;if(value>0)this.group.userData.positive++;}
      return {body_id:id,value:value??null,observation:appearance.observation,step:frame.step,elapsed:frame.elapsed};
    });
    this.cells.instanceMatrix.needsUpdate=true;if(this.cells.instanceColor)this.cells.instanceColor.needsUpdate=true;this.cells.userData.readings=readings;
    const neuralPosition=this.neuralGeometry.getAttribute("position"),neuralColor=this.neuralGeometry.getAttribute("color");
    NEURAL_RUNTIME.edges.forEach((edge,index)=>{
      [edge.body_pre,edge.body_post].forEach((id,endpoint)=>{
        const p=this.worldCells.get(id)!;neuralPosition.setXYZ(index*2+endpoint,p.x,p.y,p.z);
        const appearance=activityAppearance(byId.get(id));this.color.setRGB(appearance.color[0]!,appearance.color[1]!,appearance.color[2]!).multiplyScalar(appearance.intensity*.75);
        neuralColor.setXYZ(index*2+endpoint,this.color.r,this.color.g,this.color.b);
      });
    });
    neuralPosition.needsUpdate=true;neuralColor.needsUpdate=true;
    const routes=this.positions.getAttribute("position");
    LINKS.forEach((link,index)=>link.forEach((joint,endpoint)=>{const p=this.points[joint]!;routes.setXYZ(index*2+endpoint,p.x,p.y,p.z);}));routes.needsUpdate=true;
    const appearance=activityAppearance(drive??undefined);this.color.setRGB(appearance.color[0]!,appearance.color[1]!,appearance.color[2]!);
    this.lineMaterial.color.copy(this.color);this.markerMaterial.color.copy(this.color);
    this.lineMaterial.opacity=.10+.60*appearance.intensity;this.markerMaterial.opacity=.15+.70*appearance.intensity;
    this.group.userData.note="Cell brightness/color are received normalized rate activity; edge IDs are official, their routes and brain envelope are illustrative. Actuator routes use received motor.forward. No spike events or propagation timing.";
  }
  dispose():void{
    this.positions.dispose();this.lineMaterial.dispose();this.markerGeometry.dispose();this.markerMaterial.dispose();
    this.shellGeometry.dispose();this.shellMaterial.dispose();this.cellGeometry.dispose();this.cellMaterial.dispose();this.neuralGeometry.dispose();this.neuralMaterial.dispose();
  }
}
