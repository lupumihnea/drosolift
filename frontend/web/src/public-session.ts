export interface PublicSession {run_id:string;resumed:boolean;websocket:"/ws";expires_in:number;max_flies:number}
type Fetcher=(input:string,init?:RequestInit)=>Promise<Response>;

/** Public hosting uses cookie-scoped sessions; no session capability enters a URL. */
export function publicEndpoints(backend:string,pageOrigin:string):{bootstrap:string;websocket:string}{
  const base=new URL(backend||pageOrigin);
  const loopback=["localhost","127.0.0.1","[::1]"].includes(base.hostname);
  if(!["http:","https:"].includes(base.protocol)||(base.protocol!=="https:"&&!loopback)||base.username||base.password||base.pathname!=="/"||base.search||base.hash)throw new Error("Use a secure backend origin without a path or credentials.");
  const websocket=new URL("/ws?controls=1",base);websocket.protocol=base.protocol==="https:"?"wss:":"ws:";
  return {bootstrap:new URL("/api/session",base).href,websocket:websocket.href};
}

export async function openPublicSession(url:string,fetcher:Fetcher=fetch):Promise<PublicSession>{
  const response=await fetcher(url,{method:"POST",credentials:"include",cache:"no-store",redirect:"error"});
  if(!response.ok)throw new Error(response.status===429||response.status===503?"The gym is busy. Please try again shortly.":"Your saved training session could not be opened.");
  const value:unknown=await response.json();
  if(!value||typeof value!=="object")throw new Error("Invalid training session response");
  const s=value as Partial<PublicSession>;
  if(typeof s.run_id!=="string"||!s.run_id||s.run_id.length>128||typeof s.resumed!=="boolean"||s.websocket!=="/ws"||!Number.isFinite(s.expires_in)||s.expires_in!<=0||s.expires_in!>366*86400||s.max_flies!==10)throw new Error("Invalid training session response");
  return s as PublicSession;
}
