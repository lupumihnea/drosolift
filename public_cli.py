"""Separate public entrypoint; legacy gym-web and its saved run remain unchanged."""

import argparse
import math
import os
from pathlib import Path
from urllib.parse import urlsplit

from aiohttp import web

from brain.gym_circuit import load_gym_circuits
from experiments.experiment_002 import create_gym
from frontend.public_server import PublicConfig, create_public_app
from frontend.server import ObservatoryConfig
from frontend.session_store import SessionStore, SessionStoreError
from simulation.gym import validate_population
from world.apparatus_feedback import FEEDBACK_PROFILES


def add_public_command(commands: argparse._SubParsersAction, root: Path) -> None:
    parser = commands.add_parser('public-web', help='Serve independent durable public gym sessions')
    parser.add_argument('--session-db', type=Path, required=True, help='SQLite file on a persistent volume; one gateway worker')
    parser.add_argument('--dist-path', type=Path, default=root / 'frontend/web/dist-public', help='Public frontend build directory')
    parser.add_argument('--allow-origin', action='append', required=True, help='Exact browser origin; repeat for each allowed origin')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8003)
    parser.add_argument('--flies', type=int, default=1)
    parser.add_argument('--fps', type=float, default=10.0)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--feedback', choices=FEEDBACK_PROFILES, default='apparatus-visual-v1')
    parser.add_argument('--no-learning', action='store_true')
    parser.add_argument('--max-active', type=int, default=4)
    parser.add_argument('--max-clients', type=int, default=2)
    parser.add_argument('--max-profiles', type=int, default=256)
    parser.add_argument('--cookie-days', type=int, default=30)
    parser.add_argument('--idle-seconds', type=float, default=300)
    parser.add_argument('--insecure-local-cookie', action='store_true', help='HTTP loopback development only; production cookies are Secure')


def run_public(options: argparse.Namespace, root: Path) -> int:
    try:
        validate_population(options.flies)
        if not math.isfinite(options.fps) or not 1 <= options.fps <= 30:
            raise ValueError('Public simulation fps must be finite within1..30')
        if not 1 <= options.port <= 65535:
            raise ValueError('Port must be within1..65535')
        if not 1 <= options.max_profiles <= 10000:
            raise ValueError('Durable profile limit must be within1..10000')
        local = {'localhost', '127.0.0.1', '::1'}
        if any(urlsplit(origin).scheme != 'https' and urlsplit(origin).hostname not in local for origin in options.allow_origin):
            raise ValueError('Public non-loopback browser origins require HTTPS')
        if options.insecure_local_cookie:
            if options.host not in local or any(urlsplit(origin).hostname not in local for origin in options.allow_origin):
                raise ValueError('Insecure cookies are restricted to loopback development')
        config = PublicConfig(tuple(options.allow_origin), secure_cookie=not options.insecure_local_cookie,
            max_active=options.max_active, max_clients=options.max_clients,
            cookie_days=options.cookie_days, idle_seconds=options.idle_seconds)
        if not (options.dist_path / 'index.html').is_file():
            raise ValueError("Public browser assets missing; run 'bun --bun run build:public' in frontend/web")
        # Source hashes and every selected edge are validated once before accepting
        # visitors; each session receives fresh mutable model/body/memory objects.
        circuits = load_gym_circuits(root)
        store = SessionStore(options.session_db, max_sessions=options.max_profiles)
        try:
            app = create_public_app(config=config,
                observatory=ObservatoryConfig('compact', circuits[0].dataset, options.fps, options.dist_path),
                store=store, model_factory=lambda: create_gym(*circuits, population=options.flies,
                    seed=options.seed, learning_enabled=not options.no_learning, feedback=options.feedback))
            print(f'Public isolated gym: http://{options.host}:{options.port}; PID {os.getpid()}; one worker; max {options.max_active} active sessions')
            web.run_app(app, host=options.host, port=options.port, print=None)
        finally:
            store.close()
        return 0
    except (OSError, ValueError, SessionStoreError) as error:
        print(f'Public gym error: {error}')
        return 1
