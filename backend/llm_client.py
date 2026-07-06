from __future__ import annotations

import json
import os
from contextvars import ContextVar
from typing import Any, Iterator

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from model_config_service import resolve_model_config

load_dotenv()

CURRENT_LLM_USER_ID: ContextVar[int | None] = ContextVar("CURRENT_LLM_USER_ID", default=None)


def set_current_llm_user(user_id: int | None):
    return CURRENT_LLM_USER_ID.set(user_id)


def reset_current_llm_user(token) -> None:
    CURRENT_LLM_USER_ID.reset(token)


def current_llm_user_id() -> int | None:
    return CURRENT_LLM_USER_ID.get()


def _llm_config(agent_name: str | None = None, user_id: int | None = None) -> dict:
    return resolve_model_config(agent_name=agent_name, user_id=user_id if user_id is not None else current_llm_user_id())


def _api_key(config: dict) -> str | None:
    api_key = config.get("api_key")
    if not api_key or api_key == "your_api_key_here":
        return None
    return api_key


def _chat_model(config: dict, api_key: str, timeout: float | None) -> ChatOpenAI:
    return ChatOpenAI(
        model=config.get("model") or "gpt-4o-mini",
        api_key=api_key,
        base_url=(config.get("base_url") or "https://api.openai.com/v1").rstrip("/"),
        temperature=float(config.get("temperature", 0.7)),
        timeout=timeout,
    )


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text") or part.get("content")
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return "" if content is None else str(content)


def call_llm(
    messages: list[dict[str, str]],
    response_format: dict[str, Any] | None = None,
    agent_name: str | None = None,
    user_id: int | None = None,
) -> str:
    config = _llm_config(agent_name, user_id)
    api_key = _api_key(config)
    if not api_key:
        return json.dumps({"error": "LLM API key is not configured."}, ensure_ascii=False)

    try:
        runnable = _chat_model(config, api_key, timeout=60)
        if response_format:
            runnable = runnable.bind(response_format=response_format)
        response = runnable.invoke(messages)
        return _content_to_text(response.content)
    except Exception as exc:
        return json.dumps({"error": f"LLM request failed: {exc}"}, ensure_ascii=False)


def call_llm_stream(
    messages: list[dict[str, str]],
    response_format: dict[str, Any] | None = None,
    agent_name: str | None = None,
    user_id: int | None = None,
) -> Iterator[str]:
    config = _llm_config(agent_name, user_id)
    api_key = _api_key(config)
    if not api_key:
        yield "无法生成剧情：LLM API key is not configured."
        return

    try:
        runnable = _chat_model(config, api_key, timeout=None)
        if response_format:
            runnable = runnable.bind(response_format=response_format)
        for chunk in runnable.stream(messages):
            content = _content_to_text(chunk.content)
            if content:
                yield content
    except Exception as exc:
        yield f"无法生成剧情：LLM request failed: {exc}"
