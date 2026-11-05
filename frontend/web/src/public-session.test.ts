import {expect,test} from "bun:test";
import {publicEndpoints,openPublicSession} from "./public-session";

test("public session bootstrap uses credentials and keeps its websocket on the configured service",async()=>{
  const urls=publicEndpoints("https://api.example.com","https://app.example.com");
  expect(urls.bootstrap).toBe("https://api.example.com/api/session");
  expect(urls.websocket).toBe("wss://api.example.com/ws?controls=1");
  let options:RequestInit|undefined;
  const session=await openPublicSession(urls.bootstrap,async(_url,init)=>{options=init;return new Response(JSON.stringify({run_id:"restored-run",resumed:true,websocket:"/ws",expires_in:2592000,max_flies:10}),{status:200});});
  expect(options?.method).toBe("POST");expect(options?.credentials).toBe("include");
  expect(session.resumed).toBe(true);expect(session.run_id).toBe("restored-run");
});

test("backend endpoints reject insecure remote URLs, credentials, paths and redirects",async()=>{
  for(const value of ["http://api.example.com",["https:","//a:b","@example.com"].join(""),"https://example.com/api","https://example.com/?token=x"]){
    expect(()=>publicEndpoints(value,"https://app.example.com")).toThrow();
  }
  expect(publicEndpoints("","https://app.example.com").websocket).toBe("wss://app.example.com/ws?controls=1");
  expect(publicEndpoints("http://127.0.0.1:8003","http://127.0.0.1:5173").bootstrap).toContain(":8003/api/session");
  await expect(openPublicSession("https://example.com/api/session",async()=>new Response("busy",{status:503}))).rejects.toThrow("busy");
  await expect(openPublicSession("https://example.com/api/session",async()=>new Response('{"run_id":"x","resumed":true,"websocket":"https://other.test/ws","expires_in":9}'))).rejects.toThrow();
});
