import {expect,test} from 'bun:test';
import {Group,Object3D,Vector3,InstancedMesh} from 'three/webgpu';
import {MotorOverlay} from './motor-overlay';
import {NEURAL_GROUPS,NEURAL_RUNTIME} from './neural-activity';
import type {FrameMessage} from './types';
function rig(){const group=new Group();group.position.set(2,1,-3);for(const [i,name] of ['Head','Thorax','Leg1UpperL','Leg1LowerL','Leg1FootL','Leg1UpperR','Leg1LowerR','Leg1FootR'].entries()){const joint=new Object3D();joint.name=name;joint.position.set(i*.1,i*.05,0);group.add(joint);}return group;}
function frame():FrameMessage{return {type:'frame',schema:1,step:12,elapsed:1.2,body:{x:0,y:0,heading:0},food:null,hunger:0,ate:false,sensory:{smell_left:0,smell_right:0,vision_left:0,vision_right:0},motor:{forward:.75,turn:0},neural:{roles:{},active:[{body_id:NEURAL_GROUPS[0]!.ids[0]!,label:'received official cell',activity:.25},{body_id:NEURAL_GROUPS[1]!.ids[0]!,label:'received zero',activity:0}]},trail:[],learning:{reward:0,association_strength:0,mean_eligibility:0,active_kcs:0,changed:false}};}

test('X-ray keeps real IDs, rates and official edges on an explicitly illustrative body layout',()=>{
 const body=rig(),snapshot=frame(),overlay=new MotorOverlay();overlay.setEnabled(true);overlay.update(body,snapshot);
 expect(overlay.group.visible).toBe(true);expect(overlay.group.userData.sourceStep).toBe(12);expect(overlay.group.userData.sourceElapsed).toBe(1.2);
 expect(overlay.group.userData.registration).toContain('authored');expect(overlay.group.userData.observed).toBe(2);expect(overlay.group.userData.positive).toBe(1);
 expect(overlay.group.userData.activity).toBe(.75);
 const cells=overlay.group.getObjectByName('compact-rate-cells') as InstancedMesh;
 expect(cells.userData.readings.find((cell:{body_id:number})=>cell.body_id===snapshot.neural.active[0]!.body_id).value).toBe(.25);
 expect(cells.userData.readings.find((cell:{body_id:number})=>cell.body_id===snapshot.neural.active[1]!.body_id).observation).toBe('zero');
 expect(overlay.group.userData.structuralEdges).toEqual(NEURAL_RUNTIME.edges.map(e=>[e.body_pre,e.body_post,e.weight]));
 const head=body.getObjectByName('Head')!.getWorldPosition(new Vector3());expect(overlay.positions.getAttribute('position').getX(0)).toBeCloseTo(head.x,6);
 const colors=Array.from(cells.instanceColor!.array);overlay.update(body,snapshot);expect(Array.from(cells.instanceColor!.array)).toEqual(colors);
 snapshot.neural.active=[];overlay.update(body,snapshot);expect(overlay.group.userData.observed).toBe(0);expect(overlay.group.userData.positive).toBe(0);
 expect(cells.userData.readings.every((cell:{observation:string})=>cell.observation==='unobserved')).toBe(true);
 overlay.update(null,null);expect(overlay.group.visible).toBe(false);overlay.dispose();
});
