"""Environment-driven configuration for MK-Path.

Rules (spec sections 4-5):
- Credentials only via environment / .env file, never hardcoded.
- .env is gitignored; values are never exposed to any frontend.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# backend/app/config.py -> project root is two levels up
ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=ROOT_DIR / ".env")


class Settings:
    """Application settings resolved from environment variables."""

    # MongoDB Atlas
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "mk_path")

    # LLM (used in later phases; placeholder here, never hardcoded)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-latest")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    # Server
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # --- Storage roots (spec section 3: everything on the project drive) ---
    ROOT_DIR: Path = ROOT_DIR
    DATA_DIR: Path = ROOT_DIR / "data"
    DATASETS_DIR: Path = ROOT_DIR / "datasets"
    MODELS_DIR: Path = ROOT_DIR / "models"
    ARTIFACTS_DIR: Path = ROOT_DIR / "artifacts"
    LOGS_DIR: Path = ROOT_DIR / "logs"
    REPORTS_DIR: Path = ROOT_DIR / "reports"
    TEMP_DIR: Path = ROOT_DIR / "temp"
    DOCS_DIR: Path = ROOT_DIR / "docs"

    # --- Ingestion limits (security section of Phase 4 spec) ---
    MAX_UPLOAD_MB: int = int(os.getenv("MKPATH_MAX_UPLOAD_MB", "50"))
    MAX_ZIP_ENTRIES: int = int(os.getenv("MKPATH_MAX_ZIP_ENTRIES", "200"))
    MAX_ZIP_UNCOMPRESSED_MB: int = int(os.getenv("MKPATH_MAX_ZIP_UNCOMPRESSED_MB", "200"))
    MAX_ZIP_RATIO: int = int(os.getenv("MKPATH_MAX_ZIP_RATIO", "100"))
    MAX_ZIP_DEPTH: int = int(os.getenv("MKPATH_MAX_ZIP_DEPTH", "1"))
    MAX_PREVIEW_ROWS: int = int(os.getenv("MKPATH_MAX_PREVIEW_ROWS", "100"))

    # --- Semantic knowledge layer (Phase 6) ---
    # When context confidence drops below this threshold the semantic workflow
    # is INTERRUPTED and a clarification question is created for the user.
    SEMANTIC_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("MKPATH_SEMANTIC_CONFIDENCE_THRESHOLD", "0.7")
    )
    # LLM interpretation is optional: without a key the layer runs
    # deterministic-only and never invents business meaning.
    SEMANTIC_MAX_LLM_COLUMNS: int = int(os.getenv("MKPATH_SEMANTIC_MAX_LLM_COLUMNS", "3"))

    def ensure_directories(self) -> None:
        """Materialize the storage layout (idempotent)."""
        for d in (
            self.DATA_DIR,
            self.DATASETS_DIR,
            self.MODELS_DIR,
            self.ARTIFACTS_DIR,
            self.LOGS_DIR,
            self.REPORTS_DIR,
            self.TEMP_DIR,
            self.DOCS_DIR,
        ):
            d.mkdir(parents=True, exist_ok=True)

    @property
    def mongo_configured(self) -> bool:
        return bool(self.MONGODB_URI)


settings = Settings()
settings.ensure_directories()
