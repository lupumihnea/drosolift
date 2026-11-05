"""Serve the recorded demo with explicit module MIME types on Windows and POSIX.

The conference archive includes this same standalone standard-library script as
serve.py. No model server, third-party packages or raw sources are required.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class ReplayHandler(SimpleHTTPRequestHandler):
    """Override OS registry MIME guesses that can label JavaScript as text/plain."""
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
        '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css',
        '.json': 'application/json', '.svg': 'image/svg+xml', '.wasm': 'application/wasm'}


def main() -> None:
    location = Path(__file__).resolve().parent
    default = location if (location / 'index.html').is_file() else location.parent / 'frontend/web/dist-replay'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=default)
    parser.add_argument('--port', type=int, default=8010)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or not (args.directory / 'index.html').is_file():
        parser.error('Build the replay first and use a port within 1..65535.')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(ReplayHandler, directory=str(args.directory.resolve())))
    print(f'Recorded DrosoLift demo: http://127.0.0.1:{args.port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
