"""One controlled normal-entrypoint startup and scoped process-tree cleanup."""
import ctypes
import json
import os
from pathlib import Path
import platform
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

if os.name != 'nt':
    raise SystemExit('This startup/resource probe targets Windows; use the ordinary main.py entrypoint on other platforms.')

root = Path(__file__).resolve().parents[1]
evidence = root / 'docs/drosolift/evidence'
with socket.socket() as probe:
    if probe.connect_ex(('127.0.0.1', 8002)) == 0:
        raise RuntimeError('Measurement port 8002 is already occupied')
with tempfile.TemporaryDirectory() as temporary:
    command = [sys.executable, '-u', '-B', 'main.py', 'gym-web', '--flies', '1',
               '--seed', '7', '--port', '8002', '--no-learning', '--memory-dir', temporary]
    with (evidence / 'startup-server.log').open('w', encoding='utf-8') as log:
        started = time.perf_counter()
        process = subprocess.Popen(command, cwd=root, stdout=log, stderr=subprocess.STDOUT)
        server_pid = None
        try:
            while True:
                if process.poll() is not None:
                    raise RuntimeError(f'Server exited with {process.returncode}')
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8002/health', timeout=.5) as response:
                        health = json.load(response)
                    break
                except (urllib.error.URLError, TimeoutError, ConnectionError):
                    if time.perf_counter() - started > 60:
                        raise TimeoutError('No ready health endpoint after 60 seconds')
                    time.sleep(.05)
            elapsed = time.perf_counter() - started
            ports = subprocess.check_output(['netstat', '-ano'], text=True)
            match = re.search(r'TCP\s+127\.0\.0\.1:8002\s+\S+\s+LISTENING\s+(\d+)', ports)
            server_pid = int(match[1]) if match else process.pid
            from ctypes import wintypes
            class Memory(ctypes.Structure):
                _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                    (name, ctypes.c_size_t) for name in ['PeakWorkingSetSize', 'WorkingSetSize',
                    'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                    'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage']]
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel.OpenProcess(0x0400 | 0x0010, False, server_pid)
            counters = Memory()
            counters.cb = ctypes.sizeof(counters)
            psapi = ctypes.WinDLL('psapi', use_last_error=True)
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Memory), wintypes.DWORD]
            measured = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb) if handle else 0
            if handle:
                kernel.CloseHandle(handle)
            result = {'command': 'python -u -B main.py gym-web --flies 1 --seed 7 --port 8002 --no-learning --memory-dir <fresh temporary directory>',
                      'ready_seconds': elapsed, 'health': health, 'pid': server_pid,
                      'working_set_bytes': counters.WorkingSetSize if measured else None,
                      'peak_working_set_bytes': counters.PeakWorkingSetSize if measured else None,
                      'machine': platform.node(), 'os': platform.platform(),
                      'python': platform.python_version(),
                      'note': 'Single observed startup after source-file cache warmup; not a cold-install benchmark.'}
            (evidence / 'startup.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(result, indent=2))
        finally:
            if server_pid is not None and server_pid != process.pid:
                try:
                    os.kill(server_pid, signal.SIGTERM)
                except OSError:
                    pass
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
