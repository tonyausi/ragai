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

app = FastAPI(title="RAG AI API", version="1.0.0")
# add CORS middleware to allow all origins, methods, and headers for now
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include the router with optional prefix
# Include the router with optional prefix
app.include_router(ragflowtasks.router, prefix="/api")


# Add Redis lifecycle events
@app.on_event("startup")
async def startup():
    await redis_client.connect()  # Initialize Redis connection


@app.on_event("shutdown")
async def shutdown():
    await redis_client.disconnect()  # Close Redis connection
