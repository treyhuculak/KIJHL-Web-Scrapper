"""Application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import store
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the database pool, without waking anything up.

    Deliberately not a connection. Neon's free tier bills the hours its compute
    spends awake, and a container that connects on boot spends them on every
    cold start — including the ones that only serve the games page, which reads
    the feed live and asks the database nothing. The first query is what wakes
    it. See `store.open_pool`. Without a DATABASE_URL this does nothing at all.
    """
    await store.open_pool()
    try:
        yield
    finally:
        await store.close_pool()


app = FastAPI(title="ZebraZone", lifespan=lifespan)
app.include_router(router)
