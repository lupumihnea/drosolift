import {expect,test} from 'bun:test';
import {Vector3} from 'three/webgpu';
import {AnimatedFly} from './animated-fly';
import {loadFlyModel} from './fly-model';
import {curlSupportHeight} from './equipment-meshes';

test('the four free curl feet meet their authored sloped supports without moving root or grips',async()=>{
  const fly=new AnimatedFly(await loadFlyModel());
  for(const q of [0,.5,1]){
    const x=.45+.15*Math.sin(Math.PI*q)-.1*q,y=.62+.55*q;
    const targets:[Vector3,Vector3]=[new Vector3(x,y,.5),new Vector3(x,y,-.5)];
    fly.sample(0,false,0,{station_id:'station-2',kind:'bicep_curl',phase:'lifting',joint_position:q,joint_velocity:0,repetitions:0,completed_sets:0,rep_in_set:0,recovery_remaining:0,body_elevation:.5,body_pitch:.55,body_roll:0},targets);
    for(const leg of [2,3])for(const side of ['L','R']){
      const foot=fly.group.getObjectByName(`Leg${leg}Foot${side}`)!.getWorldPosition(new Vector3());
      expect(Math.abs(foot.y-curlSupportHeight(foot.x))).toBeLessThan(.005);
      expect(Math.abs(Math.abs(foot.z)-1.02)).toBeLessThan(.02);
    }
    for(const [i,side] of ['L','R'].entries())expect(fly.group.getObjectByName(`Leg1Foot${side}`)!.getWorldPosition(new Vector3()).distanceTo(targets[i]!)).toBeLessThan(.001);
    expect(fly.group.position.toArray()).toEqual([0,0,0]);
  }
  fly.dispose();
});
