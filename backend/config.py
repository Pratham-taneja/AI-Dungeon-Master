"""
config.py — Centralised app configuration via pydantic-settings.
All values are read from environment variables / .env file.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # APP
    app_name: str = "AI Dungeon Master API"
    debug: bool = False

    # AI Providers
    nvidia_api_key: str = ""

    # LLM 
    # Models (using NVIDIA NIM free tier models)
    llm_model: str = "meta/llama-3.1-8b-instruct"
    llm_summariser_model: str = "meta/llama-3.1-8b-instruct"
    llm_temperature: float = 0.85
    llm_max_tokens: int = 1024
    llm_streaming_timeout: int = 60

    # Database
    database_url: str = "postgresql+asyncpg://rpg_user:rpg_pass@localhost:5432/rpg_db"
    database_sync_url: str = "postgresql://rpg_user:rpg_pass@localhost:5432/rpg_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # ChromaDB
    chroma_persist_path: str = "./chroma_data"
    chroma_collection_prefix: str = "rpg_npc_"

    # App 
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Game Settings
    max_history_turns: int = 20
    npc_memory_top_k: int = 5
    world_event_interval_seconds: int = 300

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
