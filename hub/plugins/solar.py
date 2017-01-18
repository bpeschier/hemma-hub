from datetime import datetime

from .base import Plugin


class SolarPlugin(Plugin):
    label = "solar"

    solar_states = None
    solar_timestamps = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.solar_states = []
        self.solar_timestamps = []

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

    async def on_source_connect(self, source):
        # source.command(name='solar.get', address=self.meter_address, callback=self.handle_solar)
        pass

    async def on_source_message(self, source, message):
        if 'name' in message and message['name'] == 'solar':

            self.solar_states.append(message["data"]["solar"])
            self.solar_timestamps.append(int(datetime.now().timestamp() * 1000))
            self.solar_states = self.solar_states[-10:]
            self.solar_timestamps = self.solar_timestamps[-10:]

            if self.solar_states:
                await self.broadcast(self.readings)

    async def on_client_connect(self, client, client_key):
        await self.reply(client, client_key, self.readings)

    async def on_client_request(self, client, client_key, request):
        pass


def from_config(plugin_id, config, hub):
    return SolarPlugin(plugin_id, hub)
