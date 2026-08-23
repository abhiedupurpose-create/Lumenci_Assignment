"""Thin wrapper around the OpenAI-compatible chat completions API.

Isolates SDK details and turns transport failures into one exception type the
engine (and ultimately the chat UI) can handle gracefully.
"""
from __future__ import annotations

from backend.config import Settings


class LLMError(RuntimeError):
    """Raised for any live-LLM failure; message is safe to show in chat."""


class LLMClient:
    def __init__(self, settings: Settings):
        if not settings.llm_configured:
            raise LLMError("No API key configured — set OPENAI_API_KEY in .env "
                           "or Streamlit secrets. (Without one, the built-in "
                           "engine answers automatically.)")
        from openai import OpenAI
        # Bounded waiting: Streamlit runs single-threaded, so the SDK defaults
        # (600s read timeout x 2 retries) would freeze the app behind a spinner
        # for many minutes on a hung endpoint.
        kwargs = {"api_key": settings.api_key, "timeout": 60.0, "max_retries": 1}
        if settings.base_url:
            kwargs["base_url"] = settings.base_url
        # Harden the transport for hosted containers (Streamlit Community
        # Cloud): force IPv4, add connect retries, ignore env proxies. The
        # openai v3 SDK uses httpx2 (httpx's successor) — build its client.
        try:
            import httpx2
            kwargs["http_client"] = httpx2.Client(
                transport=httpx2.HTTPTransport(local_address="0.0.0.0",
                                               retries=2),
                timeout=60.0, trust_env=False)
        except Exception:
            pass  # fall back to the SDK's default client
        self._client = OpenAI(**kwargs)
        self._model = settings.model

    def complete(self, messages: list[dict], json_mode: bool = True) -> str:
        """One chat completion; returns the assistant message content."""
        try:
            kwargs = {"model": self._model, "messages": messages}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = self._client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content
            if not content:
                raise LLMError("The model returned an empty response.")
            return content
        except LLMError:
            raise
        except Exception as exc:
            # Auth, quota, network, bad model name, gateways without json_mode…
            raise LLMError(f"LLM request failed: {exc}") from exc
