"""Verify a produced conference archive, its MIME server and exact static replay."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import json
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
import zipfile

from playwright.sync_api import sync_playwright


def load_recorded_scenarios(destination: Path) -> dict[str, dict]:
    """Require both upgraded runs and their actual same-step apparatus inputs."""
    scenarios = {}
    for kind, name in (('bench_press', 'demo-bench'), ('bicep_curl', 'demo-curl')):
        recording = json.loads((destination / f'samples/{name}.json').read_text(encoding='utf-8'))
        metadata = recording.get('metadata', {})
        frames = recording.get('frames', [])
        controls = metadata.get('control_history', [])
        if (recording.get('format') != 'drosolift-recording' or recording.get('version') != 1
                or metadata.get('exercise') != kind or metadata.get('feedback_profile') != 'apparatus-visual-v1'
                or not frames or len(controls) != len(frames)):
            raise ValueError(f'Incomplete recorded exercise/provenance: {name}')
        for frame, control in zip(frames, controls, strict=True):
            if (frame['flies'][0]['exercise']['kind'] != kind
                    or (control['step'], control['elapsed']) != (frame['step'], frame['elapsed'])):
                raise ValueError(f'Unaligned recorded exercise/feedback: {name}')
        scenarios[kind] = recording
    return scenarios


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, default=root/'data/runs/drosolift-conference.zip')
    parser.add_argument('--output', type=Path, default=root/'docs/drosolift/evidence/package-verification.json')
    parser.add_argument('--review-directory', type=Path, default=root/'.tools/conference-review')
    parser.add_argument('--port', type=int, default=8011)
    parser.add_argument('--browser', default='C:/Program Files/Google/Chrome/Application/chrome.exe')
    parser.add_argument('--software', action='store_true', help='Use SwiftShader explicitly; default uses the available native GPU')
    options = parser.parse_args()
    review = options.review_directory.resolve()
    if not review.is_relative_to(root/'.tools') or review.exists():
        parser.error('Use a fresh verification directory inside the implementation .tools folder')
    if not 1 <= options.port <= 65534:
        parser.error('Port must be1..65534')
    result = {'archive':options.archive.name,'sha256':hashlib.sha256(options.archive.read_bytes()).hexdigest(),
              'bytes':options.archive.stat().st_size,'browser':options.browser,
              'software_rendering_requested': options.software, 'checks':[]}
    processes=[]
    try:
        with zipfile.ZipFile(options.archive) as archive:
            names=archive.namelist()
            assert names==sorted(names) and len(names)==len(set(names)), 'Archive order/duplicates'
            assert not any(name.lower().endswith('.glb') or any(part in ('raw','node_modules','.git') for part in Path(name).parts) for name in names), 'Restricted/raw asset in ZIP'
            manifest=archive.read('MANIFEST.sha256').decode('utf-8').splitlines()
            assert len(manifest)==len(names)-1
            for row in manifest:
                digest,name=row.split('  ',1)
                assert hashlib.sha256(archive.read(name)).hexdigest()==digest, f'Checksum:{name}'
            destination=review/'container/demo'
            for name in names:
                path=(destination/name).resolve()
                assert path.is_relative_to(destination.resolve()), 'Unsafe archive path'
                assert (archive.getinfo(name).external_attr>>16)&0o170000 != 0o120000, 'Symlink archive member'
            destination.mkdir(parents=True)
            archive.extractall(destination)
            result.update(entries=len(names),manifest_verified=len(manifest),restricted_assets=False)
        for name in ('docs/drosolift/EXERCISES.md', 'docs/science/apparatus-visual-v1.md'):
            if not (destination/name).is_file():
                raise FileNotFoundError(f'Upgraded package methods/provenance is missing: {name}')
        scenarios = load_recorded_scenarios(destination)
        result['samples'] = {kind: {'frames': len(recording['frames']),
                                   'final_repetitions': recording['frames'][-1]['flies'][0]['exercise']['repetitions'],
                                   'feedback_profile': recording['metadata']['feedback_profile']}
                             for kind, recording in scenarios.items()}
        # The bundled server requires an index in its selected directory. This
        # separate QA parent index enables /demo/ without changing package files.
        (destination.parent / 'index.html').write_text('<!doctype html><title>Subpath verification</title>', encoding='utf-8')
        for port,directory,prefix in ((options.port,destination,''),(options.port+1,destination.parent,'demo/')):
            with socket.socket() as probe:
                probe.settimeout(.2)
                if probe.connect_ex(('127.0.0.1', port)) == 0:
                    raise ValueError(f'Verification port {port} is occupied; choose a fresh port pair')
            # The package uses only stdlib. On Windows, starting the base Python
            # avoids a venv launcher whose separately spawned server can outlive it.
            python = getattr(sys, '_base_executable', None) or sys.executable
            process=subprocess.Popen([python,str(destination/'serve.py'),'--directory',str(directory),'--port',str(port)],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            processes.append(process)
            url=f'http://127.0.0.1:{port}/{prefix}'
            for _ in range(100):
                if process.poll() is not None:
                    raise AssertionError(f'Bundled static server exited before readiness on port {port}')
                try:
                    with urlopen(url,timeout=.5) as response:
                        assert response.status==200
                    break
                except OSError:time.sleep(.1)
            else:raise AssertionError('Bundled static server did not start')
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(executable_path=options.browser,headless=True,
                args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'] if options.software else [])
            result['browser_version']=browser.version
            for port,prefix in ((options.port,''),(options.port+1,'demo/')):
                origin=f'http://127.0.0.1:{port}'
                page=browser.new_page(viewport={'width':1280,'height':720},accept_downloads=True)
                sockets=[]; external=[]; errors=[]; module_mime=[]
                page.on('websocket',lambda socket:sockets.append(socket.url))
                page.on('request',lambda request:external.append(request.url)
                        if not request.url.startswith((origin+'/', 'blob:'+origin+'/', 'data:')) else None)
                page.on('pageerror',lambda error:errors.append(str(error)))
                def response_seen(response):
                    if response.url.split('?')[0].endswith('.js'):
                        module_mime.append(response.headers.get('content-type',''))
                page.on('response',response_seen)
                page.goto(f'{origin}/{prefix}',wait_until='networkidle')
                page.wait_for_function("document.querySelector('#connection-label').textContent==='RECORDED' && document.querySelector('#scene').dataset.model==='authored-rig'",timeout=90000)
                page.wait_for_function("document.querySelector('#exercise-bench').getAttribute('aria-pressed')==='true'",timeout=90000)
                for kind, button in (('bench_press', '#exercise-bench'), ('bicep_curl', '#exercise-curl')):
                    recording = scenarios[kind]
                    page.locator(button).click()
                    page.wait_for_function(f"document.querySelector('{button}').getAttribute('aria-pressed')==='true'",timeout=90000)
                    slider=page.locator('#replay-seek'); bounds=slider.bounding_box();assert bounds
                    slider.click(position={'x':bounds['width']*.55,'y':bounds['height']/2})
                    fraction=float(slider.input_value())
                    clock=recording['frames'][0]['elapsed']+fraction*(recording['frames'][-1]['elapsed']-recording['frames'][0]['elapsed'])
                    expected=next(frame for frame in reversed(recording['frames']) if frame['elapsed']<=clock)
                    page.wait_for_function(f"Number(document.querySelector('#step-value').textContent)==={expected['step']}")
                    fly = expected['flies'][0]
                    reps=int(page.locator('#hero-reps').inner_text())
                    assert reps==fly['exercise']['repetitions']
                    assert abs(float(page.locator('#joint-value').inner_text())-fly['exercise']['joint_position']*100)<=.050001
                    selected=int(page.locator('#selected-id').text_content())
                    received=next(row['activity'] for row in fly['frame']['neural']['active'] if row['body_id']==selected)
                    assert float(page.locator('#selected-value').text_content().split()[0])==received
                    control=next(row for row in reversed(recording['metadata']['control_history']) if row['elapsed']<=expected['elapsed'])
                    for side in ('left', 'right'):
                        assert abs(float(page.locator(f'#cue-{side}').text_content())-control['feedback'][0][f'indicator_{side}'])<=.000501
                    details=page.locator('.neuron-details')
                    if details.count() and details.get_attribute('open') is None:
                        details.locator('summary').click()
                    with page.expect_download() as download:
                        page.locator('#export-json').click()
                    exported=json.loads(Path(download.value.path()).read_text(encoding='utf-8'))
                    assert exported['frames']==recording['frames']
                    assert exported['metadata']['exercise']==kind
                    assert exported['metadata']['feedback_profile']=='apparatus-visual-v1'
                    result['checks'].append({'path':'/'+prefix,'exercise':kind,'default_mode':'RECORDED',
                        'seek_step':expected['step'],'seek_repetitions':reps,'exact_export':True,
                        'latched_feedback':True,'selected_neuron':selected,'websocket_connections':len(sockets),
                        'scene_renderer':page.locator('#scene').get_attribute('data-renderer'),
                        'external_requests':external.copy(),'page_errors':errors.copy()})
                assert module_mime and all('javascript' in mime for mime in module_mime), module_mime
                assert not sockets and not external and not errors, (sockets,external,errors)
                result.setdefault('javascript_mime', {})['/'+prefix]=sorted(set(module_mime))
                page.close()
            browser.close()
        result['status']='passed'
    except Exception as error:
        result.update(status='failed',failure=f'{type(error).__name__}: {error}')
        raise
    finally:
        for process in processes:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
        options.output.parent.mkdir(parents=True,exist_ok=True)
        options.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))

if __name__=='__main__':main()
