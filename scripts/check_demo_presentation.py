"""Inspect the actual upgraded replay on WebGPU/WebGL2 and record its audience flow.

Uses recorded model states, native controls and the installed Chrome GPU adapter.
No rendering or neural values are mocked, except deliberate renderer failure.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import time
from uuid import uuid4

from playwright.sync_api import sync_playwright
from scripts.check_drosolift_browser import OBSERVE, capture, graphics_info, paused, ready, seek, until

ROOT = Path(__file__).resolve().parents[1]


def finish_video(browser, source: Path, output: Path, interaction_seconds: float, filename: str = 'drosolift-demo-v2.webm') -> dict:
    """Remove initialization wait while preserving the actual UI interaction."""
    def duration(path: Path) -> float:
        probe = browser.new_page()
        try:
            probe.goto(path.as_uri(), wait_until='domcontentloaded')
            until(probe, "Number.isFinite(document.querySelector('video')?.duration)")
            return probe.evaluate("document.querySelector('video').duration")
        finally:
            probe.close()
    raw_duration = duration(source.resolve())
    destination = output / filename
    if raw_duration > 30:
        # Captures include the renderer's first initialization. The final 24 s
        # contain all 23.7 s of audience controls, with no invented frames.
        seconds = min(29.5, max(24., interaction_seconds + .25))
        assert seconds <= 30 and seconds <= raw_duration
        candidates = list((Path(os.environ['LOCALAPPDATA']) / 'ms-playwright').glob('ffmpeg-*/ffmpeg-win64.exe'))
        if not candidates:
            raise RuntimeError('Install the verification video helper: python -m playwright install ffmpeg')
        executable = max(candidates, key=lambda path: int(path.parent.name.split('-')[-1]))
        temporary = output / f'.demo-trim-{uuid4().hex}.webm'
        result = subprocess.run([str(executable), '-hide_banner', '-ss', str(raw_duration - seconds), '-i', str(source),
            '-t', str(seconds), '-an', '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '32',
            '-deadline', 'realtime', '-cpu-used', '5', str(temporary)], capture_output=True, text=True, check=True)
        (output / 'video-metadata.txt').write_text(result.stderr, encoding='utf-8')
        archive = ROOT / 'data/runs' / output.name / f'screen-capture-source-{uuid4().hex}.webm'
        archive.parent.mkdir(parents=True, exist_ok=True)
        source.replace(archive)
        temporary.replace(destination)
    else:
        source.replace(destination)
    final_duration = duration(destination.resolve())
    assert 15 <= final_duration <= 30, final_duration
    return {'file': destination.name, 'bytes': destination.stat().st_size,
        'sha256': sha256(destination.read_bytes()).hexdigest(), 'duration_seconds': final_duration,
        'raw_duration_seconds': raw_duration, 'initialization_wait_trimmed': raw_duration > 30}


def render_checks(browser, url: str, output: Path) -> dict:
    results = {}
    for mode, query in [('default', ''), ('webgl', 'renderer=webgl&')]:
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        context.add_init_script(OBSERVE)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        ready(page, f'{url}/?{query}diagnostics=1')
        seek(page, .45)
        page.wait_for_timeout(700)
        page.locator('#view-circuit').click()
        page.wait_for_timeout(350)
        capture(page, output, f'{mode}-circuit-1280x720.png')
        page.locator('#view-atlas').click()
        page.wait_for_timeout(350)
        capture(page, output, f'{mode}-anatomy-1280x720.png')
        # Upload the initially hidden body overlay before measuring retention.
        page.locator('#xray-toggle').click()
        page.wait_for_timeout(1200)
        page.locator('#xray-toggle').click()
        page.wait_for_timeout(350)
        stats = lambda: page.evaluate("Object.fromEntries(['scene','neuron-map'].map(id=>[id,JSON.parse(document.getElementById(id).dataset.graphicsStats)]))")
        before = stats()
        for _ in range(5):
            for selector in ('#xray-toggle', '#view-circuit', '#xray-toggle', '#view-atlas'):
                page.locator(selector).click()
            page.wait_for_timeout(100)
        page.wait_for_timeout(1200)
        after = stats()
        for view in before:
            for key in ('geometries', 'textures'):
                assert after[view][key] == before[view][key], (mode, view, key, before, after)
            assert after[view]['estimatedBytes'] <= before[view]['estimatedBytes'], (mode, view, before, after)
        fixed_step = page.locator('#step-value').inner_text()
        for selector, name in [('#view-overview', 'overview'), ('#view-eye', 'eye'), ('#view-fly', 'follow')]:
            page.locator(selector).click()
            page.wait_for_timeout(250)
            assert page.locator('#scene').get_attribute('data-camera-mode') == name
            assert page.locator('#step-value').inner_text() == fixed_step
            capture(page, output, f'{mode}-camera-{name}.png')
        assert page.evaluate('window.__qa.sockets.length') == 0
        for width, height in [(390, 844), (320, 740)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.wait_for_timeout(200)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
            assert page.locator('#exercise-curl').is_enabled()
            assert page.locator('#running-toggle').is_enabled()
            capture(page, output, f'{mode}-mobile-{width}.png')
        assert not errors, errors
        results[mode] = {'before': before, 'after_five_cycles': after,
                         'mobile_widths': [390, 320], 'page_errors': errors, 'websockets': 0}
        if mode == 'webgl':
            results[mode]['graphics'] = graphics_info(page)
        context.close()
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    context.add_init_script(OBSERVE)
    context.add_init_script("""HTMLCanvasElement.prototype.getContext=function(){return null;};
        try{Object.defineProperty(navigator,'gpu',{value:undefined});}catch{}""")
    page = context.new_page()
    ready(page, f'{url}/?renderer=webgl', graphics=False)
    until(page, "document.querySelectorAll('#active-neurons li').length===91")
    page.locator('#exercise-curl').click()
    until(page, "document.querySelector('#exercise-curl').getAttribute('aria-pressed')==='true'")
    paused(page, False)
    until(page, "Number(document.querySelector('#step-value').textContent)>3")
    paused(page)
    assert page.locator('#selected-value').inner_text() != '—'
    capture(page, output, 'renderer-unavailable.png')
    results['renderer_unavailable'] = {'readings': 91, 'curl_selection': True, 'play_pause': True}
    context.close()
    return results


def record(browser, url: str, output: Path) -> dict:
    context = browser.new_context(viewport={'width': 1280, 'height': 720},
        record_video_dir=str(output / 'video'), record_video_size={'width': 1280, 'height': 720})
    context.add_init_script(OBSERVE)
    page = context.new_page()
    ready(page, f'{url}/?renderer=webgl')
    # Keep the default anatomy visible throughout both task demonstrations.
    page.locator('[data-tab="workout"]').click()
    started = time.monotonic()
    paused(page, False)
    page.wait_for_timeout(8000)
    bench = {'step': page.locator('#step-value').inner_text(), 'reps': page.locator('#hero-reps').inner_text()}
    page.locator('[data-tab="neurons"]').click()
    page.locator('[data-group="visual-left"]').click()
    page.wait_for_timeout(3000)
    page.locator('#exercise-curl').click()
    until(page, "document.querySelector('#exercise-curl').getAttribute('aria-pressed')==='true'")
    page.locator('[data-group="visual-right"]').click()
    page.locator('[data-tab="workout"]').click()
    paused(page, False)
    page.wait_for_timeout(8000)
    curl = {'step': page.locator('#step-value').inner_text(), 'reps': page.locator('#hero-reps').inner_text()}
    page.locator('#view-circuit').click()
    page.wait_for_timeout(3000)
    assert page.evaluate('window.__qa.sockets.length') == 0
    result = {'actual_browser': True, 'source': 'bundled actual 20-second model recordings',
        'interaction_seconds': round(time.monotonic() - started, 3), 'bench': bench, 'curl': curl,
        'websockets': 0, 'viewport': [1280, 720]}
    video = page.video
    context.close()
    if video:
        result.update(finish_video(browser, Path(video.path()), output, result['interaction_seconds']))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8010')
    parser.add_argument('--skip-video', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'docs/drosolift/evidence/demo-v2'
    output.mkdir(parents=True, exist_ok=True)
    result = {'status': 'running', 'system': platform.platform(),
              'processor': platform.processor(), 'logical_cpus': os.cpu_count()}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
            result.update(browser=browser.version, rendering=render_checks(browser, args.url.rstrip('/'), output))
            if not args.skip_video:
                result['demo'] = record(browser, args.url.rstrip('/'), output)
            browser.close()
        result['status'] = 'passed'
    except Exception as error:
        result.update(status='failed', failure=f'{type(error).__name__}: {error}')
        raise
    finally:
        (output / 'presentation-checks.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
