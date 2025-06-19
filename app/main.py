import os
from app.config.logging_config import setup_logging
from app.routers import ragflowtasks
from app.utils.redis_client import redis_client  # Import the Redis client

# Get the absolute path to the logging configuration file
base_dir = os.path.dirname(os.path.abspath(__file__))
app_logging_config_path = os.path.join(base_dir, "config/logging_app.yaml")
setup_logging(app_logging_config_path)  # apply YAML config to the logging module

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.connect()  # Initialize Redis connection
    try:
        yield
    finally:
        await redis_client.disconnect()  # Close Redis connection


app = FastAPI(title="RAG AI API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(ragflowtasks.router, prefix="/api")
