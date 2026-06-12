"""Runtime configuration for the job market copilot."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variables are read from `.env` in the project root by default.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    data_dir: Path = Field(default_factory=lambda: Path("data"))
    raw_dir: Path = Field(default_factory=lambda: Path("data/raw"))
    artifacts_dir: Path = Field(default_factory=lambda: Path("artifacts"))

    user_agent: str = "ahmad-ai-job-market-copilot/1.0"
    request_timeout_seconds: float = 30.0
    request_retries: int = 3

    max_jobs_per_source: int = 500
    max_jobs_for_enrichment: int = 12

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "granite4.1:3b"
    ollama_quality_model: str = "granite4.1:8b"
    ollama_temperature: float = 0.0

    enable_hf_fallback: bool = False
    hf_token: str | None = None
    hf_model: str = "Qwen/Qwen2.5-7B-Instruct"

    ai_keyword_threshold: int = 2

    def resolve_path(self, relative_path: Path) -> Path:
        """Resolve relative paths from the project root."""
        if relative_path.is_absolute():
            return relative_path
        return (self.project_root / relative_path).resolve()

    @property
    def resolved_data_dir(self) -> Path:
        return self.resolve_path(self.data_dir)

    @property
    def resolved_raw_dir(self) -> Path:
        return self.resolve_path(self.raw_dir)

    @property
    def resolved_artifacts_dir(self) -> Path:
        return self.resolve_path(self.artifacts_dir)

    def ensure_directories(self) -> None:
        """Create directories required by the pipeline."""
        self.resolved_data_dir.mkdir(parents=True, exist_ok=True)
        self.resolved_raw_dir.mkdir(parents=True, exist_ok=True)
        self.resolved_artifacts_dir.mkdir(parents=True, exist_ok=True)
        (self.resolved_artifacts_dir / "charts").mkdir(parents=True, exist_ok=True)
        (self.resolved_artifacts_dir / "reports").mkdir(parents=True, exist_ok=True)
        (self.resolved_artifacts_dir / "tables").mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Create a settings instance."""
    return Settings()
