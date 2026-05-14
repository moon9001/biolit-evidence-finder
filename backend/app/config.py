"""Configuration loaded from environment variables / .env file."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env if present (best-effort).
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _get(name: str, default: str = "") -> str:
    val = os.getenv(name, default)
    return val.strip() if isinstance(val, str) else val


class Settings:
    """Lightweight settings container, intentionally not a pydantic model so we
    can hot-update values from the /api/settings endpoint at runtime."""

    def __init__(self) -> None:
        # LLM
        self.llm_api_base_url: str = _get("LLM_API_BASE_URL")
        self.llm_api_key: str = _get("LLM_API_KEY")
        self.llm_model: str = _get("LLM_MODEL", "deepseek-v4-flash")

        # Embedding
        self.embedding_api_base_url: str = _get("EMBEDDING_API_BASE_URL")
        self.embedding_api_key: str = _get("EMBEDDING_API_KEY")
        self.embedding_model: str = _get("EMBEDDING_MODEL", "qwen3-embedding:8b")

        # OCR (DeepSeek-OCR optional)
        self.deepseek_ocr_url: str = _get("DEEPSEEK_OCR_URL")
        self.deepseek_ocr_key: str = _get("DEEPSEEK_OCR_KEY")

        # Storage
        data_dir_env = _get("DATA_DIR", str(BACKEND_DIR.parent / "data"))
        self.data_dir: Path = Path(data_dir_env).expanduser().resolve()
        self.uploads_dir: Path = self.data_dir / "uploads"
        self.page_images_dir: Path = self.data_dir / "page_images"

        db_path_env = _get("DB_PATH", str(self.data_dir / "app.db"))
        self.db_path: Path = Path(db_path_env).expanduser().resolve()

        for p in (self.data_dir, self.uploads_dir, self.page_images_dir):
            p.mkdir(parents=True, exist_ok=True)

        # Page rendering
        try:
            self.page_image_dpi: int = int(_get("PAGE_IMAGE_DPI", "144"))
        except ValueError:
            self.page_image_dpi = 144

        # Chunking
        try:
            self.chunk_tokens: int = int(_get("CHUNK_TOKENS", "480"))
        except ValueError:
            self.chunk_tokens = 480
        try:
            self.chunk_overlap: int = int(_get("CHUNK_OVERLAP", "60"))
        except ValueError:
            self.chunk_overlap = 60

    # ------------------------------------------------------------------ #
    # Mutators used by the settings router
    # ------------------------------------------------------------------ #
    def update_llm(self, base_url: str, api_key: str, model: str) -> None:
        self.llm_api_base_url = base_url.strip()
        self.llm_api_key = api_key.strip()
        self.llm_model = model.strip() or self.llm_model

    def update_embedding(self, base_url: str, api_key: str, model: str) -> None:
        self.embedding_api_base_url = base_url.strip()
        self.embedding_api_key = api_key.strip()
        self.embedding_model = model.strip() or self.embedding_model

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_base_url and self.llm_api_key)

    @property
    def embedding_enabled(self) -> bool:
        return bool(self.embedding_api_base_url and self.embedding_api_key)


settings = Settings()
