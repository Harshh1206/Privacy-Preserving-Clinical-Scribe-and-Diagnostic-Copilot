from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    default_physician_id: str = "dr-001"
    default_physician_name: str = "Dr. Sarah Chen"
    database_url: str | None = None
    groq_api_key: str | None = None
    team_a_max_audio_bytes: int = 25 * 1024 * 1024
    team_a_transcription_model: str = "whisper-large-v3-turbo"
    team_a_diarization_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: Literal["qwen3:8b"] = "qwen3:8b"
    ollama_connect_timeout_seconds: float = 10.0
    ollama_request_timeout_seconds: float = 300.0
    ollama_parallel_agents: bool = False
    ollama_num_ctx: int = 32768
    ollama_num_predict_subjective_objective: int = 2200
    ollama_num_predict_assessment_plan: int = 2400
    ollama_temperature: float = 0.0
    ollama_keep_alive: str = "30m"
    ollama_pool_max_connections: int = 4
    ollama_pool_max_keepalive_connections: int = 2
    huggingface_token: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
