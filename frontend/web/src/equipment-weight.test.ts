import {expect,test} from 'bun:test';
import {Vector3} from 'three/webgpu';
import {EquipmentScene} from './equipment-scene';
import {visualPlateCount} from './equipment-meshes';
import type {EquipmentStation} from './gym-types';
import {disposeScene} from './scene-primitives';

const stations:EquipmentStation[]=[{id:'station-1',kind:'bench_press',x:2,y:-1,heading:.2,load:.6,travel:.7,grip_radius:.45},{id:'station-2',kind:'bicep_curl',x:-2,y:1,heading:.5,load:.4,travel:.55,grip_radius:.45}];
test('an applied 0.2 load step adds symmetric discs without moving a bar or its grip targets',()=>{
  const equipment=new EquipmentScene(stations,{width:20,height:12});
  for(const station of stations){
    const grips=equipment.sample(station.id,.43)!.map(p=>p.clone());
    const weight=equipment.group.getObjectByName(`${station.id}-weight`)!;
    const position=weight.position.clone();
    const before=equipment.visualLoad(station.id)!;
    expect(equipment.setLoad(station.id,station.load+.2)).toBe(true);
    const after=equipment.visualLoad(station.id)!;
    expect(after.platesPerStack).toBe(before.platesPerStack+1);
    expect(after.totalPlates-before.totalPlates).toBe(station.kind==='bench_press'?2:4);
    expect(weight.position.distanceTo(position)).toBe(0);
    const again=equipment.sample(station.id,.43)!;
    again.forEach((p,i)=>expect(p.distanceTo(grips[i]!)).toBeLessThan(1e-9));
    expect(station.load).toBe(station.id==='station-1'?.6:.4);
  }
  disposeScene(equipment.group);
});
test('plate representation is bounded, stable under retries and refuses nonfinite loads',()=>{
  expect(visualPlateCount(.1)).toBe(1);expect(visualPlateCount(.6)).toBe(3);expect(visualPlateCount(.8)).toBe(4);expect(visualPlateCount(3)).toBe(15);
  const equipment=new EquipmentScene(stations,{width:20,height:12});
  equipment.setLoad('station-2',3);const before=equipment.visualLoad('station-2');
  equipment.setLoad('station-2',3);expect(equipment.visualLoad('station-2')).toEqual(before);
  expect(equipment.setLoad('station-2',NaN)).toBe(false);expect(equipment.visualLoad('station-2')).toEqual(before);
  expect(equipment.setLoad('unknown',.8)).toBe(false);
  const weight=equipment.group.getObjectByName('station-2-weight')!;
  expect(weight.userData.totalPlates).toBe(60);
  disposeScene(equipment.group);
});
