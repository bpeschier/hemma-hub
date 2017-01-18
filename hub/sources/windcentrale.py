import asyncio
from asyncio.futures import TimeoutError

import aiohttp
from aiohttp.errors import ServerDisconnectedError
from yarl import URL

from .base import Source

WINDCENTRALE_LIVE = 'https://backend.windcentrale.nl/-gxvt={id}'
WINDCENTRALE_DATA = 'https://zep-api.windcentrale.nl/production/{id}?molenid={id}&method=getProductie'

WINDMILLS = (
    (31, 'Het Rode Hert'),
    (141, 'De Vier Winden'),
)


class WindcentralSource(Source):
    name = "windcentale"

    def __init__(self, source_id, mills):
        super().__init__(source_id)
        self.mills = list(mills)

    @classmethod
    async def get_mill_info(cls, session, mill, hub):
        while True:
            try:
                async with session.get(URL(WINDCENTRALE_LIVE.format(id=mill), encoded=True)) as response:
                    if response.status != 200:
                        break

                    async for line in response.content:
                        line = line.decode('utf8').strip().split(',')
                        await hub.handle_incoming(cls, {
                            'name': 'windmill',
                            'data': {
                                'id': mill,
                                'wind': line[0],
                                'mill_total': int(line[1]),
                                'per_share': int(line[2]),
                                'performance': int(line[3]),
                            },
                        })
            except (ServerDisconnectedError, TimeoutError, IndexError):
                await asyncio.sleep(5)

    async def get_task(self, hub):

        async with aiohttp.ClientSession() as session:
            fetchers = [asyncio.ensure_future(self.get_mill_info(session, mill, hub))
                        for mill, _ in self.mills]

            await asyncio.wait(fetchers)


def from_config(source_id, config, hub):
    mill_ids = dict([(v, k,) for k, v in WINDMILLS])
    mills = [i.split(':') for i in config.get('mills').split(',')]
    mills = ((mill_ids[k], int(v)) for (k, v) in mills)

    return WindcentralSource(source_id, mills)
