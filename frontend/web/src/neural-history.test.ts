import {expect,test} from "bun:test";
import {NeuralRateHistory,brainCropIncludes,rateColor,cellGroupColor} from "./neural-history";

test("rate history preserves timestamps, zeros and missing observations without inventing spikes",()=>{
  const history=new NeuralRateHistory(3);
  history.record(1,[{body_id:10783,label:"DNp09",activity:0}]);
  history.record(1,[{body_id:10783,label:"DNp09",activity:.2}]);
  expect(history.samples).toHaveLength(1);expect(history.samples[0]!.values.get(10783)).toBe(.2);
  expect(history.samples[0]!.values.get(11177)).toBeUndefined();
  for(const time of [2,3,4])history.record(time,[{body_id:10783,label:"DNp09",activity:0}]);
  expect(history.samples.map(sample=>sample.time)).toEqual([2,3,4]);
  history.record(.5,[]);expect(history.samples).toHaveLength(1);expect(history.samples[0]!.values.size).toBe(0);
  history.clear();expect(history.samples).toHaveLength(0);
});

test("brain framing is an explicit source-coordinate crop; cell colors do not encode rates",()=>{
  expect(brainCropIncludes([0,0,-.6])).toBe(true);expect(brainCropIncludes([0,0,.6])).toBe(false);
  const low=rateColor(.01),high=rateColor(1);
  expect(low[2]).toBeGreaterThan(low[0]);expect(high[0]).toBeGreaterThan(high[2]);
  expect(cellGroupColor(36800)).toEqual(cellGroupColor(18571));
  expect(cellGroupColor(36800)).not.toEqual(cellGroupColor(63316));
});
