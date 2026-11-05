"""Exercise the user-reviewed neural/training UI against actual model frames."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from scripts.check_drosolift_browser import OBSERVE, capture, paused, ready, until

ROOT = Path(__file__).resolve().parents[1]


def selected(page) -> dict:
    return page.evaluate("window.__qa.frame.flies.find(f=>f.id===document.querySelector('#training-fly').value)")


def exact(page, recording: dict | None = None) -> dict:
    observed = page.evaluate("""()=>({fly:window.__qa.frame?.flies.find(f=>f.id===document.querySelector('#training-fly').value),
        id:document.querySelector('#training-fly').value,step:Number(document.querySelector('#step-value').textContent),
        strength:document.querySelector('#training-strength').textContent,active:document.querySelector('#neural-active-count').textContent,
        count:document.querySelector('#neural-observed-count').textContent,mean:document.querySelector('#neural-mean-rate').textContent})""")
    fly = observed.get('fly')
    if fly is None:
        assert recording is not None, 'Expected a live frame or the actual bundled recording'
        frame = next(frame for frame in recording['frames'] if frame['step'] == observed['step'])
        fly = next(fly for fly in frame['flies'] if fly['id'] == observed['id'])
    readings = fly['frame']['neural']['active']
    assert observed['strength'] == f"{fly['training']['fitness']:.3f}×"
    assert int(observed['active']) == sum(n['activity'] > 0 for n in readings)
    assert int(observed['count']) == len(readings)
    assert abs(float(observed['mean']) - sum(n['activity'] for n in readings) / len(readings)) <= .000501
    return fly


def midstroke(page) -> None:
    paused(page, False)
    until(page, "(()=>{const f=window.__qa.frame.flies.find(f=>f.id===document.querySelector('#training-fly').value);return f.exercise.joint_position>.25&&f.exercise.joint_position<.9})()", 120_000)
    paused(page)


def weights(page) -> dict:
    old = exact(page)
    station = old['exercise']['station_id']
    load = page.evaluate("id=>window.__qa.control.loads.find(s=>s.station_id===id)", station)
    before = page.locator('#scene').get_attribute('data-plate-count')
    assert before is not None, 'Applied plate count must describe actual visible geometry'
    direction = 1 if load['load'] < 2.8 else -1
    target = round(load['load'] + direction * .2, 2)
    page.locator('#apply-load' if direction > 0 else '#remove-load').click()
    until(page, f"window.__qa.control.loads.find(s=>s.station_id==='{station}').pending_load==={target}")
    assert 'after this rep' in page.locator('#control-status').inner_text()
    assert page.locator('#scene').get_attribute('data-plate-count') == before
    frozen = page.evaluate('window.__qa.frame')
    page.wait_for_timeout(300)
    assert page.evaluate('window.__qa.frame') == frozen
    paused(page, False)
    until(page, f"window.__qa.control.loads.find(s=>s.station_id==='{station}').load==={target}", 120_000)
    until(page, f"Number(document.querySelector('#scene').dataset.appliedLoad)==={target}")
    after = int(page.locator('#scene').get_attribute('data-plate-count'))
    assert (after - int(before)) * direction > 0, (before, after, direction)
    return {'station': station, 'from': load['load'], 'to': target,
            'plates_before': int(before), 'plates_after': after, 'pending_preserves_geometry': True}


def live(browser, args, output: Path) -> dict:
    context = browser.new_context(viewport={'width': 1184, 'height': 839}, device_scale_factor=1)
    context.add_init_script(OBSERVE)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    ready(page, args.url + '/?renderer=webgl&diagnostics=1&review=v3')
    capture(page, output, 'first-pass-1184x839.png')
    for selector in ['.session-controls', '.prototype', '#exercise-context', '#view-overview', '#view-eye', '.app-footer', '[data-tab="replay"]', '.feedback-strip']:
        assert page.locator(selector).count() == 0, selector
    assert page.locator('#exercise-pending').evaluate("e=>{const r=e.getBoundingClientRect();return r.width<=1&&r.height<=1}")
    until(page, "document.querySelector('#neuron-map').dataset.crop==='brain'")
    until(page, "Number(document.querySelector('#neural-rate-history').dataset.samples)>0")
    # A user may have left an apparatus change queued before this review.
    paused(page, False)
    until(page, "window.__qa.control.exercises.find(s=>s.fly_id===document.querySelector('#training-fly').value).pending_kind===null", 120_000)
    if selected(page)['exercise']['kind'] != 'bench_press':
        page.locator('#exercise-bench').click()
        until(page, "window.__qa.frame.flies.find(f=>f.id===document.querySelector('#training-fly').value).exercise.kind==='bench_press'", 120_000)
    # Pure observer modes must leave the actual paused frame and command stream unchanged.
    midstroke(page)
    frozen = page.evaluate('window.__qa.frame')
    sent = page.evaluate('window.__qa.sent.length')
    for selector in ['#neural-cell-colors', '#neural-front', '#neural-live', '#xray-toggle']:
        page.locator(selector).click()
    page.wait_for_timeout(350)
    assert page.evaluate('window.__qa.frame') == frozen
    assert page.evaluate('window.__qa.sent.length') == sent
    assert int(page.locator('#scene').get_attribute('data-overlay-observed')) == 91
    capture(page, output, 'neural-xray-1184x839.png')
    page.locator('#xray-toggle').click()
    bench_weights = weights(page)
    initial_population = len(page.evaluate('window.__qa.frame.flies'))
    assert initial_population < 10, 'Start acceptance with at least one unused individual'
    page.locator('#add-training-fly').click()
    new_id = f'fly-{initial_population + 1}'
    until(page, f"document.querySelector('#training-fly').value==='{new_id}'")
    until(page, f"window.__qa.frame.flies.find(f=>f.id==='{new_id}').exercise.station_id!==null")
    initial = exact(page)
    initial_sets = initial['training']['sets']
    paused(page, False)
    until(page, f"window.__qa.frame.flies.find(f=>f.id==='{new_id}').training.sets>{initial_sets}", 120_000)
    trained = exact(page)
    assert trained['training']['fitness'] >= min(1.5, initial['training']['fitness'] + .005) - 1e-9
    midstroke(page)
    capture(page, output, 'training-bench-1184x839.png')
    page.set_viewport_size({'width': 1920, 'height': 1080})
    page.wait_for_timeout(250)
    capture(page, output, 'training-bench-1920x1080.png')
    page.locator('#exercise-curl').click()
    until(page, f"window.__qa.control.exercises.find(s=>s.fly_id==='{new_id}').pending_kind==='bicep_curl'")
    assert page.locator('#apply-load').is_disabled()
    paused(page, False)
    until(page, f"window.__qa.frame.flies.find(f=>f.id==='{new_id}').exercise.kind==='bicep_curl'", 120_000)
    midstroke(page)
    curl_weights = weights(page)
    midstroke(page)
    capture(page, output, 'training-curl-1920x1080.png')
    page.set_viewport_size({'width': 1280, 'height': 720})
    capture(page, output, 'training-curl-1280x720.png')
    # Fly selection switches the observation and displayed progress only.
    frozen = page.evaluate('window.__qa.frame')
    page.locator('#training-fly').select_option('fly-1')
    exact(page)
    assert page.evaluate('window.__qa.frame') == frozen
    page.locator('#training-fly').select_option(new_id)
    exact(page)
    assert page.evaluate('window.__qa.frame') == frozen
    assert int(page.locator('#neural-rate-history').get_attribute('data-samples')) <= 1
    paused(page, False)
    page.wait_for_timeout(1200)
    start = page.evaluate('performance.now()')
    page.wait_for_timeout(10000)
    cadence = page.evaluate("start=>window.__qa.raf.map(r=>{const t=r.times.filter(x=>x>=start);return{source:r.source,frames:t.length,fps:t.length>1?(t.length-1)*1000/(t.at(-1)-t[0]):0}}).filter(r=>r.frames>2)", start)
    assert cadence and min(row['fps'] for row in cadence) >= 30, cadence
    paused(page)
    for width, height in [(390, 844), (320, 740)]:
        page.set_viewport_size({'width': width, 'height': height})
        page.wait_for_timeout(200)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
        capture(page, output, f'training-mobile-{width}.png')
    paused(page, False)
    assert not errors, errors
    context.close()
    return {'bench_weight': bench_weights, 'curl_weight': curl_weights,
        'new_fly': new_id, 'initial': initial, 'trained': trained,
        'selection_observer_only': True, 'neural_modes_observer_only': True,
        'removed_annotated_elements': True, 'responsive_widths': [390, 320],
        'cadence_1280x720': cadence, 'page_errors': errors}


def renderers(browser, args, output: Path) -> dict:
    results = {}
    for mode in ['default', 'webgl', 'unavailable']:
        context = browser.new_context(viewport={'width': 1184, 'height': 839})
        context.add_init_script(OBSERVE)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        if mode == 'unavailable':
            context.add_init_script("HTMLCanvasElement.prototype.getContext=function(){return null;};try{Object.defineProperty(navigator,'gpu',{value:undefined});}catch{}")
        ready(page, args.replay_url + ('/?renderer=webgl&diagnostics=1' if mode != 'default' else '/?diagnostics=1'), graphics=mode != 'unavailable')
        until(page, "document.querySelector('#connection-label').textContent==='RECORDED'")
        if mode != 'unavailable':
            until(page, "document.querySelector('#neuron-map').dataset.crop==='brain'")
            page.locator('#neural-cell-colors').click()
            assert page.locator('#neuron-map').get_attribute('data-color-mode') == 'cell-colors'
            page.locator('#neural-live').click()
        paused(page, False)
        until(page, "Number(document.querySelector('#step-value').textContent)>6")
        paused(page)
        recording = page.request.get(args.replay_url + '/samples/demo-bench.json').json()
        exact(page, recording)
        resource_checks = None
        if mode != 'unavailable':
            page.locator('#xray-toggle').click()
            page.wait_for_timeout(250)
            page.locator('#xray-toggle').click()
            page.wait_for_timeout(1200)
            stats = lambda: page.evaluate("Object.fromEntries(['scene','neuron-map'].map(id=>[id,JSON.parse(document.getElementById(id).dataset.graphicsStats)]))")
            before = stats()
            for _ in range(5):
                for selector in ['#neural-cell-colors', '#xray-toggle', '#neural-live', '#xray-toggle']:
                    page.locator(selector).click()
            page.wait_for_timeout(1200)
            after = stats()
            for view in before:
                for key in ['geometries', 'textures']:
                    assert before[view][key] == after[view][key], (view, key, before, after)
                assert after[view]['estimatedBytes'] <= before[view]['estimatedBytes'], (view, before, after)
            resource_checks = {'before': before, 'after_five_cycles': after}
        assert page.locator('#add-training-fly').is_disabled()
        assert page.evaluate('window.__qa.sockets.length') == 0
        page.locator('.neuron-details summary').click()
        assert page.locator('#active-neurons li').count() == 91
        with page.expect_download() as download:
            page.locator('#export-json').click()
        data = json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
        assert len(data['frames']) == 201
        page.locator('.neuron-details summary').click()
        capture(page, output, f'training-{mode}-1184x839.png')
        assert not errors, errors
        results[mode] = {'renderer': page.locator('#scene').get_attribute('data-renderer'),
            'exact_readings': 91, 'recorded_frames_exported': 201, 'websockets': 0,
            'resource_checks': resource_checks, 'page_errors': errors}
        context.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--replay-url', default='http://127.0.0.1:8010')
    parser.add_argument('--renderers-only', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'docs/drosolift/evidence/demo-v3'
    output.mkdir(parents=True, exist_ok=True)
    result = {'status': 'running'}
    if args.renderers_only and (output / 'browser-checks.json').exists():
        previous = json.loads((output / 'browser-checks.json').read_text(encoding='utf-8'))
        if previous.get('live'):
            result['live'] = previous['live']
            result['live_flow_preserved_from_preceding_pass'] = True
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
            result['browser'] = browser.version
            if not args.renderers_only:
                result['live'] = live(browser, args, output)
            result['renderers'] = renderers(browser, args, output)
            browser.close()
        result['status'] = 'passed'
    except Exception as error:
        result.update(status='failed', failure=f'{type(error).__name__}: {error}')
        raise
    finally:
        (output / 'browser-checks.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({key: value for key, value in result.items() if key != 'live'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
