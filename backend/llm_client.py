"""Thin OpenAI-compatible chat-completions client over plain REST (requests).

Deliberately SDK-free: the openai SDK's transport stack failed to connect
inside the Streamlit Community Cloud sandbox while plain requests/urllib3
worked from the same container (verified by in-app network probes). A chat
completion is a single POST — battle-tested urllib3 is the safer transport,
and raw responses give real error messages instead of a generic
"Connection error.".
"""
from __future__ import annotations

import time

from backend.config import Settings

_DEFAULT_BASE = "https://api.openai.com/v1"
_CONNECT_TIMEOUT = 10
_READ_TIMEOUT = 90


class LLMError(RuntimeError):
    """Raised for any live-LLM failure; message is safe to show in chat."""


class LLMClient:
    def __init__(self, settings: Settings):
        if not settings.llm_configured:
            raise LLMError("No API key configured — set OPENAI_API_KEY in .env "
                           "or Streamlit secrets. (Without one, the built-in "
                           "engine answers automatically.)")
        self._api_key = settings.api_key
        self._base_url = (settings.base_url or _DEFAULT_BASE).rstrip("/")
        self._model = settings.model

    def complete(self, messages: list[dict], json_mode: bool = True) -> str:
        """One chat completion; returns the assistant message content."""
        import requests

        payload: dict = {"model": self._model, "messages": messages}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_exc: Exception | None = None
        for attempt in (1, 2):  # one retry on transport-level failures
            try:
                resp = requests.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}",
                             "Content-Type": "application/json"},
                    timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT))
                break
            except requests.RequestException as exc:
                last_exc = exc
                if attempt == 1:
                    time.sleep(1)
        else:
            raise LLMError(f"LLM request failed after retry: "
                           f"{type(last_exc).__name__}: {last_exc}")

        if resp.status_code != 200:
            try:
                detail = resp.json().get("error", {}).get("message", "")[:300]
            except Exception:
                detail = resp.text[:300]
            raise LLMError(f"LLM request failed (HTTP {resp.status_code}): "
                           f"{detail or 'no error detail'}")

        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            raise LLMError(f"Unexpected API response shape: {exc}") from exc
        if not content:
            raise LLMError("The model returned an empty response.")
        return content
