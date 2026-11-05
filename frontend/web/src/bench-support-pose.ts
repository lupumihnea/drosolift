import { Object3D, Quaternion, Vector3 } from "three/webgpu";

/** Authored resting-limb/wing pose; no force, contact, root or repetition authority. */
export class BenchSupportPose {
  private readonly wings: {node:Object3D;position:Vector3;rotation:Quaternion;side:number}[];
  private readonly legs: {upper:Object3D;lower:Object3D;foot:Object3D;side:number;leg:number}[]=[];

  constructor(rig:Object3D){
    this.wings=(["L","R"] as const).map((name,index)=>{
      const node=rig.getObjectByName(`Wing${name}`)!;
      return {node,position:node.position.clone(),rotation:node.quaternion.clone(),side:index===0 ? -1 : 1};
    });
    for(const leg of [2,3]) for(const [side,suffix] of [[-1,"L"],[1,"R"]] as const){
      this.legs.push({leg,side,upper:rig.getObjectByName(`Leg${leg}Upper${suffix}`)!,
        lower:rig.getObjectByName(`Leg${leg}Lower${suffix}`)!,foot:rig.getObjectByName(`Leg${leg}Foot${suffix}`)!});
    }
  }

  restore():void{
    for(const wing of this.wings){wing.node.position.copy(wing.position);wing.node.quaternion.copy(wing.rotation);}
  }

  apply(bench:boolean):void{
    this.restore();if(!bench)return;
    // Supination turns the walking pose upward. Fold the four free legs toward
    // the cushion instead; these targets are display authoring, not ground IK.
    for(const {upper,lower,foot,side,leg} of this.legs){
      const upperDirection=new Vector3(side*.68,.38,leg===2 ? -.16 : -.38).normalize();
      upper.quaternion.setFromUnitVectors(lower.position.clone().normalize(),upperDirection);
      const lowerWorld=new Quaternion().setFromUnitVectors(foot.position.clone().normalize(),
        new Vector3(side*.12,.83,leg===2 ? .08 : -.20).normalize());
      lower.quaternion.copy(upper.quaternion).invert().multiply(lowerWorld);
    }
    // A lateral fan keeps the membranes visible above the cushion. The wing
    // placement is illustrative and does not claim a biological loaded posture.
    for(const {node,side} of this.wings){
      node.position.y=.67;
      node.rotation.set(-.12,-side*.42,0);
    }
  }
}
