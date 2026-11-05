import {expect,test} from "bun:test";
import {FlyPopulation} from "./fly-population";
import {createProceduralFly} from "./procedural-fly";
import type {GymFrame} from "./gym-types";

test("an acknowledged station setup snaps to its received anchor before grip interpolation",async()=>{
  const recorded=await Bun.file(new URL("../public/samples/bench.json",import.meta.url)).json();
  const first=(recorded.frames[1] as GymFrame).flies[0]!;
  const population=new FlyPopulation(createProceduralFly());
  population.update([first],{width:20,height:12});population.render(1,false);
  const moved=structuredClone(first);moved.frame.step++;
  moved.frame.body={x:-3.2,y:-2,heading:.34};
  moved.exercise={...moved.exercise!,station_id:"station-2",kind:"bicep_curl",joint_position:0,body_elevation:.5,body_pitch:.55,body_roll:0};
  population.update([moved],{width:20,height:12});population.render(.01,false);
  expect(population.selected!.position.x).toBeCloseTo(-3.2,10);
  expect(population.selected!.position.z).toBeCloseTo(2,10);
  expect(population.selected!.rotation.y).toBeCloseTo(.34,10);
  population.dispose();
});
