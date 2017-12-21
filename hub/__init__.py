import asyncio
import importlib
import ssl

import flynn
import nacl.utils
import websockets
from flynn.decoder import InvalidCborError
from nacl.exceptions import CryptoError, BadSignatureError
from nacl.public import PublicKey, Box
from nacl.secret import SecretBox
from websockets.exceptions import ConnectionClosed, InvalidHandshake


class Hub:
    sources = None
    plugins = None
    connections = None

    requests = asyncio.Queue()
    incoming = asyncio.Queue()

    def __init__(self, config):
        self.config = config
        self.connections = set()

        self.sources = dict()
        for source_name in config['hub'].get('sources', '').split():
            source = self._get_module(config, source_name, module_type='sources')
            if source:
                self.sources[source.id] = source

        self.plugins = dict()
        for plugin_name in config['hub'].get('plugins', '').split():
            plugin = self._get_module(config, plugin_name, module_type='plugins')
            if plugin:
                self.plugins[plugin.id] = plugin

    def _get_module(self, config, module_name, module_type=None):
        import_module = module_name

        if config.has_section(module_name):
            config = config[module_name]
            import_module = config.get('module', module_name)

        if '.' not in import_module:
            import_module = "hub.{}.{}".format(module_type, import_module)
        module = importlib.import_module(import_module)

        return module.from_config(module_name, config, self)

    def add_tasks(self, loop):

        if 'local_auth' in self.config:
            loop.create_task(self.get_local_auth())

        if 'local_stream' in self.config:
            loop.create_task(self.get_local_stream())

        for source in self.sources.values():
            loop.create_task(source.get_task(self))
            loop.create_task(self.handle_connect(source))

        loop.create_task(self.get_upstream())
        loop.create_task(self.get_requests())

    def get_tls_context(self):
        if 'tls' in self.config:
            # noinspection PyUnresolvedReferences
            ssl_context = ssl.SSLContext(protocol=self.config['tls'].get('protocol', ssl.PROTOCOL_TLSv1_2))
            ssl_context.load_cert_chain(
                self.config['tls']['certificate'],
                keyfile=self.config['tls']['key'],
                password=self.config['tls'].get('key_password'),
            )
            return ssl_context

    async def get_local_auth(self):
        ssl_context = self.get_tls_context()

        await websockets.serve(
            self.handle_local_auth,
            self.config['local_auth'].get('host', '0.0.0.0'),
            self.config['local_auth'].getint('port', 1337),
            ssl=ssl_context
        )

    # noinspection PyUnusedLocal
    async def handle_local_auth(self, client, path):
        # 1. Get the public key
        client_public_key = await client.recv()

        # 2. Sign it
        signed = self.config['keys']['facade_signing_key'].sign(client_public_key)

        # 3. Send the signature back
        await client.send(flynn.dumps({
            'signature': signed.signature,
            'key': self.config['keys']['server_public_key'].encode(),
        }))

    async def get_local_stream(self):
        ssl_context = self.get_tls_context()
        await websockets.serve(
            self.handle_local_stream,
            self.config['local_stream'].get('host', '0.0.0.0'),
            self.config['local_stream'].getint('port', 1338),
            ssl=ssl_context
        )

    # noinspection PyUnusedLocal
    async def handle_local_stream(self, client, path):
        self.connections.add(client)
        try:
            while True:
                message = await client.recv()
                await self.requests.put([client, flynn.loads(message)])
        except ConnectionClosed:
            pass
        finally:
            self.connections.remove(client)

    async def get_requests(self):
        while True:
            client, message = await self.requests.get()
            await self.handle_request(client, message)

    async def handle_incoming(self, source, message):
        for plugin in self.plugins.values():
            await plugin.on_source_message(source, message)

    async def handle_connect(self, source):
        for plugin in self.plugins.values():
            await plugin.on_source_connect(source)

    async def reply(self, client, target_public_key, payload):
        box = Box(self.config['keys']['server_private_key'], target_public_key)
        nonce = nacl.utils.random(Box.NONCE_SIZE)
        message = {
            'key': target_public_key.encode(),
            'nonce': nonce,
            'payload':
                box.encrypt(flynn.dumps(payload), nonce).ciphertext,
        }
        await client.send(flynn.dumps(message))

    async def broadcast(self, payload):
        box = SecretBox(bytes(self.config['keys']['server_public_key']))
        nonce = nacl.utils.random(Box.NONCE_SIZE)
        message = {
            'nonce': nonce,
            'payload':
                box.encrypt(flynn.dumps(payload), nonce).ciphertext,
        }
        cbor_message = flynn.dumps(message)
        for client in self.connections:
            try:
                await client.send(cbor_message)
            except ConnectionClosed:
                self.connections.remove(client)

    async def handle_request(self, client, message):
        client_public_key = PublicKey(message['key'])

        # Check if it is signed
        verification = message['verification'] + message['key']
        try:
            self.config['keys']['facade_signing_key'].verify_key.verify(verification)
        except BadSignatureError:
            await self.reply(client, client_public_key, {'error': 'Who are you?'})
        else:
            nonce = message['nonce']
            cipher_text = message['payload']
            try:
                box = Box(self.config['keys']['server_private_key'], client_public_key)
                request = flynn.loads(box.decrypt(cipher_text, nonce))
                if request == 'hello':  # Pong
                    await self.reply(client, client_public_key, request)
                    for plugin in self.plugins.values():
                        await plugin.on_client_connect(client, client_public_key)
                else:
                    for plugin in self.plugins.values():
                        await plugin.on_client_request(client, client_public_key, request)

            except CryptoError:
                pass  # TODO: what to do, what to do.
            except InvalidCborError:
                pass  # TODO: what to do, what to do.

    async def get_upstream(self):
        wait_time = 1
        while True:
            try:
                async with websockets.connect(self.config['hub']['upstream']) as upstream:
                    wait_time = 1
                    self.connections.add(upstream)
                    try:
                        while True:
                            message = await upstream.recv()
                            await self.requests.put([upstream, flynn.loads(message)])
                    except ConnectionClosed:
                        pass
                    finally:
                        self.connections.remove(upstream)
            except (ConnectionRefusedError, OSError, InvalidHandshake):
                # We will wait a while before reconnecting
                await asyncio.sleep(wait_time)
                wait_time *= 1.5
