"""Exercise the actual DrosoLift browser and preserve screenshots, telemetry and timing.

This is an audience-flow acceptance check, not a source of simulated states.
Playwright observes real WebSocket frames and clicks the application controls.
The optional backend PID is stopped only after live checks, for offline evidence.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import platform
import signal
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OBSERVE = """
(() => {
  const NativeSocket = window.WebSocket;
  window.__qa = {frames: [], messages: [], sent: [], sockets: [], raf: []};
  window.WebSocket = class extends NativeSocket {
    constructor(...args) {
      super(...args); window.__qa.sockets.push(this);
      this.addEventListener('message', event => {
        const message = JSON.parse(event.data);
        window.__qa.messages.push(message);
        if (window.__qa.messages.length > 1200) window.__qa.messages.shift();
        if (message.type === 'hello') window.__qa.hello = message;
        if (message.type === 'control_state') window.__qa.control = message;
        if (message.type === 'gym_frame') {
          window.__qa.frame = message;
          window.__qa.frames.push(message);
          if (window.__qa.frames.length > 1200) window.__qa.frames.shift();
        }
        if (message.type === 'running') window.__qa.running = message.running;
      });
    }
    send(raw) { window.__qa.sent.push(JSON.parse(raw)); return super.send(raw); }
  };
  const nativeRAF = window.requestAnimationFrame.bind(window);
  const loops = new WeakMap();
  window.requestAnimationFrame = callback => {
    let record = loops.get(callback);
    if (!record) {
      record = {name:callback.name,source:callback.toString().slice(0,100),times:[]};
      loops.set(callback,record);window.__qa.raf.push(record);
    }
    return nativeRAF(time => {
      record.times.push(time);if(record.times.length>4000)record.times.shift();
      callback(time);
    });
  };
})();
"""


def until(page: Page, expression: str, timeout: int = 90_000) -> None:
    page.wait_for_function(expression, timeout=timeout)


def ready(page: Page, url: str, *, graphics: bool = True) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
    until(page, "!document.querySelector('#running-toggle').disabled")
    if graphics:
        until(page, "document.querySelector('#scene').dataset.model === 'authored-rig'")
        until(page, "document.querySelector('#neuron-map').dataset.anatomy === 'ready'")


def paused(page: Page, value: bool = True) -> None:
    current = page.evaluate("document.body.dataset.running === 'false'")
    if current != value:
        page.locator("#running-toggle").click()
    until(page, f"document.body.dataset.running === '{str(not value).lower()}'")


def capture(page: Page, output: Path, name: str) -> None:
    page.screenshot(path=str(output / name), full_page=False, animations="disabled")


def seek(page:Page, fraction:float) -> None:
    """Use the audience's native range control, then inspect its resulting value."""
    slider=page.locator("#replay-seek");bounds=slider.bounding_box()
    assert bounds
    slider.click(position={"x":max(1,min(bounds["width"]-1,bounds["width"]*fraction)),"y":bounds["height"]/2})


def graphics_info(page: Page) -> dict:
    return page.evaluate("""() => {
      const canvas=document.querySelector('#scene canvas');
      const gl=canvas?.getContext('webgl2');
      const debug=gl?.getExtension('WEBGL_debug_renderer_info');
      return {backend:document.querySelector('#scene').dataset.renderer,
        vendor:debug ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL) : null,
        renderer:debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : null,
        hardwareConcurrency:navigator.hardwareConcurrency,devicePixelRatio,
        sceneCanvas:canvas ? [canvas.width,canvas.height] : null};
    }""")


