"""Real-browser isolation and durable restart checks on a separately owned server.

Build dist-public and install Playwright's Chromium first. This script creates its
own temporary SQLite database and subprocess on port 8004; existing demo servers
are untouched. Only received frames and audience controls determine the checks.
Browser A renders the full WebGL2 scene. Browser B deliberately lacks WebGL,
verifying live numerical fallback without duplicating software 3D rendering.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import urlopen

from playwright.sync_api import Error as PlaywrightError, sync_playwright

from scripts.check_drosolift_browser import OBSERVE, capture, graphics_info, paused, ready, until


ROOT = Path(__file__).resolve().parents[1]
NUMERICAL_FALLBACK = """(() => {
  const nativeGetContext = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(kind, ...args) {
    if (['webgl', 'webgl2', 'experimental-webgl'].includes(kind)) return null;
    return nativeGetContext.call(this, kind, ...args);
  };
  try { Object.defineProperty(navigator, 'gpu', {value: undefined}); } catch {}
})();"""


class OwnedServer:
    """Stop only the Popen object created here, including for the crash/restart check."""

    def __init__(self, port: int, database: Path, dist: Path, output: Path):
        self.port, self.database, self.dist, self.output = port, database, dist, output
        self.origin = f'http://127.0.0.1:{port}'
        self.process = None
        self.log = None
        self.starts = 0

    def start(self):
        with socket.socket() as probe:
            probe.settimeout(.25)
            if probe.connect_ex(('127.0.0.1', self.port)) == 0:
                raise RuntimeError(f'Port {self.port} is occupied; no existing server was stopped')
        self.starts += 1
        self.log = (self.output / f'public-server-{self.starts}.log').open('w', encoding='utf-8')
        command = [sys.executable, '-u', '-B', '-X', 'utf8', 'main.py', 'public-web',
                   '--session-db', str(self.database), '--allow-origin', self.origin,
                   '--insecure-local-cookie', '--port', str(self.port), '--dist-path', str(self.dist)]
        self.process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
            stdout=self.log, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f'Public server exited; inspect public-server-{self.starts}.log')
            try:
                with urlopen(self.origin + '/health', timeout=1) as response:
                    if json.load(response).get('mode') == 'isolated-sessions':
                        print(json.dumps({'stage': 'server_ready', 'start': self.starts, 'port': self.port}), flush=True)
                        return
            except (URLError, TimeoutError, OSError):
                pass
            time.sleep(.25)
        raise TimeoutError('Public server did not become ready within 240 seconds')

    def stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                # The checkpoint must survive abrupt termination, not merely a
                # graceful application's final save. Never target an external PID.
                if sys.platform == 'win32':
                    # Windows venv python.exe is a launcher with a child Python
                    # process. Kill precisely this owned tree, not just its launcher.
                    killer = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/taskkill.exe'
                    subprocess.run([str(killer), '/PID', str(self.process.pid), '/T', '/F'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
                else:
                    self.process.kill()
                self.process.wait(timeout=15)
            self.process = None
        if self.log is not None:
            self.log.close()
            self.log = None
        # taskkill waits for the launcher, but Windows can retain its child's
        # listening socket briefly while termination finishes. Wait for release;
        # never attempt to terminate a process which later takes the same port.
        deadline = time.monotonic() + 15
        free_samples = 0
        while time.monotonic() < deadline:
            with socket.socket() as probe:
                probe.settimeout(.25)
                free_samples = free_samples + 1 if probe.connect_ex(('127.0.0.1', self.port)) != 0 else 0
            if free_samples >= 2:
                return
            time.sleep(.1)
        raise RuntimeError(f'Owned server stopped but port {self.port} did not release within 15 seconds')


def launch_browser(playwright, executable: str | None, headed: bool):
    options = {'headless': not headed, 'args': ['--enable-unsafe-swiftshader'], 'timeout': 30_000}
    if executable:
        return playwright.chromium.launch(executable_path=executable, **options)
    try:
        return playwright.chromium.launch(**options)
    except PlaywrightError as original:
        candidates = [
            Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'Google/Chrome/Application/chrome.exe',
            Path(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)')) / 'Microsoft/Edge/Application/msedge.exe',
        ] if sys.platform == 'win32' else []
        for candidate in candidates:
            if candidate.is_file():
                return playwright.chromium.launch(executable_path=str(candidate), **options)
        raise original


def digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def frame(page):
    return page.evaluate('window.__qa.frame')


def acknowledgements(page):
    return page.evaluate("window.__qa.messages.filter(m=>m.type==='command_ack')")


def numerical_fallback(page) -> dict:
    """Exercise actual HTML controls/rates while only WebGL contexts are absent."""
    until(page, "document.querySelector('#graphics-backend').textContent==='3D unavailable'")
    until(page, "document.querySelector('#neuron-map').dataset.anatomy==='failed'")
    assert 'Numerical readings and controls remain available' in page.locator('#scene-loading').inner_text()
    assert page.locator('#scene canvas, #neuron-map canvas').count() == 0
    assert page.locator('#apply-load').is_enabled()
    assert page.locator('#add-training-fly').is_enabled()
    was_running = page.evaluate('window.__qa.running')
    paused(page)
    frozen = frame(page)
    received = {row['body_id']: row['activity'] for row in frozen['flies'][0]['frame']['neural']['active']}
    assert len(received) == 91 and page.locator('#neural-observed-count').inner_text() == '91'
    page.locator('.neuron-details summary').click()
    rows = page.locator('#active-neurons li').evaluate_all("""rows=>rows.map(row=>({
        id:Number(row.dataset.bodyId), value:Number(row.querySelector('.neuron-activity-value').textContent)}))""")
    assert len(rows) == 91 and {row['id']: row['value'] for row in rows} == received
    page.locator('[data-body-id="10783"]').click()
    assert page.locator('#selected-id').inner_text() == '10783'
    assert float(page.locator('#selected-value').inner_text().split()[0]) == received[10783]
    assert page.locator('#neural-rate-history').evaluate("canvas=>canvas.getContext('2d')!==null")
    assert frame(page) == frozen, 'Fallback inspection advanced the paused model'
    page.locator('.neuron-details summary').click()
    if was_running:
        paused(page, False)
    return {'webgl_deliberately_unavailable': True, 'html_pause_and_resume': bool(was_running),
            'exact_received_rates': len(received), 'selected_body_id': 10783, 'canvas_2d_retained': True}


def check(browser, server: OwnedServer, output: Path) -> dict:
    contexts = []
    page_errors, console_errors, failed_requests, bootstrap, requests, sockets = [], [], [], [], [], []
    expected_renderer_diagnostics = []

    def new_page(name, viewport, *, numerical=False):
        context = browser.new_context(viewport=viewport, device_scale_factor=1, locale='en-US')
        contexts.append(context)
        context.add_init_script(OBSERVE)
        if numerical:
            context.add_init_script(NUMERICAL_FALLBACK)
        page = context.new_page()
        page.on('pageerror', lambda error: page_errors.append({'browser': name, 'message': str(error)}))

        def console_received(message):
            if message.type != 'error':
                return
            record = {'browser': name, 'message': message.text}
            # Pinned Three r186 dereferences its deliberately absent WebGL
            # context here; only B's two explicit application init catches are
            # expected. A and every other console/page error remain failures.
            known = message.text.startswith(('3D initialization failed TypeError:', 'Anatomical view failed TypeError:'))
            if numerical and known and "Cannot read properties of null (reading 'getSupportedExtensions')" in message.text:
                expected_renderer_diagnostics.append(record)
            else:
                console_errors.append(record)

        page.on('console', console_received)
        page.on('request', lambda request: requests.append(request.url))
        page.on('requestfailed', lambda request: failed_requests.append({'browser': name, 'path': urlsplit(request.url).path,
                                                                       'failure': request.failure}))
        page.on('websocket', lambda ws: sockets.append(ws.url))

        def response_received(response):
            if urlsplit(response.url).path == '/api/session':
                data = response.json()
                bootstrap.append({'browser': name, 'status': response.status, 'resumed': data.get('resumed'),
                                  'run_id': data.get('run_id'),
                                  'allow_origin': response.headers.get('access-control-allow-origin'),
                                  'allow_credentials': response.headers.get('access-control-allow-credentials')})

        page.on('response', response_received)
        return page

    a = new_page('A', {'width': 1280, 'height': 720})
    b = new_page('B', {'width': 800, 'height': 720}, numerical=True)
    url = server.origin + '/?renderer=webgl&diagnostics=1'
    try:
        ready(a, url)
        print(json.dumps({'stage': 'browser_a_ready'}), flush=True)
        until(a, "window.__qa.frame?.flies[0]?.exercise?.joint_position>.2 && window.__qa.frame.flies[0].exercise.joint_position<.9", 120_000)
        paused(a)
        initial_a = frame(a)
        run_a = a.evaluate('window.__qa.control.run_id')
        ready(b, url, graphics=False)
        until(b, 'window.__qa.frame?.flies[0]?.exercise?.station_id')
        run_b = b.evaluate('window.__qa.control.run_id')
        assert run_a != run_b, 'Separate browser contexts shared a run'
        b_step = frame(b)['step']
        until(b, f'window.__qa.frame.step>={b_step + 10}')
        assert frame(a) == initial_a, 'Pausing A did not freeze its actual model state'
        assert b.evaluate('window.__qa.running') is True
        assert a.evaluate('document.body.dataset.sessionMode') == 'private'
        assert b.evaluate('document.body.dataset.sessionMode') == 'private'
        isolation = {'a_paused_step': initial_a['step'], 'b_from_step': b_step,
                     'b_to_step': frame(b)['step'], 'different_runs': True, 'a_exact_frame_frozen': True}
        print(json.dumps({'stage': 'two_context_isolation_passed'}), flush=True)
        fallback_initial = numerical_fallback(b)
        assert frame(a) == initial_a
        print(json.dumps({'stage': 'live_numerical_fallback_passed', 'exact_rates': 91}), flush=True)

        before_plates = int(a.locator('#scene').get_attribute('data-plate-count'))
        a.locator('#apply-load').click()
        until(a, "window.__qa.control.loads[0].pending_load===.8")
        pending = acknowledgements(a)[-1]
        command = a.evaluate("window.__qa.sent.filter(m=>m.type==='set_load').at(-1)")
        assert pending['status'] == 'pending' and pending['effective_step'] is None
        assert int(a.locator('#scene').get_attribute('data-plate-count')) == before_plates
        assert a.evaluate('window.__qa.control.loads[0].load') == .6
        assert frame(a) == initial_a
        paused(a, False)
        until(a, 'window.__qa.control.loads[0].load===.8', 120_000)
        until(a, "Number(document.querySelector('#scene').dataset.appliedLoad)===.8")
        applied = next(ack for ack in reversed(acknowledgements(a))
                       if ack['command_id'] == command['command_id'] and ack['status'] == 'applied')
        assert int(a.locator('#scene').get_attribute('data-plate-count')) > before_plates
        paused(a)
        a.locator('#add-training-fly').click()
        until(a, "window.__qa.frame.flies.length===2 && document.querySelector('#training-fly').value==='fly-2'")
        until(a, "window.__qa.frame.flies[1].exercise.station_id!==null")
        assert len(frame(b)['flies']) == 1
        assert b.evaluate('window.__qa.control.loads[0].load') == .6
        a.locator('#training-fly').select_option('fly-1')
        before_reload = frame(a)
        a.reload(wait_until='domcontentloaded')
        until(a, "window.__qa.frame && !document.querySelector('#running-toggle').disabled")
        until(a, "document.querySelector('#scene').dataset.model==='authored-rig'")
        until(a, "document.querySelector('#neuron-map').dataset.anatomy==='ready'")
        assert frame(a) == before_reload, 'Reload changed the saved paused profile'
        assert a.evaluate('window.__qa.control.run_id') == run_a
        assert a.evaluate('window.__qa.running') is False
        assert a.evaluate('window.__qa.control.loads[0].load') == .8
        assert len(frame(a)['flies']) == 2
        print(json.dumps({'stage': 'controls_and_reload_passed'}), flush=True)
        capture(a, output, 'public-workout-1280x720.png')
        graphics = graphics_info(a)
        assert graphics['backend'] == 'WebGL2'

        a.set_viewport_size({'width': 1920, 'height': 1080})
        a.locator('.neuron-details summary').click()
        a.locator('[data-body-id="10783"]').click()
        reading = next(row for row in frame(a)['flies'][0]['frame']['neural']['active'] if row['body_id'] == 10783)
        assert a.locator('#selected-id').inner_text() == '10783'
        assert float(a.locator('#selected-value').inner_text().split()[0]) == reading['activity']
        capture(a, output, 'public-selected-neuron-1920x1080.png')
        a.locator('.neuron-details summary').click()
        a.locator('#xray-toggle').click()
        until(a, "Number(document.querySelector('#scene').dataset.overlayObserved)===91")
        a.evaluate('window.scrollTo(0,0)')
        a.wait_for_timeout(300)
        capture(a, output, 'public-neural-xray-1920x1080.png')
        assert frame(a) == before_reload, 'Neural inspection advanced the paused model'
        a.locator('#xray-toggle').click()
        a.set_viewport_size({'width': 390, 'height': 844})
        a.evaluate('window.scrollTo(0,0)')
        a.wait_for_timeout(250)
        assert a.evaluate('document.documentElement.scrollWidth<=innerWidth')
        capture(a, output, 'public-mobile-390x844.png')

        paused(b)
        saved_a, saved_b = frame(a), frame(b)
        # Remove both live sockets before crashing only our own subprocess. The
        # cookies stay in independent browser contexts; no capability is copied.
        a.goto('about:blank')
        b.goto('about:blank')
        server.stop()
        print(json.dumps({'stage': 'owned_process_tree_stopped_for_restart'}), flush=True)
        server.start()
        a.set_viewport_size({'width': 1280, 'height': 720})
        ready(a, url)
        ready(b, url, graphics=False)
        until(b, 'window.__qa.frame')
        assert frame(a) == saved_a, 'A restart did not restore its exact paused frame'
        assert frame(b) == saved_b, 'B restart did not restore its exact paused frame'
        assert a.evaluate('window.__qa.control.run_id') == run_a
        assert b.evaluate('window.__qa.control.run_id') == run_b
        assert a.evaluate('window.__qa.running') is False
        assert b.evaluate('window.__qa.running') is False
        fallback_restored = numerical_fallback(b)
        assert frame(b) == saved_b
        count = len(acknowledgements(a))
        a.evaluate('command=>window.__qa.sockets.at(-1).send(JSON.stringify(command))', command)
        until(a, f"window.__qa.messages.filter(m=>m.type==='command_ack').length>{count}")
        assert acknowledgements(a)[-1] == applied, 'Retry changed its original effective model step'
        assert frame(a) == saved_a, 'Retry reapplied an already completed load'
        conflicting = dict(command, load=1.0)
        a.evaluate('command=>window.__qa.sockets.at(-1).send(JSON.stringify(command))', conflicting)
        until(a, "window.__qa.messages.some(m=>m.type==='error'&&m.code==='command_id_conflict')")
        assert a.evaluate('window.__qa.control.loads[0].load') == .8

        for record in bootstrap:
            assert record['status'] == 200 and record['allow_origin'] == server.origin
            assert record['allow_credentials'] == 'true'
        assert len(bootstrap) >= 5 and all(row['resumed'] for row in bootstrap[2:])
        cookie_metadata = []
        for context in contexts:
            cookies = context.cookies(server.origin)
            assert len(cookies) == 1 and cookies[0]['httpOnly'] and cookies[0]['sameSite'] == 'Lax'
            cookie = cookies[0]
            assert all(cookie['value'] not in url for url in requests + sockets)
            cookie_metadata.append({key: cookie[key] for key in ('name', 'httpOnly', 'sameSite', 'secure', 'path')})
        assert all(urlsplit(url).netloc == urlsplit(server.origin).netloc for url in requests)
        assert all(urlsplit(url).path == '/ws' and set(parse_qs(urlsplit(url).query)) == {'controls'} for url in sockets)
        assert not page_errors, page_errors
        assert not console_errors, console_errors
        assert not failed_requests, failed_requests
        assert len(expected_renderer_diagnostics) == 4, expected_renderer_diagnostics
        with closing(sqlite3.connect(server.database)) as connection:
            journal = connection.execute('SELECT status,COUNT(*) FROM gym_command_journal GROUP BY status').fetchall()
        return {'isolation': isolation, 'weight': {'from': .6, 'to': .8, 'pending': pending, 'applied': applied,
                    'pending_preserves_geometry': True, 'plates_before': before_plates},
                'new_fly_count': 2, 'reload_exact_frame': True,
                'restart': {'abrupt_owned_process': True, 'a_step': saved_a['step'], 'b_step': saved_b['step'],
                            'a_frame_sha256': digest(saved_a), 'b_frame_sha256': digest(saved_b),
                            'exact_both_profiles': True, 'original_retry_ack': True, 'payload_conflict_rejected': True},
                'exact_neuron': {'body_id': 10783, 'activity': reading['activity']},
                'numerical_fallback_b': {'initial': fallback_initial, 'after_restart': fallback_restored,
                                         'expected_renderer_diagnostics': expected_renderer_diagnostics},
                'graphics': graphics, 'bootstrap': bootstrap, 'cookies_without_values': cookie_metadata,
                'websocket_paths': sorted(set(urlsplit(url).path + '?' + urlsplit(url).query for url in sockets)),
                'credential_in_url': False, 'external_requests': 0, 'journal_status_counts': dict(journal),
                'page_errors': page_errors, 'console_errors': console_errors, 'failed_requests': failed_requests}
    finally:
        for context in contexts:
            context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8004)
    parser.add_argument('--dist-path', type=Path, default=ROOT / 'frontend/web/dist-public')
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/drosolift/evidence/publication')
    parser.add_argument('--browser-executable', default=os.environ.get('DROSOLIFT_BROWSER_EXECUTABLE'))
    parser.add_argument('--headed', action='store_true')
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('Use an unprivileged test port within 1024..65535')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    scratch = ROOT / '.tools'
    scratch.mkdir(exist_ok=True)
    result = {'status': 'running', 'python': platform.python_version(), 'platform': platform.platform(),
              'command': 'python -B -m scripts.check_public_sessions', 'port': args.port}
    (output / 'public-browser-checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    try:
        with tempfile.TemporaryDirectory(prefix='public-browser-', dir=scratch) as directory:
            server = OwnedServer(args.port, Path(directory) / 'sessions.sqlite3', args.dist_path.resolve(), output)
            try:
                server.start()
                with sync_playwright() as playwright:
                    browser = launch_browser(playwright, args.browser_executable, args.headed)
                    try:
                        result['browser'] = browser.version
                        result['checks'] = check(browser, server, output)
                    finally:
                        browser.close()
                result['status'] = 'passed'
            finally:
                server.stop()
    except Exception as error:
        result.update(status='failed', failure=f'{type(error).__name__}: {error}')
        raise
    finally:
        (output / 'public-browser-checks.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': result['status'], 'evidence': str(output / 'public-browser-checks.json')}))


if __name__ == '__main__':
    main()
