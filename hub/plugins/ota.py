import asyncio
from io import StringIO

from intelhex import IntelHex

from .base import Plugin


class OtaPlugin(Plugin):
    block_size = 512

    def __init__(self, plugin_id, hub, source_target):
        super().__init__(plugin_id, hub)
        self.source_target = source_target

    async def on_source_message(self, source, message):
        pass

    async def on_client_request(self, client, client_key, request):
        if request.get('target') == 'ota':
            await self.program(client, request['address'], request['data'])

    async def program(self, client, address, data):
        await self.source_target.command(address, 'otamode')

        file_data = StringIO(data.decode('utf-8'))
        hex_file = IntelHex(file_data)
        hex_size = len(hex_file)

        await asyncio.sleep(3)

        print(await self.source_target.request(0, 'ota.start', address=address))
        for addr in range(0, hex_size, self.block_size):
            bsize = min(self.block_size, hex_size - addr)
            data = hex_file.tobinstr(start=addr, size=bsize)
            if len(data) > 0:
                print(await self.source_target.request(0, 'ota.block', memaddr=addr, size=len(data), data=data))

        await self.source_target.request(0, 'ota.end')


def from_config(plugin_id, config, hub):
    return OtaPlugin(plugin_id, hub, hub.sources['bridge'])
