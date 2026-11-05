import {
  AnimationClip, Bone, BufferGeometry, CylinderGeometry, DoubleSide, Float32BufferAttribute,
  Group, LineBasicMaterial, LineSegments, Mesh, MeshStandardMaterial, MeshPhysicalMaterial,
  Quaternion, QuaternionKeyframeTrack, Shape, ShapeGeometry, SphereGeometry,
  Vector3, Vector2, LatheGeometry, CatmullRomCurve3, DataTexture, RGBAFormat,
  RepeatWrapping, InstancedMesh, Matrix4, Color, CircleGeometry, SRGBColorSpace, type Object3D,
} from "three/webgpu";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";

type Triple=[number,number,number];

/** Original deterministic cuticle texture; not measured pigmentation or anatomy. */
function cuticleTexture(pigment:boolean):DataTexture {
  const width=128,height=256,pixels=new Uint8Array(width*height*4);
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
    const noise=(((x*73856093)^(y*19349663)^(x*y*83492791))>>>0)%31;
    if(pigment){
      const boundary=(y/height*6.2)%1;
      const edge=boundary>.81 ? .47 : boundary>.74 ? .70 : 1;
      const tone=(.70+y/height*.3)*(1+(noise-15)/220)*edge;
      pixels.set([174*tone,111*tone,59*tone,255],(y*width+x)*4);
    }else{
      const value=104+noise;pixels.set([value,value,value,255],(y*width+x)*4);
    }
  }
  const texture=new DataTexture(pixels,width,height,RGBAFormat);texture.wrapS=texture.wrapT=RepeatWrapping;
  if(pigment)texture.colorSpace=SRGBColorSpace;
  texture.needsUpdate=true;return texture;
}

