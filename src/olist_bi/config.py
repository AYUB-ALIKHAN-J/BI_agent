"""Central configuration. Everything is overridable via environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _project_root() -> Path:
    # src/olist_bi/config.py -> project root is three levels up
    return Path(__file__).resolve().parents[2]


try:
    from dotenv import load_dotenv

    load_dotenv(_project_root() / ".env")
except ImportError:
    pass


def _default_provider() -> str:
    explicit = os.getenv("LLM_PROVIDER")
    if explicit:
        return explicit.lower()
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    return "ollama"


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("OLIST_DATA_DIR", _project_root() / "data/raw"))
    )
    warehouse_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("OLIST_WAREHOUSE_PATH", _project_root() / "warehouse/olist.duckdb")
        )
    )
    log_level: str = field(default_factory=lambda: os.getenv("OLIST_LOG_LEVEL", "INFO"))
    llm_provider: str = field(default_factory=_default_provider)
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.1"))
    groq_api_key: str | None = field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    groq_model: str = field(
        default_factory=lambda: os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    )


def get_settings() -> Settings:
    return Settings()
