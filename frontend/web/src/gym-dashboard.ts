import type { GymFrame, GymFly } from "./gym-types";
import type { HelloMessage, ConnectionState } from "./types";
import { TrainingHistory } from "./training-history";
import { formatReading } from "./snapshot";

/** Stable per-fly observation; population setup is an explicit apparatus command. */
export class GymDashboard {
  selectedId = "fly-1";
  private readonly form = document.querySelector<HTMLFormElement>("#population-form")!;
  private readonly count = document.querySelector<HTMLInputElement>("#fly-count")!;
  private readonly apply = document.querySelector<HTMLButtonElement>("#apply-population")!;
  private readonly status = document.querySelector<HTMLElement>("#population-status")!;
  private readonly picker = document.querySelector<HTMLElement>("#fly-picker")!;
  private readonly panel = document.querySelector<HTMLElement>("#training-instrument")!;
  private readonly history = new TrainingHistory();
  private connected = false;
  private enabled = false;
  private pending = false;
  private ids = "";

  constructor(onCount: (count: number) => void, private readonly onSelect: (id: string) => void) {
    this.count.addEventListener("invalid", () => {
      const message = this.count.validity.valueMissing
        ? "Enter a fly count."
        : "Enter an integer from 1 to 10.";
      this.count.setCustomValidity(message);
      this.status.textContent = message;
    });
    this.count.addEventListener("input", () => {
      this.count.setCustomValidity("");
      this.status.textContent = "";
    });
    this.form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!this.form.reportValidity() || !this.connected || this.pending) return;
      this.pending = true; this.apply.disabled = true;
      this.status.textContent = "Applying…";
      onCount(this.count.valueAsNumber);
    });
  }
  configure(hello: HelloMessage): void {
    this.enabled = hello.schema !== 1;
    this.form.hidden = !this.enabled; this.picker.hidden = !this.enabled; this.panel.hidden = !this.enabled;
    document.querySelector("#chamber-title")!.textContent = this.enabled ? "The bench press" : "Specimen chamber";
    if (hello.schema !== 1) this.acknowledge(hello.population);
    this.syncDisabled();
  }
  connection(state: ConnectionState): void {
    this.connected = state === "open";
    if (!this.connected) { this.pending = false; this.status.textContent = "Waiting for connection."; }
    this.syncDisabled();
  }
  acknowledge(count: number): void {
    this.pending = false; this.count.value = String(count);
    this.count.setCustomValidity("");
    this.status.textContent = `${count} flies in the gym`;
    this.syncDisabled();
  }
  recorded():void{
    this.connected=false;this.pending=false;this.syncDisabled();
    this.status.textContent="Recorded population · apparatus setup is available in live mode.";
  }
  commandError(): void {
    this.pending = false; this.syncDisabled();
    this.status.textContent = "Enter a count from 1 to 10.";
  }
  update(message: GymFrame): GymFly {
    for (const fly of message.flies) this.history.record(fly.id, message.elapsed, fly.training.association_strength, fly.training.fatigue);
    if (!message.flies.some((fly) => fly.id === this.selectedId)) this.selectedId = message.flies[0]!.id;
    const ids = message.flies.map((fly) => fly.id).join(",");
    if (ids !== this.ids) {
      this.ids = ids;
      this.picker.replaceChildren(...message.flies.map((fly) => this.flyButton(fly.id)));
    }
    this.picker.querySelectorAll<HTMLButtonElement>("button").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.fly === this.selectedId)));
    const selected = message.flies.find((fly) => fly.id === this.selectedId)!;
    this.renderTraining(selected);
    return selected;
  }
  select(id:string):void{this.selectedId=id;this.onSelect(id);}
  private flyButton(id: string): HTMLButtonElement {
    const button = document.createElement("button");
    button.type = "button"; button.dataset.fly = id;
    button.textContent = `Fly ${Number(id.slice(4))}`;
    button.addEventListener("click", () => this.select(id));
    return button;
  }
  private syncDisabled(): void {
    this.count.disabled = !this.enabled || !this.connected || this.pending;
    this.apply.disabled = !this.enabled || !this.connected || this.pending;
  }
  private renderTraining(fly: GymFly): void {
    const training = fly.training;
    const exercise = fly.exercise;
    const apparatus = document.querySelector<HTMLElement>("#exercise-readings")!;
    apparatus.hidden = !exercise;
    if (exercise) {
      const name = exercise.kind === "bench_press" ? "Bench press" : exercise.kind === "bicep_curl" ? "Bicep curl" : "Free movement";
      const phase = {free:"Free",lifting:"Lifting",lowering:"Lowering",recovery:"Recovery"}[exercise.phase];
      document.querySelector("#exercise-name")!.textContent = name;
      document.querySelector("#exercise-phase")!.textContent = phase;
      document.querySelector("#exercise-reps")!.textContent = String(exercise.repetitions);
      document.querySelector("#exercise-recovery")!.textContent = exercise.recovery_remaining > 0 ? `${exercise.recovery_remaining.toFixed(1)} s` : "—";
      this.panel.dataset.exercise = exercise.kind ?? exercise.phase;
      this.panel.dataset.repetitions = String(exercise.repetitions);
    }
    for (const key of ["sets", "effort", "fatigue", "fitness", "reward", "association_strength"] as const) {
      document.getElementById(`gym-${key}`)!.textContent = key === "sets" ? String(training[key]) : formatReading(training[key]);
    }
    (document.querySelector("#gym-progress") as HTMLMeterElement).value = training.set_progress;
    document.querySelector("#gym-progress-value")!.textContent = `${Math.round(training.set_progress * 100)}%`;
    const samples = this.history.forFly(fly.id);
    const first = samples[0]?.time ?? 0, last = samples.at(-1)?.time ?? 0;
    for (const key of ["association", "fatigue"] as const) {
      const coordinates = samples.map((sample) => `${8 + (sample.time - first) / Math.max(1, last - first) * 224},${72 - sample[key] * 64}`).join(" ");
      document.querySelector(`#curve-${key}`)!.setAttribute("points", coordinates);
    }
    document.querySelector("#curve-range")!.textContent = samples.length < 2 ? "Waiting for samples" : `${first.toFixed(0)}–${last.toFixed(0)} s`;
    this.panel.dataset.fly = fly.id;
  }
}
