import { expect, test } from "bun:test";
import runtime from "../../../data/circuits/gym-v1-runtime.json";
import { activityAppearance, NEURAL_GROUPS, summarizeGroups, atlasConnections, circuitLayout } from "./neural-activity";

test("functional model groups exactly partition official runtime identities without exercise-specialized neurons",()=>{
  const ids=[...new Set(runtime.edges.flatMap(edge=>[edge.body_pre,edge.body_post]))].sort((a,b)=>a-b);
  const grouped=NEURAL_GROUPS.flatMap(group=>group.ids).sort((a,b)=>a-b);
  expect(grouped).toEqual(ids);
  expect(new Set(grouped).size).toBe(grouped.length);
  expect(NEURAL_GROUPS.find(group=>group.id==="visual-left")!.ids).toEqual(runtime.sensory_inputs.vision_left);
  expect(NEURAL_GROUPS.find(group=>group.id==="visual-right")!.ids).toEqual(runtime.sensory_inputs.vision_right);
  expect(NEURAL_GROUPS.some(group=>/bench|curl/i.test(group.label))).toBe(false);
});

test("group means use received observations only and keep zero distinct from absence",()=>{
  const partial=summarizeGroups([{body_id:36800,label:"L2#36800",activity:0}]);
  const visual=partial.find(group=>group.id==="visual-left")!;
  expect(visual.observed).toBe(1);expect(visual.total).toBe(6);expect(visual.mean).toBe(0);
  expect(partial.find(group=>group.id==="visual-right")!.mean).toBeNull();
  expect(activityAppearance(undefined).observation).toBe("unobserved");
  expect(activityAppearance(0).observation).toBe("zero");
  expect(activityAppearance(.000001).observation).toBe("positive");
  expect(activityAppearance(.8).intensity).toBeGreaterThan(activityAppearance(.2).intensity);
});

test("atlas links use only measured endpoints and official structural edges; circuit positions stay explicit",()=>{
  const positions=new Map<number,readonly number[]>([[10030,[1,2,3]],[10442,[4,5,6]]]);
  const links=atlasConnections(positions);
  expect(links).toHaveLength(1);expect(links[0]!.pre).toBe(10030);expect(links[0]!.post).toBe(10442);
  expect(links[0]!.weight).toBe(67);
  const layout=circuitLayout();expect(layout.registration).toBe("authored circuit layout; not atlas anatomy");
  expect(layout.positions.size).toBe(new Set(runtime.edges.flatMap(edge=>[edge.body_pre,edge.body_post])).size);
  expect(positions.size).toBe(2);
});
