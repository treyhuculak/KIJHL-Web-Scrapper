"""Application entry point."""

from fastapi import FastAPI

from .routes import router

app = FastAPI(title="ZebraZone")
app.include_router(router)
