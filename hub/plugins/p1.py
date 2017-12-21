from datetime import datetime

from .base import Plugin


class P1Plugin(Plugin):
    label = "p1"

    state = None
    timestamp = None

    @property
    def energy_delivered(self):
        return self.state['e_d_1'] + self.state['e_d_2']

    @property
    def energy_delivered_current(self):
        return self.state['p_d']

    @property
    def energy_returned(self):
        return self.state['e_r_1'] + self.state['e_r_2']

    @property
    def energy_returned_current(self):
        return self.state['p_r']

    @property
    def energy_consumption(self):
        return self.energy_delivered_current - self.energy_returned_current

    @property
    def gas_delivered(self):
        return self.state['g_d']

    @property
    def readings(self):
        return {
            'energy_delivered': self.energy_delivered,
            'energy_delivered_current': self.energy_delivered_current,
            'energy_returned': self.energy_returned,
            'energy_returned_current': self.energy_returned_current,
            'energy_consumption': self.energy_consumption,
            'gas_delivered': self.gas_delivered,
            'timestamp': self.timestamp,
        }

    async def on_source_connect(self, source):
        # source.command(name='p1.get', address=self.meter_address, callback=self.handle_p1)
        pass

    async def update_p1(self, data):
        self.state = data
        self.timestamp = int(datetime.now().timestamp() * 1000)

        if self.state:
            await self.broadcast(self.readings)

    async def on_source_message(self, source, message):
        if 'name' in message and message['name'] == 'p1':
            await self.update_p1(message["data"])

    async def on_client_connect(self, client, client_key):
        if self.state:
            await self.reply(client, client_key, self.readings)

    async def on_client_request(self, client, client_key, request):
        pass


def from_config(plugin_id, config, hub):
    return P1Plugin(plugin_id, hub)
