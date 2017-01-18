import asyncio


class Source:
    outgoing = asyncio.Queue()
    id = None

    def __init__(self, source_id):
        self.id = source_id

    def get_task(self, hub):
        raise NotImplementedError
