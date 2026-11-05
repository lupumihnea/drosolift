"""Cookie-isolated public gateway around the unchanged compact gym mechanics."""

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
import hashlib
import logging
import math
import re
import secrets
import time
from urllib.parse import urlsplit
from uuid import uuid4

from aiohttp import WSMsgType, web

from frontend.gym_server import GymObservatoryServer
from frontend.server import ObservatoryConfig
from frontend.session_store import SessionStore, SessionStoreError, SessionStoreFull
from simulation.gym import GymSimulation


COOKIE_NAME = 'drosolift_session'
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PublicConfig:
    allowed_origins: tuple[str, ...]
    secure_cookie: bool = True
    cookie_days: int = 30
    max_active: int = 4
    max_clients: int = 2
    idle_seconds: float = 300.0
    cleanup_seconds: float = 15.0

    def __post_init__(self) -> None:
        if not self.allowed_origins:
            raise ValueError('At least one exact browser origin is required')
        for origin in self.allowed_origins:
            parsed = urlsplit(origin)
            parsed.port  # Reject invalid port syntax before accepting browser traffic.
            if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username
                    or parsed.password or parsed.path or parsed.query or parsed.fragment
                    or origin != f'{parsed.scheme}://{parsed.netloc}'):
                raise ValueError('Allowed origins must be exact HTTP(S) origins without paths')
        for value, maximum in ((self.max_active, 64), (self.max_clients, 8), (self.cookie_days, 90)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError('Public session limits are invalid')
        for value in (self.idle_seconds, self.cleanup_seconds):
            if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
                raise ValueError('Public session intervals must be finite and positive')


@dataclass(slots=True)
class ActiveSession:
    key: str
    public_id: str
    server: GymObservatoryServer
    last_seen: float
    clients: int = 0
    task: asyncio.Task | None = None
    failed: bool = False


class PublicGateway:
    """One worker, bounded active simulations; disconnected visitors earn no work."""

    def __init__(self, config: PublicConfig, observatory: ObservatoryConfig,
                 store: SessionStore, model_factory: Callable[[], GymSimulation]) -> None:
        self.config = config
        self.observatory = observatory
        self.store = store
        self.model_factory = model_factory
        self.sessions: dict[str, ActiveSession] = {}
        self.lock = asyncio.Lock()

    def require_origin(self, request: web.Request) -> str:
        origin = request.headers.get('Origin')
        if origin not in self.config.allowed_origins:
            raise web.HTTPForbidden(text='A configured browser Origin is required')
        return origin

    @staticmethod
    def cookie_key(request: web.Request) -> str | None:
        token = request.cookies.get(COOKIE_NAME, '')
        if re.fullmatch(r'[A-Za-z0-9_-]{43}', token) is None:
            return None
        return hashlib.sha256(token.encode('ascii')).hexdigest()

    def checkpoint(self, session: ActiveSession) -> None:
        from experiments.session_checkpoint import snapshot

        self.store.put(session.key, session.public_id,
            {'format': 'drosolift-public-session', 'version': 1,
             'simulation': snapshot(session.server.simulation),
             'server': session.server.export_observer_state()},
            now=time.time(), ttl=self.config.cookie_days * 86400)

    def _create_active(self, key: str, public_id: str, payload: dict | None) -> ActiveSession:
        from experiments.session_checkpoint import restore
        from frontend.command_journal import CommandJournal

        simulation = self.model_factory()
        state = {}
        if payload is not None:
            if payload.get('format') != 'drosolift-public-session' or payload.get('version') != 1:
                raise SessionStoreError('Unsupported public session checkpoint')
            restore(simulation, payload['simulation'])
            state = payload['server']
            if (not isinstance(state, dict) or not isinstance(state.get('run_id'), str)
                    or type(state.get('running')) is not bool or not isinstance(state.get('run_metadata'), dict)
                    or state['run_metadata'].get('run_id') != state['run_id']
                    or state['run_metadata'].get('dt') != 1 / self.observatory.fps):
                raise SessionStoreError('Invalid saved observer state')
        run_id = state.get('run_id', str(uuid4()))
        journal = CommandJournal(self.store.connection, session_id=key, run_id=run_id)
        server = GymObservatoryServer(simulation, self.observatory,
            run_id=run_id, command_journal=journal, running=state.get('running', True),
            run_metadata=state.get('run_metadata'), command_rate_limit=(120, 60.0))
        active = ActiveSession(key, public_id, server, time.time())
        def save_boundary(_):
            try:
                self.checkpoint(active)
            except Exception:
                active.failed = True
                server.on_boundary = None
                raise

        server.on_boundary = save_boundary
        return active

    async def _fail(self, session: ActiveSession) -> None:
        session.failed = True
        session.server.running = False
        session.server.on_boundary = None
        for socket in tuple(session.server._clients):
            await socket.close(code=1011, message=b'Session checkpoint unavailable; reconnect after server recovery')

    async def _run_clock(self, session: ActiveSession) -> None:
        try:
            await session.server.clock()
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception('Public session clock stopped; original durable checkpoint retained')
            await self._fail(session)

    async def _stop_clock(self, session: ActiveSession) -> None:
        if session.task is not None:
            session.task.cancel()
            with suppress(asyncio.CancelledError):
                await session.task
            session.task = None

    async def _free_slot(self) -> None:
        if len(self.sessions) < self.config.max_active:
            return
        idle = sorted((session for session in self.sessions.values() if session.clients == 0), key=lambda s: s.last_seen)
        if not idle:
            raise web.HTTPServiceUnavailable(text='All active simulation slots are occupied', headers={'Retry-After': '15'})
        session = idle[0]
        await self._stop_clock(session)
        if not session.failed:
            self.checkpoint(session)
        await session.server.close()
        del self.sessions[session.key]

    async def _resolve(self, request: web.Request, *, create: bool) -> tuple[ActiveSession, bool, str | None]:
        key = self.cookie_key(request)
        if key in self.sessions:
            session = self.sessions[key]
            if session.failed:
                raise web.HTTPServiceUnavailable(text='Session needs server recovery; durable checkpoint retained')
            session.last_seen = time.time()
            return session, True, None
        saved = self.store.get(key, now=time.time()) if key else None
        if saved is None and not create:
            raise web.HTTPUnauthorized(text='Create or resume this browser session first')
        await self._free_slot()
        token = None
        if saved is None:
            token = secrets.token_urlsafe(32)
            key = hashlib.sha256(token.encode('ascii')).hexdigest()
        active = self._create_active(key, saved.public_id if saved else str(uuid4()), saved.checkpoint if saved else None)
        self.checkpoint(active)
        self.sessions[key] = active
        return active, saved is not None, token

    async def bootstrap(self, request: web.Request) -> web.Response:
        self.require_origin(request)
        if request.query or await request.read():
            raise web.HTTPBadRequest(text='Session bootstrap does not accept identity parameters or a request body')
        try:
            async with self.lock:
                session, resumed, token = await self._resolve(request, create=True)
                self.checkpoint(session)
            response = web.json_response({'run_id': session.server.run_id, 'resumed': resumed,
                'websocket': '/ws', 'expires_in': self.config.cookie_days * 86400, 'max_flies': 10})
            # Refresh an existing browser's lifetime without exposing its credential.
            response.set_cookie(COOKIE_NAME, token or request.cookies[COOKIE_NAME],
                max_age=self.config.cookie_days * 86400, path='/', httponly=True,
                secure=self.config.secure_cookie, samesite='Lax')
            response.headers['Cache-Control'] = 'no-store'
            return response
        except (SessionStoreError, ValueError, KeyError, TypeError) as error:
            LOGGER.warning('Public session initialization rejected: %s', error)
            message = 'Saved session unavailable; retained without resetting' if not isinstance(error, SessionStoreFull) else 'Durable session capacity reached'
            raise web.HTTPServiceUnavailable(text=message, headers={'Retry-After': '30'}) from error

    async def websocket(self, request: web.Request) -> web.WebSocketResponse:
        self.require_origin(request)
        if any(key != 'controls' for key in request.query):
            raise web.HTTPBadRequest(text='Session identity is accepted only from the browser cookie')
        try:
            async with self.lock:
                session, _, _ = await self._resolve(request, create=False)
                if session.clients >= self.config.max_clients:
                    raise web.HTTPTooManyRequests(text='This session has reached its socket limit')
                session.clients += 1
        except (SessionStoreError, ValueError, KeyError, TypeError) as error:
            raise web.HTTPServiceUnavailable(text='Saved session unavailable; retained without resetting') from error
        server = session.server
        socket = web.WebSocketResponse(max_msg_size=1024, heartbeat=30)
        try:
            await socket.prepare(request)
            server._clients.add(socket)
            await socket.send_json(server._hello_message())
            await socket.send_json({'type': 'running', 'running': server.running})
            await server._send_additional_initial_state(socket, request)
            await socket.send_json(server._latest_frame)
            if session.task is None:
                session.task = asyncio.create_task(self._run_clock(session))
            async for message in socket:
                session.last_seen = time.time()
                if message.type is WSMsgType.TEXT:
                    try:
                        await server._handle_command(socket, message.data)
                    except Exception:
                        LOGGER.exception('Public command stopped; original durable checkpoint retained')
                        await self._fail(session)
                        break
                elif message.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
                else:
                    await server._send_command_error(socket)
        finally:
            server._clients.discard(socket)
            server._control_clients.discard(socket)
            async with self.lock:
                session.clients -= 1
                session.last_seen = time.time()
                if session.clients == 0:
                    await self._stop_clock(session)
                    if not session.failed:
                        self.checkpoint(session)
        return socket

    async def cleanup_idle(self) -> None:
        while True:
            await asyncio.sleep(self.config.cleanup_seconds)
            async with self.lock:
                for key, session in tuple(self.sessions.items()):
                    if session.clients == 0 and time.time() - session.last_seen >= self.config.idle_seconds:
                        await self._stop_clock(session)
                        if not session.failed:
                            self.checkpoint(session)
                        await session.server.close()
                        del self.sessions[key]

    async def close(self) -> None:
        for session in tuple(self.sessions.values()):
            await self._stop_clock(session)
            if not session.failed:
                self.checkpoint(session)
            await session.server.close()
        self.sessions.clear()


def create_public_app(*, config: PublicConfig, observatory: ObservatoryConfig, store: SessionStore,
                      model_factory: Callable[[], GymSimulation]) -> web.Application:
    """Serve exact-origin cookie bootstrap plus independently clocked model sockets."""
    if not (observatory.dist_path / 'index.html').is_file():
        raise FileNotFoundError('Browser assets are missing; build the frontend first')
    gateway = PublicGateway(config, observatory, store, model_factory)

    @web.middleware
    async def cors(request: web.Request, handler):
        if request.path not in ('/api/session', '/ws'):
            return await handler(request)
        origin = gateway.require_origin(request)
        if request.method == 'OPTIONS' and request.path == '/api/session':
            response = web.Response(status=204)
        else:
            try:
                response = await handler(request)
            except web.HTTPException as error:
                response = web.Response(status=error.status, reason=error.reason, body=error.body, headers=error.headers)
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Vary'] = 'Origin'
        return response

    app = web.Application(client_max_size=1024, middlewares=[cors])
    app.router.add_post('/api/session', gateway.bootstrap)
    async def preflight(_: web.Request) -> web.Response:
        return web.Response(status=204)

    app.router.add_options('/api/session', preflight)
    app.router.add_get('/ws', gateway.websocket)

    async def health(_: web.Request) -> web.Response:
        return web.json_response({'status': 'ready', 'mode': 'isolated-sessions',
            'active_sessions': len(gateway.sessions), 'max_active': config.max_active})

    async def index(_: web.Request) -> web.FileResponse:
        return web.FileResponse(observatory.dist_path / 'index.html')

    app.router.add_get('/health', health)
    app.router.add_get('/', index)
    for name in ('assets', 'samples'):
        if (observatory.dist_path / name).is_dir():
            app.router.add_static(f'/{name}/', observatory.dist_path / name, show_index=False)
    if (observatory.dist_path / 'favicon.svg').is_file():
        async def favicon(_: web.Request) -> web.FileResponse:
            return web.FileResponse(observatory.dist_path / 'favicon.svg')
        app.router.add_get('/favicon.svg', favicon)

    async def shutdown(_):
        await gateway.close()

    app.on_shutdown.append(shutdown)

    async def lifecycle(_):
        task = asyncio.create_task(gateway.cleanup_idle())
        yield
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await gateway.close()

    app.cleanup_ctx.append(lifecycle)
    return app
