"""Application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg_pool import PoolTimeout

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


@app.exception_handler(PoolTimeout)
async def no_answer(request: Request, error: Exception) -> JSONResponse:
    """A database that never picked up. Handled here rather than in the routes
    because it can come out of any query, and it means the same thing whichever
    one it was: not a broken request, a database to ask again in a minute."""
    return JSONResponse(
        status_code=503,
        content={"detail": "The database did not answer in time. Try again in a moment."},
    )
