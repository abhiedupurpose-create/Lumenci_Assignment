"""Facade the frontend talks to. Owns engine dispatch (live LLM vs demo),
error fallback, and metrics recording — so the UI layer contains no logic
beyond rendering and wiring.
"""
from __future__ import annotations

from backend.chart_store import ChartStore
from backend.config import Settings, get_settings
from backend.demo_engine import handle_user_message_demo
from backend.llm_client import LLMClient, LLMError
from backend.models import ChatMessage, DocFile, EngineResponse
from backend.refinement_engine import (SessionMetrics, accept_suggestion,
                                       check_decision_intent,
                                       check_diff_intent, check_restore_intent,
                                       handle_user_message,
                                       latest_pending_suggestion,
                                       perform_diff, perform_restore,
                                       reject_suggestion)


def engine_status(demo_mode: bool, settings: Settings | None = None) -> tuple[str, str]:
    """(badge_label, detail) for the sidebar status pill."""
    settings = settings or get_settings()
    if demo_mode:
        return ("🎭 Demo mode", "Scripted engine — no API calls. Grounded against "
                                "your uploaded documents.")
    if settings.llm_configured:
        endpoint = settings.base_url or "api.openai.com"
        return (f"⚡ Live · {settings.model}", f"Endpoint: {endpoint}")
    return ("⚠️ No API key", "Set OPENAI_API_KEY in .env / Streamlit secrets, "
                             "or switch on Demo mode.")


def respond(user_message: str, *, demo_mode: bool, system_prompt: str,
            store: ChartStore, docs: list[DocFile],
            history: list[ChatMessage], metrics: SessionMetrics,
            settings: Settings | None = None) -> EngineResponse:
    """Route one analyst message to the right engine; never raises."""
    settings = settings or get_settings()

    # Version intents first: "restore to v2" must win over the undo intent,
    # and "what changed from v1" is answered deterministically from history.
    restore_to = check_restore_intent(user_message)
    if restore_to is not None:
        return perform_restore(store, restore_to)
    diff = check_diff_intent(user_message, store)
    if diff is not None:
        return perform_diff(store, *diff)

    # Typed decisions ("accept", "reject that") resolve against the most
    # recent pending suggestion — accept/reject works through conversation,
    # not only through the card buttons.
    decision = check_decision_intent(user_message)
    if decision:
        sug = latest_pending_suggestion(history)
        if sug is None:
            return EngineResponse(
                reply="There's no pending suggestion to act on right now — ask me "
                      "for a refinement first.",
                handled_intent=decision)
        text = (accept_suggestion(store, sug, metrics) if decision == "accept"
                else reject_suggestion(sug, metrics))
        return EngineResponse(reply=text, handled_intent=decision)

    if demo_mode or not settings.llm_configured:
        resp = handle_user_message_demo(user_message, store=store, docs=docs,
                                        history=history)
        if not demo_mode:
            # Key missing but demo toggle off: label the fallback honestly
            # instead of passing scripted output off as the live model.
            resp.reply = ("🎭 *No API key configured — answering in demo mode.*\n\n"
                          + resp.reply)
            resp.handled_intent = resp.handled_intent or "demo_fallback"
    else:
        try:
            client = LLMClient(settings)
            resp = handle_user_message(user_message, client=client,
                                       system_prompt=system_prompt, store=store,
                                       docs=docs, history=history)
        except (LLMError, ValueError) as exc:
            # ValueError covers prompt-template mismatches — respond() promises
            # the UI it never raises, whatever breaks underneath.
            metrics.llm_failures += 1
            return EngineResponse(
                reply=(f"⚠️ {exc}\n\nYou can retry, check your key/endpoint in the "
                       "sidebar status, or switch on **Demo mode** to continue "
                       "without the API."),
                handled_intent="error")
    metrics.record_new(resp.suggestions)
    return resp