/** Original articulated illustration, with authored microstructure and unchanged bone lengths. */
export function createProceduralFly():GLTF {
  const scene=new Group();scene.name="DrosoLiftFly";
  scene.userData={source:"DrosoLift procedural fly v1",artRevision:2,license:"Apache-2.0",registration:"authored display anatomy"};
  const grain=cuticleTexture(false),pigment=cuticleTexture(true);
  const amber=new MeshPhysicalMaterial({color:"#61412b",roughness:.56,metalness:.04,clearcoat:.22,clearcoatRoughness:.4,bumpMap:grain,bumpScale:.0014});
  const chitin=new MeshPhysicalMaterial({color:"#30231c",roughness:.49,metalness:.03,clearcoat:.20,bumpMap:grain,bumpScale:.001});
  const gold=new MeshPhysicalMaterial({color:"#62482f",roughness:.56,metalness:.06,clearcoat:.3,bumpMap:grain,bumpScale:.001});
  const abdomenMaterial=new MeshPhysicalMaterial({color:"#ffffff",map:pigment,roughness:.46,metalness:.03,clearcoat:.34,clearcoatRoughness:.3,bumpMap:grain,bumpScale:.0013});
  const eye=new MeshPhysicalMaterial({color:"#66101b",roughness:.29,metalness:.06,clearcoat:.5,clearcoatRoughness:.23});
  const facetMaterial=new MeshPhysicalMaterial({color:"#8c1c28",roughness:.55,metalness:.04,clearcoat:.10,clearcoatRoughness:.45});
  const wingMaterial=new MeshPhysicalMaterial({color:"#8d9b9c",roughness:.35,metalness:.03,clearcoat:.65,iridescence:.3,iridescenceIOR:1.3,
    transparent:true,opacity:.14,side:DoubleSide,depthWrite:false});
  const veinMaterial=new LineBasicMaterial({color:"#8b785c",transparent:true,opacity:.52});
  const hairMaterial=new LineBasicMaterial({color:"#9b7955",transparent:true,opacity:.7});
  const sphere=new SphereGeometry(1,32,20);
  const segmentGeometry=new CylinderGeometry(.015,.030,1,12);

  function ellipsoid(parent:Object3D,name:string,at:Triple,size:Triple,material:MeshStandardMaterial=amber,geometry:BufferGeometry=sphere):Mesh{
    const mesh=new Mesh(geometry,material);mesh.name=name;mesh.position.set(...at);mesh.scale.set(...size);parent.add(mesh);return mesh;
  }
  function segment(parent:Object3D,end:Vector3,material:MeshStandardMaterial=gold,radius=1):void{
    const mesh=new Mesh(segmentGeometry,material);mesh.position.copy(end).multiplyScalar(.5);
    mesh.quaternion.setFromUnitVectors(new Vector3(0,1,0),end.clone().normalize());mesh.scale.set(radius,end.length(),radius);parent.add(mesh);
  }
  function lines(parent:Object3D,points:number[],material=hairMaterial):void{
    parent.add(new LineSegments(new BufferGeometry().setAttribute("position",new Float32BufferAttribute(points,3)),material));
  }
  // A continuous tapered shell replaces separate spherical rings. Pigment bands
  // live on the same smooth surface and cannot separate under a supported pose.
  const profile=new CatmullRomCurve3([
    new Vector3(.025,-1.10,0),new Vector3(.145,-1.00,0),new Vector3(.255,-.83,0),
    new Vector3(.315,-.62,0),new Vector3(.325,-.41,0),new Vector3(.28,-.20,0),new Vector3(.16,-.04,0),
  ]).getPoints(56).map(point=>new Vector2(Math.max(.015,point.x),point.y));
  const abdomen=new Mesh(new LatheGeometry(profile,48).rotateX(Math.PI/2),abdomenMaterial);
  abdomen.name="Abdomen";abdomen.position.y=.55;abdomen.scale.y=.82;scene.add(abdomen);
  ellipsoid(scene,"Thorax",[0,.60,.12],[.30,.275,.37],amber);
  ellipsoid(scene,"Scutellum",[0,.76,-.09],[.205,.12,.15],gold);
  for(const side of [-1,1])ellipsoid(scene,`ThoracicLobe${side}`,[side*.25,.53,.10],[.085,.17,.21],chitin);
  const dorsal:number[]=[];
  for(const x of [-.095,.095])for(let i=0;i<23;i++){
    const z=-.10+i*.016,y=.60+.276*Math.sqrt(Math.max(0,1-((z-.12)/.38)**2));
    dorsal.push(x,y,z,x,y+.002,z+.016);
  }
  lines(scene,dorsal,new LineBasicMaterial({color:"#39281e",transparent:true,opacity:.8}));
  const head=new Bone();head.name="Head";head.position.set(0,.61,.65);scene.add(head);
  ellipsoid(head,"HeadSurface",[0,0,0],[.205,.215,.185],gold);
  ellipsoid(head,"FacePlate",[0,-.02,.175],[.064,.125,.022],amber);
  for(const [suffix,side] of [["L",-1],["R",1]] as const){
    const center=new Vector3(side*.218,.006,.025),radii=new Vector3(.145,.213,.187);
    ellipsoid(head,`Eye${suffix}`,center.toArray() as Triple,radii.toArray() as Triple,eye);
    const bands=32,columns=32,count=bands*columns;
    const facets=new InstancedMesh(new CircleGeometry(1,6),facetMaterial,count);
    facets.name=`EyeFacets${suffix}`;
    const matrix=new Matrix4(),orientation=new Quaternion(),scale=new Vector3(),position=new Vector3(),normal=new Vector3();
    let index=0;
    for(let row=0;row<bands;row++)for(let col=0;col<columns;col++){
      const phi=(row+.5)/bands*Math.PI,theta=(-.49+(col+.5+(row%2)*.35)/columns)*Math.PI*.96;
      normal.set(side*Math.sin(phi)*Math.cos(theta),Math.cos(phi),Math.sin(phi)*Math.sin(theta));
      position.copy(normal).multiply(radii).add(center).addScaledVector(normal,.0015);
      const surfaceNormal=normal.clone().divide(radii).normalize();orientation.setFromUnitVectors(new Vector3(0,0,1),surfaceNormal);
      const radius=.0108*(.75+.25*Math.sin(phi));scale.set(radius,radius,1);
      matrix.compose(position,orientation,scale);facets.setMatrixAt(index,matrix);
      facets.setColorAt(index,new Color().setRGB(.70+(row*7+col*3)%17/70,.62+(row+col)%11/80,.64+(row*3+col)%13/90));index++;
    }
    head.add(facets);
  }
  const proboscis=new Bone();proboscis.name="Proboscis";proboscis.position.set(0,-.14,.20);head.add(proboscis);
  ellipsoid(proboscis,"ProboscisSurface",[0,-.02,.035],[.021,.023,.040],chitin);
  for(const side of [-1,1])ellipsoid(head,`Palp${side}`,[side*.033,-.11,.179],[.012,.025,.039],gold);
  for(const side of [-1,1]){
    const antenna=new Group();antenna.position.set(side*.085,.115,.19);head.add(antenna);
    segment(antenna,new Vector3(side*.035,.055,.065),gold,.38);
    ellipsoid(antenna,`Antenna${side}`,[side*.035,.055,.065],[.025,.037,.040],chitin);
    const arista:number[]=[];const start=new Vector3(side*.035,.085,.070),end=new Vector3(side*.11,.16,.13);
    arista.push(...start.toArray(),...end.toArray());
    for(let i=1;i<6;i++){const p=start.clone().lerp(end,i/7);arista.push(...p.toArray(),p.x+side*.018,p.y+.012,p.z-.017);}
    lines(antenna,arista);
  }

  for(const [suffix,side] of [["L",-1],["R",1]] as const){
    const wing=new Group();wing.name=`Wing${suffix}`;wing.position.set(side*.13,.85,.12);
    const shape=new Shape();shape.moveTo(0,0);
    shape.bezierCurveTo(side*.22,-.05,side*.55,-.40,side*.56,-.72);
    shape.bezierCurveTo(side*.58,-.96,side*.40,-1.14,side*.23,-1.15);
    shape.bezierCurveTo(side*.06,-1.15,side*.005,-.58,0,0);
    const geometry=new ShapeGeometry(shape,32).rotateX(Math.PI/2);
    const membrane=new Mesh(geometry,wingMaterial);membrane.name=`WingMembrane${suffix}`;wing.add(membrane);
    const veins:number[]=[];
    const edge=shape.getPoints(48).map(p=>new Vector3(p.x,.002,p.y));
    for(let i=0;i<edge.length-1;i++)veins.push(...edge[i]!.toArray(),...edge[i+1]!.toArray());
    for(const path of [
      [[0,0],[.12,-.31],[.18,-.73],[.23,-1.14]],
      [[0,0],[.24,-.30],[.37,-.69],[.42,-1.03]],
      [[.015,-.02],[.30,-.27],[.47,-.54],[.55,-.76]],
    ]){
      const curve=new CatmullRomCurve3(path.map(([x,z])=>new Vector3(side*x!,.003,z!))).getPoints(24);
      for(let i=0;i<curve.length-1;i++)veins.push(...curve[i]!.toArray(),...curve[i+1]!.toArray());
    }
    for(const [x1,z1,x2,z2] of [[.13,-.48,.32,-.47],[.18,-.78,.42,-.78],[.32,-.47,.46,-.49]])veins.push(side*x1!,.004,z1!,side*x2!,.004,z2!);
    lines(wing,veins,veinMaterial);scene.add(wing);
  }

  const tracks:QuaternionKeyframeTrack[]=[];
  for(const [suffix,side] of [["L",-1],["R",1]] as const)for(let leg=1;leg<=3;leg++){
    const z=.29-(leg-1)*.25;
    const upper=new Bone();upper.name=`Leg${leg}Upper${suffix}`;upper.position.set(side*.22,.48,z);
    const lower=new Bone();lower.name=`Leg${leg}Lower${suffix}`;
    const foot=new Bone();foot.name=`Leg${leg}Foot${suffix}`;
    lower.position.set(side*.40,-.20,leg===1?.17:-.12);foot.position.set(side*.34,-.26,leg===1?.13:-.19);
    upper.add(lower);lower.add(foot);scene.add(upper);
    segment(upper,lower.position,amber,1.13);segment(lower,foot.position,gold,.65);
    segment(foot,new Vector3(side*.065,-.014,.02),chitin,.28);
    ellipsoid(upper,`Coxa${leg}${suffix}`,[0,0,0],[.055,.052,.06],amber);
    ellipsoid(lower,`Joint${leg}${suffix}`,[0,0,0],[.026,.029,.028],chitin);
    for(const [parent,end] of [[upper,lower.position],[lower,foot.position]] as const){
      const setae:number[]=[];
      const across=new Vector3(0,0,1).cross(end).normalize();
      for(let i=1;i<13;i++){
        const p=end.clone().multiplyScalar(i/14),direction=across.clone().multiplyScalar(i%2?.038:-.038).add(new Vector3(0,.012,0));
        setae.push(...p.toArray(),...p.clone().add(direction).toArray());
      }
      lines(parent,setae);
    }
    const values:number[]=[];
    for(let step=0;step<=4;step++){
      const phase=step/4*Math.PI*2+(leg%2===0?Math.PI:0)+(side<0?Math.PI:0);
      values.push(...new Quaternion().setFromAxisAngle(new Vector3(0,1,0),Math.sin(phase)*.22).toArray());
    }
    tracks.push(new QuaternionKeyframeTrack(`${upper.name}.quaternion`,[0,.25,.5,.75,1],values));
  }
  const bristles:number[]=[];
  for(let i=0;i<210;i++){
    const angle=i*2.3999632297,z=-.62+(i%31)/31*1.12;
    const x=Math.cos(angle)*.275,y=.60+Math.sin(angle)*.235;
    bristles.push(x,y,z,x*1.11,y+(y-.60)*.16,z+.025);
  }
  lines(scene,bristles);
  const animations=[new AnimationClip("Walk",1,tracks),new AnimationClip("Feed",1,[
    new QuaternionKeyframeTrack("Proboscis.quaternion",[0,.5,1],[0,0,0,1,Math.sin(.20),0,0,Math.cos(.20),0,0,0,1]),
  ])];
  scene.updateMatrixWorld(true);
  return {scene,scenes:[scene],animations,cameras:[],asset:{version:"2.0",generator:"DrosoLift original procedural fly, art revision2"},userData:{}} as unknown as GLTF;
}
