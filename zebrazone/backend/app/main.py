"""Application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from . import store
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the database while the app is still starting.

    Neon suspends an idle free database, and waking it costs the better part of
    a second. Spending it here means it overlaps the rest of the boot and the
    browser fetching its JavaScript, instead of being charged to whoever asks
    the first question. Without a DATABASE_URL this does nothing at all.
    """
    await store.open_pool()
    try:
        yield
    finally:
        await store.close_pool()


app = FastAPI(title="ZebraZone", lifespan=lifespan)
app.include_router(router)
