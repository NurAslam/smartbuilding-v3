from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging

# Simulation routers
from app.simulation.routers.info import router as sim_info
from app.simulation.routers.analyze import router as sim_analyze
from app.simulation.routers.predict import router as sim_predict
from app.simulation.routers.models import router as sim_models

# Realtime routers & lifecycle
from app.realtime.routers.sensor import router as sensor_router
from app.realtime.db import init_table
from app.realtime.scheduler import scheduler


setup_logging()
app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # sesuaikan di production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prefix sama seperti rancangan gabungan sebelumnya
app.include_router(sim_info,    prefix="/simulation")
app.include_router(sim_analyze, prefix="/simulation")
app.include_router(sim_predict, prefix="/simulation")
app.include_router(sim_models,  prefix="/simulation")

app.include_router(sensor_router, prefix="/realtime")


@app.get("/status")
def status():
    return {
        "combined": "ok",
        "version": settings.APP_VERSION,
        "apps": {
            "simulation": {"base_path": "/simulation"},
            "realtime": {"base_path": "/realtime"},
        }
    }


@app.on_event("startup")
def on_startup():
    init_table()
    if settings.ENABLE_SCHEDULER and not scheduler.running:
        scheduler.start()
