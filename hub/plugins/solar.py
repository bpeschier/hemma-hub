from datetime import datetime

from .base import Plugin


class SolarPlugin(Plugin):
    label = "solar"

    solar_states = None
    solar_timestamps = None

    def __init__(self, plugin_id, hub, source_target):
        super().__init__(plugin_id, hub)
        self.solar_states = []
        self.solar_timestamps = []
        self.source_target = source_target

    @property
    def production(self):
        if len(self.solar_states) < 2:
            return 0

        def _get_production(diff, t1, t2):
            if t1 == t2:
                return 0
            return diff // ((t2 - t1) / 3600000)

        produced = _get_production(self.solar_states[-1] - self.solar_states[-2], self.solar_timestamps[-2],
                                   self.solar_timestamps[-1])

        return produced

    @property
    def delivered(self):
        return self.solar_states[-1] if self.solar_states else 0

    @property
    def timestamp(self):
        return self.solar_timestamps[-1] if self.solar_timestamps else None

    @property
    def readings(self):
        return {
            'delivered': self.delivered,
            'production': self.production,
            'timestamp': self.timestamp,
        }

    async def update_solar(self, solar_value, reset=False):
        if reset:
            self.solar_states = []
            self.solar_timestamps = []

        self.solar_states.append(solar_value)
        self.solar_timestamps.append(int(datetime.now().timestamp() * 1000))
        self.solar_states = self.solar_states[-10:]
        self.solar_timestamps = self.solar_timestamps[-10:]

        if self.solar_states:
            await self.broadcast(self.readings)

    async def on_source_connect(self, source):
        if source == self.source_target:
            solar_value = await source.request(4, 'solar.get')
            if solar_value and 'solar' in solar_value:
                await self.update_solar(solar_value['solar'])

    async def on_source_message(self, source, message):
        if 'name' in message and message['name'] == 'solar':
            await self.update_solar(message["data"]["solar"])

    async def on_client_connect(self, client, client_key):
        await self.reply(client, client_key, self.readings)

    async def on_client_request(self, client, client_key, request):
        if request.get('target') == 'solar':
            solar_value = await self.source_target.request(4, 'solar.set', solar=request.get('data', 0))
            if solar_value and 'solar' in solar_value:
                await self.update_solar(solar_value['solar'], reset=True)


def from_config(plugin_id, config, hub):
    return SolarPlugin(plugin_id, hub, hub.sources['bridge'])
