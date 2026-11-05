"""Public browser cookie jars own isolated, durable actual compact gym sessions."""

import asyncio
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from aiohttp import ClientSession, CookieJar, WSServerHandshakeError
from aiohttp.test_utils import TestServer

from brain.gym_circuit import load_gym_circuits
from experiments.experiment_002 import create_gym
from frontend.public_server import PublicConfig, create_public_app
from frontend.server import ObservatoryConfig
from frontend.session_store import SessionStore


ROOT = Path(__file__).resolve().parents[2]
ORIGIN = 'http://localhost:3000'


class PublicSessionTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.circuits = load_gym_circuits(ROOT)

    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name)
        (self.path / 'index.html').write_text('<main>Public gym</main>')
        self.sessions = []
        self.sockets = []
        self.servers = []
        self.stores = []
        self.server = await self.start_gateway()
        self.a = self.client()
        self.b = self.client()

    def client(self, cookie=None):
        client = ClientSession(cookie_jar=CookieJar(unsafe=True))
        if cookie is not None:
            client.cookie_jar.update_cookies({'drosolift_session': cookie})
        self.sessions.append(client)
        return client

    async def start_gateway(self, **options):
        store = SessionStore(self.path / 'sessions.sqlite3', max_sessions=options.pop('max_stored', 8))
        self.stores.append(store)
        app = create_public_app(
            config=PublicConfig(allowed_origins=(ORIGIN,), secure_cookie=options.pop('secure_cookie', False), **options),
            observatory=ObservatoryConfig('compact', 'male-cns:v1.0', 20, self.path),
            store=store, model_factory=lambda: create_gym(*self.circuits, seed=7, feedback='apparatus-visual-v1'))
        server = TestServer(app)
        await server.start_server()
        self.servers.append(server)
        return server

    async def asyncTearDown(self):
        for socket in self.sockets:
            await socket.close()
        for client in self.sessions:
            await client.close()
        for server in reversed(self.servers):
            await server.close()
        for store in self.stores:
            store.close()
        self.directory.cleanup()

    async def bootstrap(self, client, server=None, origin=ORIGIN):
        return await client.post((server or self.server).make_url('/api/session'), headers={'Origin': origin})

    async def socket(self, client, server=None, query='?controls=1'):
        socket = await client.ws_connect((server or self.server).make_url('/ws' + query), headers={'Origin': ORIGIN})
        self.sockets.append(socket)
        return socket

    async def receive(self, socket, kind):
        for _ in range(1000):
            message = await socket.receive_json(timeout=3)
            if message['type'] == kind:
                return message
        self.fail('Missing ' + kind)

    async def test_separate_cookie_jars_cannot_pause_or_change_each_others_fly_bank(self):
        ra, rb = await self.bootstrap(self.a), await self.bootstrap(self.b)
        self.assertEqual((200, 200), (ra.status, rb.status))
        body_a, body_b = await ra.json(), await rb.json()
        self.assertNotEqual(body_a['run_id'], body_b['run_id'])
        self.assertNotIn('token', body_a)
        self.assertTrue(ra.cookies['drosolift_session']['httponly'])
        self.assertEqual('Lax', ra.cookies['drosolift_session']['samesite'])
        a, b = await self.socket(self.a), await self.socket(self.b)
        await self.receive(a, 'gym_frame')
        await self.receive(b, 'gym_frame')
        await a.send_json({'type': 'set_running', 'running': False, 'command_id': 'pause'})
        await self.receive(a, 'command_ack')
        await a.send_json({'type': 'set_population', 'count': 3})
        self.assertEqual(3, (await self.receive(a, 'population'))['count'])
        fa = await self.receive(a, 'gym_frame')
        fb = await self.receive(b, 'gym_frame')
        self.assertEqual(3, len(fa['flies']))
        self.assertEqual(1, len(fb['flies']))
        frozen = fa['step']
        await asyncio.sleep(.12)
        while fb['step'] == 0:
            fb = await self.receive(b, 'gym_frame')
        self.assertGreater(fb['step'], 0)
        await b.close()
        await a.close()
        a = await self.socket(self.a)
        self.assertEqual(frozen, (await self.receive(a, 'gym_frame'))['step'])

    async def test_restart_restores_same_run_joint_clock_and_retry_ack(self):
        response = await self.bootstrap(self.a)
        original = await response.json()
        cookie = response.cookies['drosolift_session'].value
        a = await self.socket(self.a)
        frame = await self.receive(a, 'gym_frame')
        while frame['flies'][0]['exercise']['joint_position'] == 0:
            frame = await self.receive(a, 'gym_frame')
        await a.send_json({'type': 'set_running', 'running': False, 'command_id': 'pause-restore'})
        ack = await self.receive(a, 'command_ack')
        await a.close()
        a = await self.socket(self.a)
        before = await self.receive(a, 'gym_frame')
        await a.close()
        await self.server.close()
        self.stores[0].close()
        restarted = await self.start_gateway()
        visitor = self.client(cookie)
        response = await self.bootstrap(visitor, restarted)
        restored = await response.json()
        self.assertEqual((True, original['run_id']), (restored['resumed'], restored['run_id']))
        a = await self.socket(visitor, restarted)
        frame = await self.receive(a, 'gym_frame')
        self.assertEqual(before, frame)
        self.assertEqual(ack['effective_step'], frame['step'])
        await a.send_json({'type': 'set_running', 'running': False, 'command_id': 'pause-restore'})
        self.assertEqual(ack, await self.receive(a, 'command_ack'))

    async def test_bootstrap_and_socket_require_explicit_origin_and_cookie(self):
        self.assertEqual(403, (await self.bootstrap(self.a, origin='https://evil.example')).status)
        self.assertEqual(403, (await self.a.post(self.server.make_url('/api/session'))).status)
        with self.assertRaises(WSServerHandshakeError) as failure:
            await self.socket(self.a)
        self.assertEqual(401, failure.exception.status)
        response = await self.a.options(self.server.make_url('/api/session'), headers={'Origin': ORIGIN, 'Access-Control-Request-Method': 'POST'})
        self.assertEqual(204, response.status)
        self.assertEqual(ORIGIN, response.headers['Access-Control-Allow-Origin'])
        self.assertEqual('true', response.headers['Access-Control-Allow-Credentials'])
        self.assertNotEqual('*', response.headers['Access-Control-Allow-Origin'])
        await self.bootstrap(self.a)
        for headers in ({}, {'Origin': 'https://evil.example'}):
            with self.assertRaises(WSServerHandshakeError) as failure:
                await self.a.ws_connect(self.server.make_url('/ws?controls=1'), headers=headers)
            self.assertEqual(403, failure.exception.status)
        with self.assertRaises(WSServerHandshakeError) as failure:
            await self.socket(self.a, query='?controls=1&session_id=someone-else')
        self.assertEqual(400, failure.exception.status)

    async def test_idle_instance_eviction_keeps_cookie_profile_and_freezes_disconnected_clock(self):
        await self.server.close()
        self.server = await self.start_gateway(idle_seconds=.04, cleanup_seconds=.02)
        original = await (await self.bootstrap(self.a)).json()
        a = await self.socket(self.a)
        await self.receive(a, 'gym_frame')
        await a.close()
        a = await self.socket(self.a)
        before = await self.receive(a, 'gym_frame')
        await a.close()
        await asyncio.sleep(.15)
        self.assertEqual(0, (await (await self.a.get(self.server.make_url('/health'))).json())['active_sessions'])
        resumed = await (await self.bootstrap(self.a)).json()
        self.assertEqual(original['run_id'], resumed['run_id'])
        a = await self.socket(self.a)
        self.assertEqual(before, await self.receive(a, 'gym_frame'))

    async def test_session_and_socket_quotas_do_not_replace_existing_sessions(self):
        await self.server.close()
        self.server = await self.start_gateway(max_active=1, max_clients=1)
        await self.bootstrap(self.a)
        a = await self.socket(self.a)
        self.assertEqual(503, (await self.bootstrap(self.b)).status)
        with self.assertRaises(WSServerHandshakeError) as failure:
            await self.socket(self.a)
        self.assertEqual(429, failure.exception.status)
        await a.close()
        self.assertEqual(200, (await self.bootstrap(self.b)).status)

    async def test_corrupt_saved_session_fails_without_silent_new_profile(self):
        response = await self.bootstrap(self.a)
        cookie = response.cookies['drosolift_session'].value
        await self.server.close()
        self.stores[0].close()
        with closing(sqlite3.connect(self.path / 'sessions.sqlite3', isolation_level=None)) as connection:
            connection.execute("UPDATE sessions SET checkpoint = '{}' ")
        restarted = await self.start_gateway()
        visitor = self.client(cookie)
        response = await self.bootstrap(visitor, restarted)
        self.assertEqual(503, response.status)
        self.assertNotIn('drosolift_session', response.cookies)

    async def test_full_saved_profile_quota_preserves_existing_browser(self):
        await self.server.close()
        self.stores[0].close()
        self.server = await self.start_gateway(max_stored=1)
        original = await (await self.bootstrap(self.a)).json()
        response = await self.bootstrap(self.b)
        self.assertEqual(503, response.status)
        self.assertNotIn('drosolift_session', response.cookies)
        restored = await (await self.bootstrap(self.a)).json()
        self.assertEqual(original['run_id'], restored['run_id'])
        self.assertTrue(restored['resumed'])

    async def test_production_cookie_is_host_only_secure_http_only_and_not_a_response_token(self):
        await self.server.close()
        self.server = await self.start_gateway(secure_cookie=True)
        response = await self.bootstrap(self.a)
        self.assertEqual(200, response.status)
        cookie = response.cookies['drosolift_session']
        self.assertTrue(cookie['secure'])
        self.assertTrue(cookie['httponly'])
        self.assertEqual('', cookie['domain'])
        self.assertEqual('/', cookie['path'])
        self.assertEqual(str(30 * 86400), cookie['max-age'])
        self.assertNotIn(cookie.value, await response.text())
