"""FastAPI application."""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import agent, fleet, service, simulation, telemetry, vehicles
from app.ml.model_loader import warmup_models
from app.simulation.engine import simulation_engine

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Load ML models once at startup.
    warmup_models()
    yield
    if simulation_engine.running:
        await simulation_engine.stop()


app = FastAPI(
    title="FixSight",
    description="Predictive vehicle maintenance system",
    lifespan=lifespan,
)

cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://localhost:8080",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "ok"}, status_code=200)


# Register API routers
app.include_router(vehicles.router, prefix="/api")
app.include_router(telemetry.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(service.router, prefix="/api")
app.include_router(fleet.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")


if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000)
