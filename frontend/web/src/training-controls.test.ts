import {expect,test} from "bun:test";
import {adjustWeight} from "./training-controls";

test("weight buttons move by a visible plate step within authoritative limits",()=>{
  expect(adjustWeight(.6,1)).toBe(.8);
  expect(adjustWeight(.8,-1)).toBe(.6);
  expect(adjustWeight(.1,-1)).toBe(.1);
  expect(adjustWeight(2.9,1)).toBe(3);
  expect(adjustWeight(3,1)).toBe(3);
});

test("invalid received weights never turn into a model command",()=>{
  for(const value of [NaN,Infinity,-Infinity,0,3.1])expect(()=>adjustWeight(value,1)).toThrow();
});
