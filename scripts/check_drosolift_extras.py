"""Verify the documented static server, local video and real reconnection flow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.check_drosolift_browser import OBSERVE, ROOT, capture, paused, ready, seek, until


def check(options) -> None:
    output=ROOT/"docs/drosolift/evidence/native"
    output.mkdir(parents=True,exist_ok=True)
    results={"status":"in_progress"}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",headless=True)
        context=browser.new_context(viewport={"width":1280,"height":720});context.add_init_script(OBSERVE)
        page=context.new_page();errors=[];responses=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.on("response",lambda response:responses.append({"url":response.url,"content_type":response.headers.get("content-type")}) if response.url.split("?")[0].endswith(".js") else None)
        ready(page,options.static_url+"/?renderer=webgl&diagnostics=1")
        assert page.locator("#connection-label").inner_text()=="RECORDED"
        assert page.evaluate("window.__qa.sockets.length")==0
        assert responses and all("javascript" in response["content_type"] for response in responses)
        results["documented_server"]={"url":options.static_url,"default_recorded":True,"websockets":0,"javascript_mime_verified":True}
        seek(page,.4)
        recorded_step=int(page.locator("#step-value").inner_text())
        assert recorded_step>0
        for tab in ["neurons","workout","replay"]:
            page.locator(f'[data-tab="{tab}"]').click()
            assert page.locator("#connection-label").inner_text()=="RECORDED","Observer tab left recorded mode"
            assert int(page.locator("#step-value").inner_text())==recorded_step
            assert page.evaluate("window.__qa.sockets.length")==0,"Recorded observer tab opened a WebSocket"
        results["recorded_observer_tabs"]={"tabs":["neurons","workout","replay"],"same_step":recorded_step,"websockets":0}
        assert not page.locator("#load-control").is_visible()
        capture(page,output,"replay-1280x720.png")
        page.set_viewport_size({"width":1920,"height":1080});page.wait_for_timeout(250)
        capture(page,output,"replay-1920x1080.png")
        page.set_viewport_size({"width":1280,"height":720})
        if options.navigation_only:
            results.update(status="passed",page_errors=errors)
            (output/"recorded-navigation-results.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
            context.close();browser.close();print(json.dumps(results,indent=2),flush=True);return

        # The test fixture is our actual app recording; no athlete video is implied.
        video=output/"drosolift-live-demo.webm"
        page.locator("#user-video").set_input_files(str(video))
        until(page,"Number.isFinite(document.querySelector('#replay-video').duration) && document.querySelector('#replay-video').duration>0")
        seek(page,.25)
        page.locator("#video-offset").fill("2")
        page.wait_for_timeout(250)
        observed=page.locator("#replay-video").evaluate("video=>({time:video.currentTime,duration:video.duration,blob:video.src.startsWith('blob:')})")
        recording=json.loads((ROOT/"frontend/web/dist-replay/samples/bench.json").read_text())
        fraction=float(page.locator("#replay-seek").input_value())
        first,last=recording["frames"][0]["elapsed"],recording["frames"][-1]["elapsed"]
        expected=min(observed["duration"],max(0,(last-first)*fraction+2))
        assert abs(observed["time"]-expected)<.1,(observed,expected)
        assert observed["blob"]
        assert not page.locator("#video-placeholder").is_visible()
        results["local_video"]={"fixture":"actual DrosoLift app recording; no supplied athlete video", "offset_seconds":2,
            "expected_video_seconds":expected,"actual_video_seconds":observed["time"],"local_blob":True}

        # Optional diagnostic counters report resource objects, not video-memory bytes.
        if options.resources:
            until(page,"document.querySelector('#scene').dataset.graphicsStats && document.querySelector('#neuron-map').dataset.graphicsStats")
            page.locator("#xray-toggle").click()
            until(page,"document.querySelector('#neuron-map').dataset.detail==='official-skeletons'")
            page.wait_for_timeout(1200)
            baseline=page.evaluate("Object.fromEntries(['scene','neuron-map'].map(id=>[id,JSON.parse(document.getElementById(id).dataset.graphicsStats)]))")
            samples=[]
            for _ in range(5):
                page.locator("#xray-toggle").click();page.locator("#xray-toggle").click()
                page.wait_for_timeout(1100)
                samples.append(page.evaluate("Object.fromEntries(['scene','neuron-map'].map(id=>[id,JSON.parse(document.getElementById(id).dataset.graphicsStats)]))"))
            for sample in samples:
                for view in ["scene","neuron-map"]:
                    for key in ["geometries","textures","estimatedBytes"]:
                        assert sample[view].get(key)==baseline[view].get(key),(view,key,baseline[view],sample[view])
            results["resource_switching"]={"baseline":baseline,"after_cycles":samples,"cycles":5,
                "qualification":"Three.js renderer object/draw counters; VRAM bytes not measured"}
        capture(page,output,"local-video-alignment.png")
        (output/"extras-results.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
        context.close()

        # Close the actual paused WebSocket, then wait for the normal client retry.
        context=browser.new_context(viewport={"width":1280,"height":720});context.add_init_script(OBSERVE)
        page=context.new_page();page.on("pageerror",lambda error:errors.append(str(error)))
        ready(page,options.live_url+"/?renderer=webgl")
        was_running=page.evaluate("window.__qa.running")
        paused(page)
        before=page.evaluate("({frame:window.__qa.frame,control:window.__qa.control,sockets:window.__qa.sockets.length})")
        page.evaluate("window.__qa.sockets.at(-1).close()")
        until(page,f"window.__qa.sockets.length > {before['sockets']} && window.__qa.sockets.at(-1).readyState === WebSocket.OPEN")
        until(page,"document.querySelector('#connection-label').textContent==='LIVE'")
        after=page.evaluate("({frame:window.__qa.frame,control:window.__qa.control,running:window.__qa.running})")
        assert after["frame"]==before["frame"]
        assert after["control"]["run_id"]==before["control"]["run_id"]
        assert after["control"]["loads"]==before["control"]["loads"]
        assert after["running"] is False
        results["network_reconnect"]={"paused_step":after["frame"]["step"],"same_full_snapshot":True,"same_run_and_loads":True}
        # Population setup is explicit; observer selection/camera must not tick it.
        fixed_step=after["frame"]["step"]
        page.locator("#open-methods").click()
        page.locator("details:has(#population-form) > summary").click()
        if len(after["frame"]["flies"])!=1:
            page.locator("#fly-count").fill("1");page.locator("#apply-population").click()
            until(page,"window.__qa.frame.flies.length===1")
            assert page.evaluate("window.__qa.frame.step")==fixed_step
        page.locator("#fly-count").fill("10");page.locator("#apply-population").click()
        until(page,"window.__qa.frame.flies.length===10")
        assert page.evaluate("window.__qa.frame.step")==fixed_step
        page.locator('[data-fly="fly-2"]').click()
        page.locator("#close-methods").click();page.locator("#view-fly").click()
        assert page.locator("#scene").get_attribute("data-selected-fly")=="fly-2"
        assert page.evaluate("window.__qa.frame.step")==fixed_step
        # One explicit resume lets new identities establish their actual grips.
        paused(page,False)
        resumed_step=page.evaluate("window.__qa.frame.step")
        until(page,f"window.__qa.frame.step > {resumed_step+2}")
        paused(page)
        station=page.evaluate("window.__qa.frame.flies[1].exercise.station_id")
        load=None;curl_title=None
        if station is not None:
            load=page.evaluate("station=>window.__qa.control.loads.find(s=>s.station_id===station).load",station)
            assert float(page.locator("#current-load").inner_text())==load
            curl_title="curl" in page.locator("#chamber-title").inner_text().lower()
            assert curl_title
        fixed_step=page.evaluate("window.__qa.frame.step")
        page.locator("#open-methods").click()
        page.locator("#fly-count").fill("1");page.locator("#apply-population").click()
        until(page,"window.__qa.frame.flies.length===1")
        assert page.evaluate("window.__qa.frame.step")==fixed_step
        assert page.locator("#scene").get_attribute("data-selected-fly")=="fly-1"
        page.locator("#close-methods").click()
        results["population"]={"counts":[1,10,1],"paused_setup_preserves_step":True,"selected_fly":"fly-2",
          "selected_station":station,"selected_load":load,"curl_title":curl_title,
          "qualification":"Previously removed identities retain physical state/recovery; readding does not promise a new grip."}
        paused(page,False)
        context.close();browser.close()
        assert not errors,errors
    results.update(status="passed",page_errors=errors)
    (output/"extras-results.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    print(json.dumps(results,indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static-url",default="http://127.0.0.1:8010")
    parser.add_argument("--live-url",default="http://127.0.0.1:8000")
    parser.add_argument("--resources",action="store_true")
    parser.add_argument("--navigation-only",action="store_true")
    check(parser.parse_args())
