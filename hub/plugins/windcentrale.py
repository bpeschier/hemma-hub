from datetime import datetime
from .base import Plugin
from ..sources.windcentrale import WINDMILLS


class WindcentralePlugin(Plugin):
    label = "windcentrale"
    name = "Windcentrale"

    mills = None
    mill_data = None

    def __init__(self, plugin_id, hub, mills):
        super().__init__(plugin_id, hub)
        self.mills = dict(mills)
        self.mill_data = {}

    async def on_source_message(self, source, message):
        if 'name' in message and message['name'] == 'windmill':
            mill_id = message["data"]["id"]
            amount = self.mills[mill_id]
            state = {
                'id': mill_id,
                'power': message["data"]["per_share"] * amount,
                'performance': message["data"]["performance"],
                'timestamp': int(datetime.now().timestamp() * 1000),
                'name': dict(WINDMILLS)[mill_id],
            }
            self.mill_data[mill_id] = state

            if self.mill_data:
                await self.broadcast(list(self.mill_data.values()))

    async def on_client_connect(self, client, client_key):
        if self.mill_data:
            await self.reply(client, client_key, list(self.mill_data.values()))

    async def on_client_request(self, client, client_key, request):
        pass


def from_config(plugin_id, config, hub):
    mill_ids = dict((v, k) for k, v in WINDMILLS)
    mills = [i.split(':') for i in config.get('mills').split(',')]
    mills = ((mill_ids[k], int(v)) for (k, v) in mills)
    return WindcentralePlugin(plugin_id, hub, mills)
