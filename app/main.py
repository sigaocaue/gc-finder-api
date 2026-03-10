from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title="GC Finder API",
    description="API REST para localização de Grupos de Crescimento (GCs)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro dos routers
from app.routers.auth import router as auth_router
from app.routers.gc_medias import router as gc_medias_router
from app.routers.gc_meetings import router as gc_meetings_router
from app.routers.gcs import router as gcs_router
from app.routers.health import router as health_router
from app.routers.leaders import router as leaders_router
from app.routers.public import router as public_router
from app.routers.users import router as users_router

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(leaders_router)
app.include_router(gcs_router)
app.include_router(gc_meetings_router)
app.include_router(gc_medias_router)
app.include_router(public_router)
