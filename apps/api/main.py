"""
main.py
-------
NextGen CPQ – FastAPI Application Entry Point (Week 4)

Run with:
    uvicorn api.main:app --reload

Swagger UI available at:
    http://127.0.0.1:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.database import init_db
from api.routers.quotes import router as quotes_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="NextGen CPQ API",
    description="Modular CPQ quoting system — configure, price, and generate quotes.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(quotes_router)


@app.get("/health", tags=["health"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "nextgen-cpq-api"}