def live_checks(browser, url: str, output: Path, results: dict) -> None:
    context=browser.new_context(viewport={"width":1280,"height":720},locale="en-US",device_scale_factor=1)
    context.add_init_script(OBSERVE)
    page=context.new_page()
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    ready(page,f"{url}?renderer=webgl")
    until(page,"window.__qa.frame?.flies[0]?.exercise?.station_id")
    results["graphics"]=graphics_info(page)
    assert results["graphics"]["backend"] == "WebGL2"
    until(page,"window.__qa.frame.flies[0].exercise.joint_position > .2 && window.__qa.frame.flies[0].exercise.joint_position < .85")
    paused(page)
    before=page.evaluate("window.__qa.frame")
    before_text=json.dumps(before,sort_keys=True)
    step=before["step"]
    sent=page.evaluate("window.__qa.sent.length")
    page.wait_for_timeout(600)
    assert json.dumps(page.evaluate("window.__qa.frame"),sort_keys=True)==before_text
    assert page.evaluate("window.__qa.control.step")==step
    results["pause"]={"step":step,"elapsed":before["elapsed"],"joint":before["flies"][0]["exercise"]["joint_position"],"frozen_ms":600}

    # Inspect a stable official identity and exact received value through normal UI.
    page.locator(".neuron-details summary").click()
    page.locator('[data-body-id="10783"]').click()
    selected=next(n for n in before["flies"][0]["frame"]["neural"]["active"] if n["body_id"]==10783)
    assert page.locator("#selected-id").inner_text()=="10783"
    assert float(page.locator("#selected-value").inner_text().split()[0])==selected["activity"]
    rows=page.locator("#active-neurons li")
    by_id={n["body_id"]:n for n in before["flies"][0]["frame"]["neural"]["active"]}
    assert rows.count()==len(by_id)
    for row in rows.all():
        body_id=int(row.locator(".neuron-id").inner_text())
        assert row.locator(".neuron-identity").inner_text()==by_id[body_id]["label"]
        assert float(row.locator(".neuron-activity-value").inner_text())==by_id[body_id]["activity"]
    page.locator(".neuron-details summary").click()
    capture(page,output,"workout-1280x720.png")
    page.set_viewport_size({"width":1920,"height":1080});page.wait_for_timeout(350)
    capture(page,output,"workout-1920x1080.png")
    page.locator('[data-tab="neurons"]').click()
    until(page,"document.querySelector('#xray-toggle').getAttribute('aria-pressed') === 'true'")
    for _ in range(4):
        page.locator("#xray-toggle").click()
    until(page,"document.querySelector('#neuron-map').dataset.detail === 'official-skeletons'")
    page.wait_for_timeout(500)
    capture(page,output,"neurons-xray-1920x1080.png")
    page.set_viewport_size({"width":1280,"height":720});page.wait_for_timeout(350)
    capture(page,output,"neurons-xray-1280x720.png")
    for selector,mode in [("#view-overview","overview"),("#view-eye","eye"),("#view-fly","follow")]:
        page.locator(selector).click()
        assert page.locator("#scene").get_attribute("data-camera-mode")==mode
    assert page.evaluate("window.__qa.sent.length")==sent,"Observer controls sent model commands"
    assert json.dumps(page.evaluate("window.__qa.frame"),sort_keys=True)==before_text,"Observer controls changed state"
    results["observer_invariance"]={"camera_modes":3,"xray":True,"rapid_xray_toggles":4,"neuron_id":10783,"all_exact_readings":len(by_id)}
    page.locator('[data-tab="workout"]').click()

    # Apply a load while paused in the middle of a real stroke.
    old_load=page.evaluate("window.__qa.control.loads[0].load")
    new_load=.8 if old_load != .8 else .6
    page.locator("#load-value").fill(str(new_load));page.locator("#apply-load").click()
    until(page,"window.__qa.messages.some(m=>m.type==='command_ack' && m.command==='set_load' && m.status==='pending')")
    pending=page.evaluate("window.__qa.messages.filter(m=>m.type==='command_ack' && m.command==='set_load').at(-1)")
    command=page.evaluate("window.__qa.sent.filter(m=>m.type==='set_load').at(-1)")
    assert pending["effective_step"] is None
    assert page.evaluate("window.__qa.control.loads[0].load")==old_load
    assert page.evaluate("window.__qa.control.loads[0].pending_load")==new_load
    assert "Pending" in page.locator("#control-status").inner_text()
    ack_count=page.evaluate("window.__qa.messages.filter(m=>m.type==='command_ack' && m.command==='set_load').length")
    # Retry the exact UI-issued command on its real connection; no new actuator input.
    page.evaluate("command=>window.__qa.sockets.at(-1).send(JSON.stringify(command))",command)
    until(page,f"window.__qa.messages.filter(m=>m.type==='command_ack' && m.command==='set_load').length > {ack_count}")
    assert page.evaluate("window.__qa.control.loads[0].pending_load")==new_load
    paused(page,False)
    until(page,f"window.__qa.control.loads[0].load === {new_load} && window.__qa.control.loads[0].pending_load === null",120_000)
    until(page,f"window.__qa.messages.some(m=>m.type==='command_ack' && m.command_id==='{command['command_id']}' && m.status==='applied')")
    applied=page.evaluate(f"window.__qa.messages.find(m=>m.type==='command_ack' && m.command_id==='{command['command_id']}' && m.status==='applied')")
    assert applied["effective_step"]>step
    results["load"]={"from":old_load,"to":new_load,"pending":pending,"applied":applied,"duplicate_retry":True}

    # Actual repeated telemetry, a completed return stroke and changing rate values.
    start_reps=before["flies"][0]["exercise"]["repetitions"]
    until(page,f"window.__qa.frame.flies[0].exercise.repetitions > {start_reps}",120_000)
    until(page,"window.__qa.frames.length > 15")
    frames=page.evaluate("window.__qa.frames")
    rates=[{"step":f["step"],"elapsed":f["elapsed"],"body_id":10783,
            "activity":next(n["activity"] for n in f["flies"][0]["frame"]["neural"]["active"] if n["body_id"]==10783),
            "joint_position":f["flies"][0]["exercise"]["joint_position"],"repetitions":f["flies"][0]["exercise"]["repetitions"]} for f in frames]
    assert len({r["activity"] for r in rates})>1,"Selected actual neural value did not change"
    (output/"browser-telemetry.json").write_text(json.dumps({"hello":page.evaluate("window.__qa.hello"),"samples":rates},indent=2),encoding="utf-8")
    results["actual_telemetry"]={"body_id":10783,"sample_count":len(rates),"distinct_rates":len({r["activity"] for r in rates}),
      "rep_start":start_reps,"rep_end":rates[-1]["repetitions"]}
    assert page.locator("#selected-id").inner_text()=="10783","Identity selection changed with rankings"

    # Warm up, then measure presentation callback intervals for the actual render loops.
    page.wait_for_timeout(1500)
    timing_start=page.evaluate("performance.now()")
    page.wait_for_timeout(10_000)
    timing=page.evaluate("""start=>window.__qa.raf.map(record=>{
      const times=record.times.filter(t=>t>=start), gaps=times.slice(1).map((t,i)=>t-times[i]);
      const duration=times.length>1 ? times.at(-1)-times[0] : 0;
      return {name:record.name,source:record.source,frames:times.length,span_ms:duration,
        fps:duration ? (times.length-1)*1000/duration : 0,max_gap_ms:gaps.length?Math.max(...gaps):null};
    })""",timing_start)
    results["performance"]={"viewport":[1280,720],"warmup_ms":1500,"sample_ms":10_000,"loops":timing,
      "qualification":"Observed requestAnimationFrame callbacks in real render loops; GPU completion time not measured."}

    paused(page)
    frozen=page.evaluate("window.__qa.frame")
    frozen_run=page.evaluate("window.__qa.control.run_id")
    page.reload(wait_until="domcontentloaded")
    until(page,"window.__qa.frame && window.__qa.control")
    assert page.evaluate("window.__qa.running") is False
    assert page.evaluate("window.__qa.frame.step")==frozen["step"]
    assert page.evaluate("window.__qa.control.run_id")==frozen_run
    assert page.evaluate("window.__qa.frame.flies[0].exercise")==frozen["flies"][0]["exercise"]
    results["reconnect"]={"paused_step":frozen["step"],"run_id":frozen_run,"exercise_preserved":True}
    until(page,"document.querySelector('#scene').dataset.model === 'authored-rig'")
    for width,height in [(390,844),(320,740)]:
        page.set_viewport_size({"width":width,"height":height});page.wait_for_timeout(350)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"),f"Horizontal overflow at {width}"
        assert page.locator(".connection").is_visible()
        assert page.locator("#running-toggle").is_enabled()
        capture(page,output,f"mobile-{width}.png")
    results["responsive"]=[390,320]
    results["page_errors"]=errors
    assert not errors,errors
    context.close()


