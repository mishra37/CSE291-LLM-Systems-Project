"""Baseline schedulers: FIFO with a fixed concurrency limit K.

Every scheduler exposes the same interface to the runner:
    async with sched.task(task) as ticket:   # task-level admission
        res = await sched.request(req, ticket)  # one model call; req = {"prompt", "max_tokens"}
and fills req["t_enqueue"] / req["t_dispatch"] so the runner can compute queueing time.
"""
import asyncio
import contextlib


class FifoRequestScheduler:
    """One global FIFO queue of model requests; at most K are in flight.

    A multi-step task holds nothing while it waits on a tool, so its next step joins the back
    of the queue and may land on a different server slot, whose KV cache no longer holds this
    task's context -> the prompt is recomputed.
    """
    name = "fifo_request"

    def __init__(self, k, client, clock):
        self.k, self.client, self.clock = k, client, clock
        self.queue = asyncio.Queue()
        self.workers = []

    async def start(self):
        self.workers = [asyncio.ensure_future(self._worker()) for _ in range(self.k)]

    async def stop(self):
        for w in self.workers:
            w.cancel()

    @contextlib.asynccontextmanager
    async def task(self, task):
        yield None

    async def request(self, req, ticket=None):
        fut = asyncio.get_event_loop().create_future()
        req["t_enqueue"] = self.clock()
        await self.queue.put((req, fut))
        return await fut

    async def _worker(self):
        while True:
            req, fut = await self.queue.get()
            req["t_dispatch"] = self.clock()
            fut.set_result(await self.client.complete(req["prompt"], req["max_tokens"], clock=self.clock, **req.get("generation", {})))


class FifoTaskScheduler:
    """Admit at most K tasks at a time, in arrival order.

    An admitted task keeps its admission and is pinned to one server slot for all of its
    steps, so its KV cache is retained across tool calls -- but that slot sits idle during
    every tool delay.
    """
    name = "fifo_task"

    def __init__(self, k, client, clock):
        self.k, self.client, self.clock = k, client, clock
        self.free_slots = asyncio.Queue()  # asyncio.Queue serves waiting getters in FIFO order

    async def start(self):
        for slot in range(self.k):
            self.free_slots.put_nowait(slot)

    async def stop(self):
        pass

    @contextlib.asynccontextmanager
    async def task(self, task):
        slot = await self.free_slots.get()
        try:
            yield slot
        finally:
            self.free_slots.put_nowait(slot)

    async def request(self, req, ticket=None):
        req["t_enqueue"] = req["t_dispatch"] = self.clock()
        return await self.client.complete(req["prompt"], req["max_tokens"], slot=ticket, clock=self.clock, **req.get("generation", {}))


SCHEDULERS = {s.name: s for s in (FifoRequestScheduler, FifoTaskScheduler)}
