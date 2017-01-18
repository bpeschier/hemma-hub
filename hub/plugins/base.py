class Plugin:
    label = None
    id = None

    def __init__(self, plugin_id, hub):
        self.id = plugin_id
        self.hub = hub

    async def reply(self, target, target_key, content):
        await self.hub.reply(target, target_key, {
            'label': self.label,
            'data': content,
        })

    async def broadcast(self, content):
        await self.hub.broadcast({
            'label': self.label,
            'data': content,
        })

    async def on_source_connect(self, source):
        pass

    async def on_source_message(self, source, message):
        raise NotImplementedError

    async def on_client_connect(self, client, client_key):
        pass

    async def on_client_request(self, client, client_key, request):
        raise NotImplementedError
