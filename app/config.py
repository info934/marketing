from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
AVATAR_DATA_PATH = Path(os.getenv("AVATAR_DATA_PATH", BASE_DIR / "data" / "avatars.json"))
COMPANY_DATA_PATH = Path(os.getenv("COMPANY_DATA_PATH", BASE_DIR / "data" / "companies.json"))
CREATIVE_MEMORY_DB_PATH = Path(
    os.getenv("CREATIVE_MEMORY_DB_PATH", BASE_DIR / "data" / "creative_memory.sqlite")
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_SEEDANCE_MODEL = os.getenv(
    "OPENROUTER_SEEDANCE_MODEL", "bytedance/seedance-2.0-fast"
)
OPENROUTER_PROMPT_MODEL = os.getenv("OPENROUTER_PROMPT_MODEL", "openai/gpt-5.4-mini")
OPENROUTER_UGC_SCENARIO_MODEL = os.getenv(
    "OPENROUTER_UGC_SCENARIO_MODEL", OPENROUTER_PROMPT_MODEL
)
OPENROUTER_STATIC_PROMPT_MODEL = os.getenv(
    "OPENROUTER_STATIC_PROMPT_MODEL", OPENROUTER_PROMPT_MODEL
)
OPENROUTER_PROMPT_FALLBACK_MODELS = [
    item.strip()
    for item in os.getenv("OPENROUTER_PROMPT_FALLBACK_MODELS", "").split(",")
    if item.strip()
]
REQUIRE_PROMPT_MODEL_FOR_STATIC_CREATIVES = (
    os.getenv("REQUIRE_PROMPT_MODEL_FOR_STATIC_CREATIVES", "true").lower()
    in {"1", "true", "yes", "on"}
)
OPENROUTER_IMAGE_MODEL = os.getenv(
    "OPENROUTER_IMAGE_MODEL", "google/gemini-3-pro-image-preview"
)
OPENROUTER_VISION_MODEL = os.getenv("OPENROUTER_VISION_MODEL", OPENROUTER_IMAGE_MODEL)
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

EMBEDDING_USE_OPENROUTER_API_KEY = (
    os.getenv("EMBEDDING_USE_OPENROUTER_API_KEY", "false").lower()
    in {"1", "true", "yes", "on"}
)
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "") or (
    OPENROUTER_API_KEY if EMBEDDING_USE_OPENROUTER_API_KEY else ""
)
EMBEDDING_BASE_URL = os.getenv(
    "EMBEDDING_BASE_URL",
    OPENROUTER_BASE_URL if EMBEDDING_USE_OPENROUTER_API_KEY else "https://api.openai.com/v1",
)
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "openai/text-embedding-3-small" if EMBEDDING_USE_OPENROUTER_API_KEY else "text-embedding-3-small",
)
EMBEDDING_TIMEOUT_SECONDS = int(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "45"))

DEFAULT_MARKET = "UK"
DEFAULT_LANGUAGE = "en"
DEFAULT_PLATFORM = "meta"
DEFAULT_VIDEO_LENGTH = 15
