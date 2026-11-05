import { parseServerMessage } from "./snapshot";
import type { ConnectionState, FrameMessage, HelloMessage, ServerMessage } from "./types";
import type { GymFrame } from "./gym-types";
import { parseControlMessage, type ControlMessage } from "./observatory-state";
import type {ExerciseKind} from "./gym-types";

interface SimulationClientEvents {
  onConnection(state: ConnectionState): void;
  onHello(message: HelloMessage): void;
  onFrame(message: FrameMessage): void;
  onRunning(running: boolean): void;
  onError(code: string): void;
  onGymFrame?(message: GymFrame): void;
  onPopulation?(count: number): void;
  onControl?(message: ControlMessage): void;
  onSessionError?(message:string):void;
}
interface ConnectionOptions {endpoint?:string;beforeConnect?:()=>Promise<void>}

export class SimulationClient {
  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private reconnectAttempt = 0;
  private stopped = false;
  private gymControls=false;
  private generation=0;

  constructor(private readonly events: SimulationClientEvents,private readonly options:ConnectionOptions={}) {}

  connect(): void {
    this.stopped = false;
    this.gymControls=false;
    const generation=++this.generation;
    if(this.reconnectTimer!==null){window.clearTimeout(this.reconnectTimer);this.reconnectTimer=null;}
    this.events.onConnection(this.reconnectAttempt ? "reconnecting" : "connecting");
    const open=()=>{if(!this.stopped&&this.generation===generation)this.openSocket();};
    if(this.options.beforeConnect){
      void Promise.resolve().then(this.options.beforeConnect).then(open,error=>{
        if(this.stopped||this.generation!==generation)return;
        this.handleClose();this.events.onSessionError?.(error instanceof Error?error.message:"Could not open your training session.");
      });
    }else open();
  }

  private openSocket():void{
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(this.options.endpoint??`${protocol}//${window.location.host}/ws?controls=1`);
    this.socket=socket;
    socket.addEventListener("open", () => {if(this.socket===socket)this.handleOpen();});
    socket.addEventListener("message", (event) => {if(this.socket===socket)this.handleMessage(event.data);});
    socket.addEventListener("close", () => {if(this.socket===socket)this.handleClose();});
    socket.addEventListener("error", () => {if(this.socket===socket)socket.close();});
  }

  setRunning(running: boolean): void {
    if (this.socket?.readyState !== WebSocket.OPEN) return;
    this.socket.send(JSON.stringify({ type: "set_running", running, ...(this.gymControls?{command_id:crypto.randomUUID()}:{}) }));
  }

  setLoad(station_id:string, load:number):void {
    if(!this.gymControls || this.socket?.readyState!==WebSocket.OPEN)return;
    this.socket.send(JSON.stringify({type:"set_load",command_id:crypto.randomUUID(),station_id,load}));
  }

  setExercise(fly_id:string,kind:ExerciseKind):void{
    if(!this.gymControls||this.socket?.readyState!==WebSocket.OPEN)return;
    this.socket.send(JSON.stringify({type:"set_exercise",command_id:crypto.randomUUID(),fly_id,kind}));
  }

  setPopulation(count: number): void {
    if (this.socket?.readyState !== WebSocket.OPEN) return;
    this.socket.send(JSON.stringify({type: "set_population", count}));
  }

  disconnect(): void {
    this.stopped = true;
    ++this.generation;
    if (this.reconnectTimer !== null) window.clearTimeout(this.reconnectTimer);
    const socket=this.socket;
    this.socket = null;
    socket?.close();
  }

  private handleOpen(): void {
    this.reconnectAttempt = 0;
    this.events.onConnection("open");
  }

  private handleMessage(raw: unknown): void {
    try {
      if (typeof raw !== "string") throw new Error("Non-text WebSocket message");
      const message=JSON.parse(raw);
      if(message.type === "control_state" || message.type === "command_ack"){
        const control=parseControlMessage(message);this.gymControls=true;this.events.onControl?.(control);
      }
      else this.dispatch(parseServerMessage(message));
    } catch {
      this.stopped = true;
      this.events.onConnection("incompatible");
      this.socket?.close();
    }
  }

  private dispatch(message: ServerMessage): void {
    if (message.type === "hello") this.events.onHello(message);
    if (message.type === "frame") this.events.onFrame(message);
    if (message.type === "gym_frame") this.events.onGymFrame?.(message);
    if (message.type === "population") this.events.onPopulation?.(message.count);
    if (message.type === "running") this.events.onRunning(message.running);
    if (message.type === "error") this.events.onError(message.code);
  }

  private handleClose(): void {
    this.socket = null;
    if (this.stopped) return;
    this.reconnectAttempt += 1;
    this.events.onConnection("reconnecting");
    const delay = Math.min(8_000, 500 * 2 ** (this.reconnectAttempt - 1));
    this.reconnectTimer = window.setTimeout(() => this.connect(), delay);
  }
}