def renderer_checks(browser,url:str,output:Path,results:dict) -> None:
    context=browser.new_context(viewport={"width":1280,"height":720});context.add_init_script(OBSERVE)
    page=context.new_page()
    page.add_init_script("""HTMLCanvasElement.prototype.getContext = function(){return null;};
      try{Object.defineProperty(navigator,'gpu',{value:undefined});}catch{}""")
    ready(page,f"{url}?renderer=webgl",graphics=False)
    until(page,"document.querySelectorAll('#active-neurons li').length>0")
    assert page.locator("#running-toggle").is_enabled()
    assert page.locator("#apply-load").is_enabled()
    paused(page,False)
    step=page.evaluate("window.__qa.frame.step")
    until(page,f"window.__qa.frame.step>{step+2}")
    paused(page)
    capture(page,output,"renderer-unavailable.png")
    results["renderer_unavailable"]={"received_readings":page.locator("#active-neurons li").count(),"pause_works":True,"load_reachable":True}
    context.close()
    context=browser.new_context(viewport={"width":1280,"height":720});page=context.new_page()
    ready(page,url,graphics=False)
    try:
        until(page,"document.querySelector('#scene').dataset.model === 'authored-rig'",30_000)
        results["webgpu_attempt"]={"initialized_backend":page.locator("#scene").get_attribute("data-renderer"),
          "navigator_gpu":page.evaluate("!!navigator.gpu")}
        capture(page,output,"default-renderer.png")
    except Exception as error:
        results["webgpu_attempt"]={"initialized_backend":None,"gap":str(error).splitlines()[0]}
    context.close()


