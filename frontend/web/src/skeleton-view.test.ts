import { expect, test } from "bun:test";
import { Group, LineSegments, LineBasicMaterial } from "three/webgpu";
import { parseSkeletonCache, updateSkeletonActivity, skeletonCoordinates } from "./skeleton-view";
import cache from "../public/assets/selected-skeletons.json";

const sample = {schema:1,dataset:"male-cns:v1.0",coordinate_units_nm:8,
  transform:{center:[10,20,30],scale:0.01,display_y_sign:-1},
  skeletons:[{body_id:10783,sha256:"b702c072f0a2ae0ce5531e14a4b7e197f8d13b39ac864ad7fa2c601d129e0d50",
    nodes:[[1,0,10,20,30,2,-1],[2,0,12,24,36,2,1]]}]};

test("skeleton cache preserves native atlas axes and exact parent edges", () => {
  const cache = parseSkeletonCache(sample);
  expect(skeletonCoordinates(cache.skeletons[0]!,cache.transform)).toEqual([0,-0,0,.02,-.04,.06]);
  expect(() => parseSkeletonCache({...sample,coordinate_units_nm:1})).toThrow();
  expect(() => parseSkeletonCache({...sample,skeletons:[{...sample.skeletons[0],nodes:[[1,0,0,0,0,1,999]]}]})).toThrow();
});

test("morphology distinguishes unobserved from received zero and positive rate", () => {
  const group=new Group();const line=new LineSegments(undefined,new LineBasicMaterial());
  line.userData.body_id=10783;group.add(line);
  updateSkeletonActivity(group,[]);
  expect(line.userData.observation).toBe("unobserved");
  updateSkeletonActivity(group,[{body_id:10783,label:"DN",activity:0}]);
  expect(line.userData.observation).toBe("zero");
  const zero=(line.material as LineBasicMaterial).color.clone();
  updateSkeletonActivity(group,[{body_id:10783,label:"DN",activity:.6}]);
  expect(line.userData.observation).toBe("positive");
  expect((line.material as LineBasicMaterial).color.equals(zero)).toBe(false);
  expect(line.userData.activity).toBe(.6);
});

test("the bounded default morphology collection includes official sensory, relay and descending cells",()=>{
  const parsed=parseSkeletonCache(cache);
  expect(parsed.skeletons.map(s=>s.body_id).sort((a,b)=>a-b)).toEqual([10702,10783,11177,36800,63316,67052,80841,201965]);
  expect(parsed.skeletons.reduce((sum,s)=>sum+s.nodes.length,0)).toBeLessThan(60000);
});
