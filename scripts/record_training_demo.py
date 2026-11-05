"""Record the actual live fly selection, weight, X-ray and exercise audience flow."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

from playwright.sync_api import sync_playwright
from scripts.check_demo_presentation import finish_video
from scripts.check_drosolift_browser import OBSERVE, paused, ready, until

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    output = ROOT / 'docs/drosolift/evidence/demo-v3'
    output.mkdir(parents=True, exist_ok=True)
    result = {'status': 'running', 'source': 'actual live model and browser controls'}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe', headless=True)
            context = browser.new_context(viewport={'width': 1280, 'height': 720},
                record_video_dir=str(output / 'video'), record_video_size={'width': 1280, 'height': 720})
            context.add_init_script(OBSERVE)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            ready(page, args.url + '/?renderer=webgl')
            fly_id = page.evaluate('window.__qa.frame.flies.at(-1).id')
            page.locator('#training-fly').select_option(fly_id)
            paused(page, False)
            until(page, f"window.__qa.control.exercises.find(s=>s.fly_id==='{fly_id}').pending_kind===null")
            if page.evaluate(f"window.__qa.frame.flies.find(f=>f.id==='{fly_id}').exercise.kind") != 'bench_press':
                page.locator('#exercise-bench').click()
                until(page, f"window.__qa.frame.flies.find(f=>f.id==='{fly_id}').exercise.kind==='bench_press'", 120_000)
            started = time.monotonic()
            page.wait_for_timeout(3000)
            if page.locator('#apply-load').is_enabled():
                page.locator('#apply-load').click()
            page.wait_for_timeout(2500)
            page.locator('#xray-toggle').click()
            page.wait_for_timeout(2500)
            page.locator('#xray-toggle').click()
            page.locator('#exercise-curl').click()
            until(page, f"window.__qa.frame.flies.find(f=>f.id==='{fly_id}').exercise.kind==='bicep_curl'", 120_000)
            page.wait_for_timeout(5000)
            page.locator('#neural-cell-colors').click()
            page.wait_for_timeout(2000)
            page.locator('#neural-live').click()
            page.wait_for_timeout(1000)
            interaction = time.monotonic() - started
            assert interaction < 29.25, f'Wait for a faster safe-boundary capture: {interaction}s'
            result.update(fly=fly_id, browser=browser.version, interaction_seconds=round(interaction, 3),
                viewport=[1280, 720], final_frame=page.evaluate('window.__qa.frame'),
                ui_commands=page.evaluate("window.__qa.sent.filter(m=>['set_load','set_exercise'].includes(m.type))"), page_errors=errors)
            assert not errors, errors
            video = page.video
            context.close()
            assert video
            result.update(finish_video(browser, Path(video.path()), output, interaction, 'drosolift-training-demo.webm'))
            browser.close()
        result['status'] = 'passed'
    except Exception as error:
        result.update(status='failed', failure=f'{type(error).__name__}: {error}')
        raise
    finally:
        (output / 'video-checks.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({key: value for key, value in result.items() if key not in ['final_frame', 'ui_commands']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