def record_demo(browser,url:str,output:Path,results:dict) -> None:
    recording=output/"video"
    context=browser.new_context(viewport={"width":1280,"height":720},record_video_dir=str(recording),record_video_size={"width":1280,"height":720})
    context.add_init_script(OBSERVE);page=context.new_page()
    ready(page,f"{url}?renderer=webgl")
    paused(page,False)
    started=time.monotonic()
    page.wait_for_timeout(9000)
    page.locator('[data-tab="neurons"]').click();page.wait_for_timeout(5000)
    page.locator('[data-tab="workout"]').click();page.wait_for_timeout(6000)
    recorded_reps=page.evaluate("window.__qa.frames.map(f=>f.flies[0].exercise.repetitions)")
    results["demo"]={"actual_browser":True,"interaction_seconds":round(time.monotonic()-started,3),
      "repetitions_seen":sorted(set(recorded_reps))}
    video=page.video
    context.close()
    if video:
        path=Path(video.path());destination=output/"drosolift-live-demo.webm";path.replace(destination)
        results["demo"].update(file=destination.name,bytes=destination.stat().st_size,
          sha256=hashlib.sha256(destination.read_bytes()).hexdigest())


@contextmanager
def static_site(directory:Path):
    class Handler(SimpleHTTPRequestHandler):
        extensions_map={**SimpleHTTPRequestHandler.extensions_map,".js":"text/javascript",".mjs":"text/javascript",
          ".css":"text/css",".json":"application/json",".wasm":"application/wasm"}
        def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(directory),**kwargs)
        def translate_path(self,path):
            if path.startswith("/conference/"):path=path[len("/conference"):]
            return super().translate_path(path)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f"http://127.0.0.1:{server.server_port}"
    finally:server.shutdown();server.server_close();thread.join()


