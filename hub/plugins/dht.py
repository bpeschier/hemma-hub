from datetime import datetime

from .base import Plugin


class DHTPlugin(Plugin):
    label = "dht"

    state = None
    timestamp = None

    async def on_source_message(self, source, message):
        if 'name' in message and message['name'] == 'dht':
            self.state = message["data"]
            self.timestamp = datetime.now().timestamp()

            if self.state:
                await self.broadcast(self.state)

    async def on_client_connect(self, client, client_key):
        if self.state:
            await self.reply(client, client_key, self.state)

    async def on_client_request(self, client, client_key, request):
        pass


def from_config(plugin_id, config, hub):
    return DHTPlugin(plugin_id, hub)
