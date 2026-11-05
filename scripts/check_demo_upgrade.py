"""Observe exercise switching, source-backed activity and the upgraded real demo.

Run against gym-web --feedback apparatus-visual-v1 and the replay server on8010.
No telemetry is fabricated. Protocol retry reuses a command sent by the actual UI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from playwright.sync_api import sync_playwright
from scripts.check_drosolift_browser import OBSERVE, capture, graphics_info, paused, ready, seek, until

ROOT = Path(__file__).resolve().parents[1]
LEFT = (36800, 18571, 546043, 21982, 14473, 546087)
RIGHT = (63316, 28221, 27196, 37738, 24236, 27390)


def means(frame: dict) -> dict:
    values = {row['body_id']: row['activity'] for row in frame['flies'][0]['frame']['neural']['active']}
    return {'left': sum(values[key] for key in LEFT) / len(LEFT),
            'right': sum(values[key] for key in RIGHT) / len(RIGHT)}


def snapshot(page) -> dict:
    return page.evaluate('({frame:window.__qa.frame,control:window.__qa.control})')


def verify_display(page, frame: dict) -> None:
    expected = means(frame)
    for side in ('left', 'right'):
        displayed = page.locator(f'[data-group="visual-{side}"] .group-rate').inner_text()
        assert abs(float(displayed) - expected[side]) < .001, (side, displayed, expected)
    selected = int(page.locator('#selected-id').inner_text())
    neuron = next(n for n in frame['flies'][0]['frame']['neural']['active'] if n['body_id'] == selected)
    assert float(page.locator('#selected-value').inner_text().split()[0]) == neuron['activity']


def live(browser, args, output: Path, results: dict) -> None:
    context = browser.new_context(viewport={'width': 1280, 'height': 720}, device_scale_factor=1)
    context.add_init_script(OBSERVE)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    ready(page, args.url + '/?renderer=webgl&diagnostics=1')
    until(page, "window.__qa.control?.feedback?.[0]?.profile==='apparatus-visual-v1'")
    until(page, "document.querySelectorAll('#neural-groups button').length===6")
    assert page.locator('#exercise-curl').is_enabled()
    if page.evaluate("window.__qa.frame.flies[0].exercise.kind") != 'bench_press':
        page.locator('#exercise-bench').click()
        paused(page, False)
        until(page, "window.__qa.frame.flies[0].exercise.kind==='bench_press'")
    paused(page, False)
    until(page, "window.__qa.frame.flies[0].exercise.kind==='bench_press' && window.__qa.frame.flies[0].exercise.joint_position>.3")
    paused(page)
    bench = snapshot(page)
    verify_display(page, bench['frame'])
    bench_feedback = bench['control']['feedback'][0]
    assert bench_feedback['indicator_left'] > bench_feedback['indicator_right']
    capture(page, output, 'bench-1280x720.png')
    page.set_viewport_size({'width': 1920, 'height': 1080})
    page.wait_for_timeout(250)
    capture(page, output, 'bench-1920x1080.png')
    page.set_viewport_size({'width': 1280, 'height': 720})
    page.locator('#exercise-curl').click()
    until(page, "window.__qa.control.exercises[0].pending_kind==='bicep_curl'")
    command = page.evaluate("window.__qa.sent.filter(m=>m.type==='set_exercise').at(-1)")
    page.evaluate("command=>window.__qa.sockets.at(-1).send(JSON.stringify(command))", command)
    page.wait_for_timeout(250)
    assert snapshot(page)['frame'] == bench['frame'], 'Paused setup changed an incomplete stroke'
    paused(page, False)
    until(page, "window.__qa.frame.flies[0].exercise.kind==='bicep_curl'")
    curl_start = snapshot(page)
    assert curl_start['frame']['flies'][0]['exercise']['repetitions'] >= bench['frame']['flies'][0]['exercise']['repetitions']
    baseline_reps = curl_start['frame']['flies'][0]['exercise']['repetitions']
    until(page, f"window.__qa.frame.flies[0].exercise.repetitions>{baseline_reps}")
    until(page, "window.__qa.frame.flies[0].exercise.joint_position>.3")
    paused(page)
    curl = snapshot(page)
    verify_display(page, curl['frame'])
    curl_feedback = curl['control']['feedback'][0]
    assert curl_feedback['indicator_right'] > curl_feedback['indicator_left']
    assert 'curl' in page.locator('#chamber-title').inner_text().lower()
    capture(page, output, 'curl-1280x720.png')
    page.set_viewport_size({'width': 1920, 'height': 1080})
    page.wait_for_timeout(250)
    capture(page, output, 'curl-1920x1080.png')
    unchanged = snapshot(page)['frame']
    page.locator('[data-group="visual-right"]').click()
    page.locator('#view-circuit').click()
    page.locator('#xray-toggle').click()
    page.wait_for_timeout(350)
    assert snapshot(page)['frame'] == unchanged
    capture(page, output, 'curl-circuit-xray-1920x1080.png')
    page.locator('#view-atlas').click()
    page.locator('[data-group="visual-right"]').click()
    page.wait_for_timeout(350)
    capture(page, output, 'curl-anatomy-xray-1920x1080.png')
    page.locator('#xray-toggle').click()
    page.set_viewport_size({'width': 1280, 'height': 720})
    paused(page, False)
    page.wait_for_timeout(1800)
    start = page.evaluate('performance.now()')
    page.wait_for_timeout(10000)
    end = page.evaluate('performance.now()')
    loops = page.evaluate('window.__qa.raf.map(r=>({source:r.source,times:r.times}))')
    cadence = []
    for loop in loops:
        times = [value for value in loop['times'] if start <= value <= end]
        if len(times) > 2:
            cadence.append({'source': loop['source'], 'frames': len(times), 'fps': (len(times) - 1) * 1000 / (times[-1] - times[0])})
    assert cadence and min(item['fps'] for item in cadence) >= 30, cadence
    results['live'] = {'bench': bench, 'curl': curl, 'bench_visual_means': means(bench['frame']),
        'curl_visual_means': means(curl['frame']), 'retry': command, 'curl_full_return': True,
        'observer_invariance': True, 'graphics': graphics_info(page), 'cadence': cadence,
        'scene_stats': page.locator('#scene').get_attribute('data-graphics-stats'),
        'neural_stats': page.locator('#neuron-map').get_attribute('data-graphics-stats')}
    assert not errors, errors
    results['live']['page_errors'] = errors
    # Live-only setup must become unavailable when the same viewer enters replay.
    page.locator('[data-tab="replay"]').click()
    until(page, "document.querySelector('#connection-label').textContent==='RECORDED' && document.querySelector('#step-value').textContent==='0'")
    page.locator('#open-methods').click()
    page.locator('details:has(#population-form)>summary').click()
    assert page.locator('#apply-population').is_disabled()
    page.locator('#close-methods').click()
    results['live']['recorded_setup_disabled'] = True
    page.get_by_role('button', name='Go live', exact=True).click()
    until(page, "document.querySelector('#connection-label').textContent==='LIVE'")
    paused(page, False)
    # Leave the live audience flow running after its recorded-mode regression.
    context.close()


def recorded(browser, args, output: Path, results: dict) -> None:
    context = browser.new_context(viewport={'width': 1280, 'height': 720}, accept_downloads=True)
    context.add_init_script(OBSERVE)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    ready(page, args.replay_url + '/?renderer=webgl')
    until(page, "document.querySelector('#connection-label').textContent==='RECORDED'")
    checks = []
    for kind, button in [('bench_press', '#exercise-bench'), ('bicep_curl', '#exercise-curl')]:
        page.locator(button).click()
        until(page, f"document.querySelector('{button}').getAttribute('aria-pressed')==='true'")
        seek(page, .55)
        page.wait_for_timeout(100)
        with page.expect_download() as item:
            page.locator('#export-json').click()
        data = json.loads(Path(item.value.path()).read_text())
        assert data['metadata']['exercise'] == kind
        assert data['metadata']['feedback_profile'] == 'apparatus-visual-v1'
        assert len(data['frames']) == 201
        time_value = float(page.locator('#replay-seek').input_value()) * data['frames'][-1]['elapsed']
        expected = next(frame for frame in reversed(data['frames']) if frame['elapsed'] <= time_value)
        assert int(page.locator('#step-value').inner_text()) == expected['step']
        assert int(page.locator('#hero-reps').inner_text()) == expected['flies'][0]['exercise']['repetitions']
        verify_display(page, expected)
        fixed = int(page.locator('#step-value').inner_text())
        for tab in ['neurons', 'workout', 'replay']:
            page.locator(f'[data-tab="{tab}"]').click()
            assert int(page.locator('#step-value').inner_text()) == fixed
        assert page.evaluate('window.__qa.sockets.length') == 0
        checks.append({'exercise': kind, 'seek_step': fixed, 'frames': len(data['frames']), 'websockets': 0})
        capture(page, output, 'recorded-' + kind + '-1280x720.png')
    assert not errors, errors
    results['recorded'] = checks
    results['recorded_page_errors'] = errors
    context.close()


def run(args) -> None:
    output = ROOT / 'docs/drosolift/evidence/demo-v2'
    output.mkdir(parents=True, exist_ok=True)
    results = {'status': 'running'}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
            results['browser'] = browser.version
            if not args.recorded_only:
                live(browser, args, output, results)
            recorded(browser, args, output, results)
            browser.close()
        results['status'] = 'passed'
    except Exception as error:
        results.update(status='failed', failure=f'{type(error).__name__}: {error}')
        raise
    finally:
        (output / 'browser-checks.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(json.dumps({key: value for key, value in results.items() if key != 'live'}, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--replay-url', default='http://127.0.0.1:8010')
    parser.add_argument('--recorded-only', action='store_true')
    run(parser.parse_args())