def offline_checks(browser,output:Path,results:dict) -> None:
    sample=json.loads((ROOT/"frontend/web/dist/samples/bench.json").read_text())
    frames=sample["frames"]
    with static_site(ROOT/"frontend/web/dist") as url:
        checked=[]
        for prefix in ["/","/conference/"]:
            context=browser.new_context(viewport={"width":1280,"height":720},accept_downloads=True)
            context.add_init_script(OBSERVE);page=context.new_page();errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            ready(page,f"{url}{prefix}?replay=1&renderer=webgl")
            until(page,"document.querySelector('#connection-label').textContent==='RECORDED'")
            assert page.evaluate("window.__qa.sockets.length")==0,"Recorded mode opened a WebSocket"
            assert page.locator("#video-placeholder").is_visible()
            selected=frames[len(frames)//2]
            target_time=selected["elapsed"]
            normalized=(target_time-frames[0]["elapsed"])/(frames[-1]["elapsed"]-frames[0]["elapsed"])
            seek(page,normalized)
            # Range input step rounds its value; choose the exact corresponding left sample.
            slider=float(page.locator("#replay-seek").input_value())
            expected_time=frames[0]["elapsed"]+slider*(frames[-1]["elapsed"]-frames[0]["elapsed"])
            expected=next(f for f in reversed(frames) if f["elapsed"]<=expected_time)
            assert int(page.locator("#step-value").inner_text())==expected["step"]
            assert int(page.locator("#hero-reps").inner_text())==expected["flies"][0]["exercise"]["repetitions"]
            before=int(page.locator("#step-value").inner_text());page.wait_for_timeout(250)
            assert int(page.locator("#step-value").inner_text())==before
            page.locator("#replay-speed").select_option("0.25")
            page.locator("#running-toggle").click();page.wait_for_timeout(1200);page.locator("#running-toggle").click()
            after=int(page.locator("#step-value").inner_text())
            assert before<after<=before+5,"Quarter-speed replay time did not follow recorded samples"
            with page.expect_download() as download:
                page.locator("#export-json").click()
            exact=json.loads(Path(download.value.path()).read_text())
            assert exact["frames"]==frames
            with page.expect_download() as download:
                page.locator("#export-csv").click()
            rows=list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text())))
            assert len(rows)==sum(len(f["flies"]) for f in frames)
            assert int(rows[-1]["repetitions"])==frames[-1]["flies"][-1]["exercise"]["repetitions"]
            page.locator("#replay-restart").click()
            assert int(page.locator("#step-value").inner_text())==frames[0]["step"]
            # Seek to a representative loaded state for the artifact.
            seek(page,.35);page.wait_for_timeout(300)
            capture(page,output,"replay-subpath.png" if prefix!="/" else "replay-1280x720.png")
            if prefix=="/":
                page.set_viewport_size({"width":1920,"height":1080});page.wait_for_timeout(350)
                capture(page,output,"replay-1920x1080.png")
            checked.append({"path":prefix,"exact_seek_step":expected["step"],"quarter_speed_steps":after-before,"websocket_connections":0,"csv_rows":len(rows),"page_errors":errors})
            assert not errors,errors
            context.close()
        results["offline_replay"]=checked
    recorded_build=ROOT/"frontend/web/dist-replay"
    if recorded_build.exists():
        defaults=[]
        with static_site(recorded_build) as url:
            for prefix in ["/","/conference/"]:
                context=browser.new_context(viewport={"width":1280,"height":720})
                context.add_init_script(OBSERVE);page=context.new_page()
                ready(page,f"{url}{prefix}?renderer=webgl")
                until(page,"document.querySelector('#connection-label').textContent==='RECORDED'")
                assert page.evaluate("window.__qa.sockets.length")==0
                assert int(page.locator("#step-value").inner_text())==frames[0]["step"]
                defaults.append({"path":prefix,"no_replay_query":True,"websocket_connections":0})
                capture(page,output,"recorded-build-subpath.png" if prefix!="/" else "recorded-build-default.png")
                context.close()
        results["recorded_build_defaults"]=defaults


def run(options) -> None:
    output=options.output.resolve();output.mkdir(parents=True,exist_ok=True)
    results={"machine":{"platform":platform.platform(),"processor":platform.processor(),"logical_cpus":os.cpu_count()},
      "url":options.url,"started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(executable_path=options.browser,headless=True,
              args=["--use-angle=swiftshader","--enable-unsafe-swiftshader"] if options.software else [])
            results["machine"]["browser_version"]=browser.version
            results["machine"]["software_rendering_requested"]=options.software
            if not options.static_only:
                print("Running live browser checks",flush=True)
                live_checks(browser,options.url,output,results)
                print("Running renderer and numerical fallback checks",flush=True)
                renderer_checks(browser,options.url,output,results)
                print("Recording actual live browser demo",flush=True)
                record_demo(browser,options.url,output,results)
            if options.stop_backend_pid:
                os.kill(options.stop_backend_pid,signal.SIGTERM)
                for _ in range(30):
                    try:urlopen(f"{options.url}/health",timeout=.3)
                    except (URLError,TimeoutError,ConnectionError):break
                    time.sleep(.1)
                else:raise AssertionError("Requested Python backend is still reachable")
                results["backend_stopped"]={"pid":options.stop_backend_pid,"health_unreachable":True}
            if not options.live_only:
                print("Running static root and subpath replay checks",flush=True)
                offline_checks(browser,output,results)
            browser.close()
        results["status"]="passed"
    except Exception as error:
        results.update(status="failed",failure=f"{type(error).__name__}: {error}")
        raise
    finally:
        (output/"browser-results.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
        print(json.dumps(results,indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url",default="http://127.0.0.1:8000")
    parser.add_argument("--output",type=Path,default=ROOT/"docs/drosolift/evidence")
    parser.add_argument("--browser",default="C:/Program Files/Google/Chrome/Application/chrome.exe")
    parser.add_argument("--software",action="store_true",help="Explicitly use Chrome SwiftShader; report as software graphics")
    parser.add_argument("--static-only",action="store_true")
    parser.add_argument("--live-only",action="store_true")
    parser.add_argument("--stop-backend-pid",type=int)
    run(parser.parse_args())
