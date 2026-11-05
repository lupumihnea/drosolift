import {expect,test} from "bun:test";
import {SimulationClient} from "./simulation-client";

test("retired sockets cannot overwrite a reconnected session; extensions require server negotiation",()=>{
  const oldWindow=globalThis.window,oldWebSocket=globalThis.WebSocket;
  const instances:FakeSocket[]=[];const timers:unknown[]=[];const received:string[]=[];
  class FakeSocket extends EventTarget{
    static OPEN=1;readyState=1;sent:string[]=[];
    constructor(public url:string){super();instances.push(this);}
    send(text:string){this.sent.push(text);}
    close(){this.readyState=3;}
    message(value:unknown){this.dispatchEvent(new MessageEvent("message",{data:JSON.stringify(value)}));}
  }
  try{
    globalThis.window={location:{protocol:"http:",host:"localhost"},setTimeout:(callback:unknown)=>{timers.push(callback);return timers.length;},clearTimeout:()=>{}} as unknown as Window & typeof globalThis;
    globalThis.WebSocket=FakeSocket as unknown as typeof WebSocket;
    const client=new SimulationClient({onConnection:s=>received.push(s),onHello:()=>{},onFrame:()=>{},onRunning:()=>received.push("running"),onError:()=>{}});
    client.connect();const first=instances[0]!;first.dispatchEvent(new Event("open"));
    // An old gym schema can request pause without the new command extension.
    first.message({type:"hello",schema:3,backend:"compact",dataset:"male-cns:v1.0",fps:10,world:{width:20,height:12},experiment:"gym",population:1,station:{x:0,y:0,width:1,height:1,resistance:1},equipment:[{id:"station-1",kind:"bench_press",x:0,y:0,heading:0,load:.6,travel:.7,grip_radius:.45}]});
    client.setRunning(false);expect(JSON.parse(first.sent[0]!)).toEqual({type:"set_running",running:false});
    first.message({type:"control_state",protocol:1,run_id:"r",step:0,elapsed:0,loads:[]});
    client.setRunning(true);expect(JSON.parse(first.sent[1]!).command_id).toBeString();
    client.disconnect();client.connect();const second=instances[1]!;second.dispatchEvent(new Event("open"));
    const count=received.length;first.dispatchEvent(new Event("close"));first.message({type:"running",running:false});
    expect(received.length).toBe(count);expect(timers.length).toBe(0);
    client.setRunning(false);expect(JSON.parse(second.sent[0]!)).toEqual({type:"set_running",running:false});
  }finally{globalThis.window=oldWindow;globalThis.WebSocket=oldWebSocket;}
});

test("a public socket waits for session bootstrap and cancelled bootstrap cannot reconnect",async()=>{
  const savedWindow=globalThis.window,savedSocket=globalThis.WebSocket;
  const sockets:string[]=[];let release!:()=>void;
  class Socket extends EventTarget{static OPEN=1;readyState=1;constructor(url:string){super();sockets.push(url);}close(){this.readyState=3;}}
  try{
    globalThis.window={location:{protocol:"http:",host:"localhost"},setTimeout:()=>1,clearTimeout:()=>{}} as unknown as Window & typeof globalThis;
    globalThis.WebSocket=Socket as unknown as typeof WebSocket;
    const client=new SimulationClient({onConnection:()=>{},onHello:()=>{},onFrame:()=>{},onRunning:()=>{},onError:()=>{}},
      {endpoint:"wss://api.example.com/ws?controls=1",beforeConnect:()=>new Promise<void>(resolve=>release=resolve)});
    client.connect();await Promise.resolve();expect(sockets).toHaveLength(0);
    client.disconnect();release();await new Promise(resolve=>setTimeout(resolve,0));expect(sockets).toHaveLength(0);
    client.connect();await Promise.resolve();release();await new Promise(resolve=>setTimeout(resolve,0));
    expect(sockets).toEqual(["wss://api.example.com/ws?controls=1"]);client.disconnect();
  }finally{globalThis.window=savedWindow;globalThis.WebSocket=savedSocket;}
});
