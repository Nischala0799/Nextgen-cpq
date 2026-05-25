"""
main.py
-------
NextGen CPQ – FastAPI Application Entry Point (Week 4)

Run with:
    uvicorn api.main:app --reload

Swagger UI available at:
    http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI

from api.routers.quotes import router as quotes_router

app = FastAPI(
    title="NextGen CPQ API",
    description="Modular CPQ quoting system — configure, price, and generate quotes.",
    version="0.1.0",
)

app.include_router(quotes_router)


@app.get("/health", tags=["health"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "nextgen-cpq-api"}