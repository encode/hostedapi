from starlette.datastructures import URL
from contextlib import asynccontextmanager
import asyncio
import asyncio_redis


class Broadcast:
    def __init__(self, url: URL):
        self._url = url
        self._groups = {}

    async def connect(self):
        host, port = self._url.hostname, self._url.port
        pub_conn = await asyncio_redis.Connection.create(host, port)
        sub_conn = await asyncio_redis.Connection.create(host, port)
        self._pub = pub_conn
        self._sub = await sub_conn.start_subscribe()
        self._listener_task = asyncio.create_task(self._listener())

    async def disconnect(self):
        self._listener_task.cancel()
        self._sub.close()
        self._pub.close()

    async def _listener(self):
        while True:
            message = await self._sub.next_published()
            for group in list(self._groups[message.channel]):
                await group.put(message.value)

    async def publish(self, group, message):
        await self._pub.publish(group, message)

    @asynccontextmanager
    async def subscribe(self, group):
        queue = asyncio.Queue()

        if not self._groups.get(group):
            await self._sub.subscribe([group])
            self._groups[group] = set([queue])
        else:
            self._groups[group].add(queue)

        yield queue

        self._groups[group].remove(queue)
        if not self._groups.get(group):
            del self._groups[group]
            await self._sub.unsubscribe([group])
