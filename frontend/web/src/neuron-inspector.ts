import { filterNeuronReadings } from "./neuron-readings";
import { formatBodyId } from "./snapshot";
import type { ActiveNeuron, FrameMessage } from "./types";

interface NeuronRow {
  element: HTMLLIElement;
  identity: HTMLSpanElement;
  meter: HTMLMeterElement;
  value: HTMLSpanElement;
}

/** Renders only the neuron records received in the current telemetry frame. */
export class NeuronInspector {
  private readonly count: HTMLElement;
  private readonly input: HTMLInputElement;
  private readonly list: HTMLOListElement;
  private readonly state: HTMLElement;
  private readings: readonly ActiveNeuron[] | null = null;
  private readonly rows = new Map<number, NeuronRow>();

  constructor(private readonly root: Document) {
    this.count = required(root, "active-count");
    this.input = required(root, "neuron-search") as HTMLInputElement;
    this.list = required(root, "active-neurons") as HTMLOListElement;
    this.state = required(root, "neuron-state");
    this.input.addEventListener("input", () => this.render());
  }

  update(frame: FrameMessage): void {
    this.readings = frame.neural.active;
    const received = new Set(this.readings.map((neuron) => neuron.body_id));
    for (const id of this.rows.keys()) if (!received.has(id)) this.rows.delete(id);
    const positive = this.readings.filter((neuron) => neuron.activity > 0).length;
    this.count.textContent = `${positive} positive / ${this.readings.length} received`;
    this.render();
  }

  private render(): void {
    if (this.readings === null) {
      this.showState("Waiting for received neural activity…");
      return;
    }

    const filtered = filterNeuronReadings(this.readings, this.input.value);
    if (!filtered.length) {
      this.list.replaceChildren();
      this.showState(this.input.value.trim() ? "No matching readings." : "No readings received.");
      return;
    }

    const allZero = this.readings.every((neuron) => neuron.activity === 0);
    if (allZero) this.showState("All received readings are zero.");
    else this.state.hidden = true;
    let cursor = this.list.firstElementChild;
    for (const neuron of filtered) {
      const row = this.rows.get(neuron.body_id) ?? this.row(neuron);
      if (row.identity.textContent !== neuron.label) {
        row.identity.textContent = neuron.label;
        row.meter.setAttribute("aria-label", `Rate activity for ${neuron.label}`);
      }
      const value = neuron.activity.toString();
      if (row.value.textContent !== value) {
        row.value.textContent = value;
        row.meter.value = Math.min(1, Math.max(0, neuron.activity));
      }
      // Move existing rows only when ordering changes; preserve exact received values.
      if (row.element === cursor) cursor = cursor.nextElementSibling;
      else this.list.insertBefore(row.element, cursor);
    }
    while (cursor) { const next = cursor.nextElementSibling; cursor.remove(); cursor = next; }
  }

  private row(neuron: ActiveNeuron): NeuronRow {
    const item = this.root.createElement("li");
    item.className = "neuron-row";
    item.dataset.bodyId=String(neuron.body_id);item.tabIndex=0;item.setAttribute("role","option");
    const select=()=>this.root.dispatchEvent(new CustomEvent("neuron-select",{detail:neuron.body_id}));
    item.addEventListener("click",select);item.addEventListener("keydown",event=>{if(event.key==="Enter" || event.key===" "){event.preventDefault();select();}});

    const identity = this.root.createElement("span");
    identity.className = "neuron-identity";
    identity.textContent = neuron.label;
    identity.dir = "ltr";

    const bodyId = this.root.createElement("span");
    bodyId.className = "neuron-id";
    bodyId.textContent = formatBodyId(neuron.body_id);
    bodyId.dir = "ltr";

    const meter = this.root.createElement("meter");
    meter.className = "neuron-activity-meter";
    meter.min = 0;
    meter.max = 1;
    meter.value = Math.min(1, Math.max(0, neuron.activity));
    meter.setAttribute("aria-label", `Rate activity for ${neuron.label}`);

    const value = this.root.createElement("span");
    value.className = "neuron-activity-value";
    value.textContent = neuron.activity.toString();
    value.dir = "ltr";
    item.append(identity, bodyId, meter, value);
    const row = {element:item,identity,meter,value};
    this.rows.set(neuron.body_id,row);
    return row;
  }

  private showState(message: string): void {
    if (this.state.textContent !== message) this.state.textContent = message;
    if (this.state.hidden) this.state.hidden = false;
  }
}

function required(root: Document, id: string): HTMLElement {
  const element = root.getElementById(id);
  if (!element) throw new Error(`Missing interface element: ${id}`);
  return element;
}
