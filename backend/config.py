"""Configuration loading.

Order of precedence: real environment variables (Streamlit Cloud injects
secrets there too via st.secrets, which we read without importing streamlit —
see note below) → .env file → defaults.

To stay Streamlit-free in the backend, we read Streamlit Cloud secrets from
the standard secrets.toml locations directly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load ONLY the project's own .env (never walk up parent directories);
# harmless no-op when absent, e.g. on Streamlit Cloud where secrets are used.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
try:
    load_dotenv(_PROJECT_ROOT / ".env")
except OSError:
    pass

_SECRET_PATHS = [
    _PROJECT_ROOT / ".streamlit" / "secrets.toml",
    Path.home() / ".streamlit" / "secrets.toml",
]


def _load_streamlit_secrets() -> dict:
    try:
        import tomllib
    except ModuleNotFoundError:  # Python < 3.11
        return {}
    for path in _SECRET_PATHS:
        try:
            if path.exists():
                with open(path, "rb") as fh:
                    return tomllib.load(fh)
        except Exception:
            continue
    return {}


_secrets = _load_streamlit_secrets()


def _from_st_secrets(key: str) -> str:
    """Last-resort lookup through st.secrets — the canonical (and on Streamlit
    Community Cloud, the only reliable) way dashboard secrets are delivered.
    Imported lazily so the backend stays usable without Streamlit installed."""
    try:
        import streamlit as st
        return str(st.secrets.get(key, "") or "")
    except Exception:
        return ""


def _get(key: str, default: str = "") -> str:
    return (os.environ.get(key)
            or str(_secrets.get(key, "") or "")
            or _from_st_secrets(key)
            or default).strip()


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str          # empty → official OpenAI endpoint
    model: str

    @property
    def llm_configured(self) -> bool:
        return bool(self.api_key)


_PLACEHOLDERS = {"sk-...", "...", "your-key-here", "changeme"}


def get_settings() -> Settings:
    api_key = _get("OPENAI_API_KEY")
    if api_key.lower() in _PLACEHOLDERS or len(api_key) < 12:
        api_key = ""  # template placeholder ≠ configured key
    return Settings(
        api_key=api_key,
        base_url=_get("OPENAI_BASE_URL"),
        model=_get("ILUMOS_MODEL", "gpt-5.6-luna"),
    )
