"""FastAPI application."""
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routers import agent, telemetry, vehicles
from app.ml.model_loader import warmup_models


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Load ML models once at startup.
    warmup_models()
    yield

app = FastAPI(
    title="FixSight",
    description="Predictive vehicle maintenance system",
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "ok"}, status_code=200)


# Register API routers
app.include_router(vehicles.router, prefix="/api")
app.include_router(telemetry.router, prefix="/api")
app.include_router(agent.router, prefix="/api")


if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000)
