# app/config/settings.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_TITLE: str = "RAG AI API"
    REDIS_URL: str
    EXPOSED_PORT: int
    RAGFLOW_BASE_URL: str
    RAGFLOW_API_KEY: str
    RAGFLOW_STREAM: str
    TENDER_KNOWLEDGE_BASE: str
    TENDER_QUESTION_HEADER: str
    VENDOR_QUESTION_HEADER: str
    PUBLIC_LLM_MODEL: str
    NULL_RAGFLOW_ANSWER: str
    PROCESSED_FILE_DIR: str
    Q_COLUMN_WIDTH: int
    A_COLUMN_WIDTH: int
    REF_COLUMN_WIDTH: int
    GEMINI_API_KEY: str

    class Config:
        env_file = ".env"


settings = Settings()
