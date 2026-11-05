import { DataTexture, LinearFilter, NormalBlending, PointsMaterial, RGBAFormat, Sprite, SpriteMaterial, UnsignedByteType } from "three/webgpu";

/** Original analytic display kernel; no external artwork or inferred anatomy. */
export function neuralGlowTexture():DataTexture{
  const size=64,data=new Uint8Array(size*size*4);
  for(let y=0;y<size;y++)for(let x=0;x<size;x++){
    const radius=Math.hypot((x+.5)/size*2-1,(y+.5)/size*2-1);
    const alpha=radius>=1?0:Math.pow(1-radius,2.4);
    const index=(y*size+x)*4;data[index]=255;data[index+1]=255;data[index+2]=255;data[index+3]=Math.round(alpha*255);
  }
  const texture=new DataTexture(data,size,size,RGBAFormat,UnsignedByteType);texture.magFilter=LinearFilter;texture.minFilter=LinearFilter;texture.needsUpdate=true;
  return texture;
}

export function neuralPointMaterial(texture:DataTexture,size:number,opacity:number,vertexColors=true){
  // WebGPU point primitives are one pixel; a point-map has no reliable billboard UV.
  // Context and skeleton samples therefore use untextured point primitives.
  return new PointsMaterial({size,opacity,vertexColors,transparent:true,depthWrite:false,depthTest:false,
    blending:NormalBlending,toneMapped:false,sizeAttenuation:true});
}

/** Actual camera-facing geometry honors radial UVs on both WebGPU and WebGL2. */
export function neuralSprite(texture:DataTexture,size:number,opacity:number):Sprite{
  const sprite=new Sprite(new SpriteMaterial({map:texture,transparent:true,opacity,depthWrite:false,depthTest:false,
    blending:NormalBlending,toneMapped:false}));
  sprite.scale.setScalar(size);sprite.frustumCulled=false;return sprite;
}
