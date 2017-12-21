import asyncio
import flynn

import websockets

from .base import Source


class BridgeSource(Source):
    current_id = 0
    current_id_lock = asyncio.Lock()

    events = None
    results = None

    def __init__(self, source_id, target):
        super().__init__(source_id)
        self.target = target
        self.events = {}
        self.results = {}

    async def get_task(self, hub):
        bridge = await websockets.connect(self.target)
        while True:
            producer_task = asyncio.ensure_future(bridge.recv())
            listener_task = asyncio.ensure_future(self.outgoing.get())

            done, pending = await asyncio.wait(
                [listener_task, producer_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            if listener_task in done:
                message = listener_task.result()
                await bridge.send(flynn.dumps(message))
            else:
                listener_task.cancel()

            if producer_task in done:
                message = flynn.loads(producer_task.result())

                if 'id' in message:  # reply
                    await self.set_result(message['id'], message)
                else:
                    await hub.handle_incoming(self, message)
            else:
                producer_task.cancel()

    async def get_command_id(self):
        async with self.current_id_lock:
            self.current_id = (self.current_id + 1) % (1024 * 1024)
            cmd_id = self.current_id
        return cmd_id

    async def get_response(self, cmd_id):
        event = self.events.setdefault(cmd_id, asyncio.Event())
        try:
            await asyncio.wait_for(event.wait(), 5.0)
        finally:
            event.clear()
            del self.events[cmd_id]
            return self.results.pop(cmd_id, None)

    async def set_result(self, command_id, data):
        self.results[command_id] = data['data']
        event = self.events.setdefault(command_id, asyncio.Event())
        event.set()

    async def command(self, target_address, command, **kwargs):
        command_id = await self.get_command_id()
        await self.outgoing.put({
            "address": target_address,
            "id": command_id,
            "name": command,
            "args": kwargs,
        })

    async def request(self, target_address, command, **kwargs):
        command_id = await self.get_command_id()
        await self.outgoing.put({
            "address": target_address,
            "id": command_id,
            "name": command,
            "args": kwargs,
        })
        return await self.get_response(command_id)


def from_config(source_id, config, hub):
    return BridgeSource(source_id, config.get('url', 'ws://127.0.0.1:9876'))
