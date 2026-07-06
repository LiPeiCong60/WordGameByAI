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


def _chat_model(config: dict, api_key: str, timeout: float | None, streaming: bool = False) -> ChatOpenAI:
    model_kwargs = {}
    if streaming:
        model_kwargs["stream_options"] = {"include_usage": True}
    return ChatOpenAI(
        model=config.get("model") or "gpt-4o-mini",
        api_key=api_key,
        base_url=(config.get("base_url") or "https://api.openai.com/v1").rstrip("/"),
        temperature=float(config.get("temperature", 0.7)),
        timeout=timeout,
        model_kwargs=model_kwargs,
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
        runnable = _chat_model(config, api_key, timeout=60, streaming=False)
        if response_format:
            runnable = runnable.bind(response_format=response_format)
        response = runnable.invoke(messages)
        content = _content_to_text(response.content)
        
        # Log token usage
        prompt_tokens, completion_tokens, _ = _extract_token_usage(response)
        model_name = config.get("model") or "gpt-4o-mini"
        actual_user_id = user_id if user_id is not None else current_llm_user_id()
        
        # Estimate if zero (fallback)
        if prompt_tokens == 0 and completion_tokens == 0:
            prompt_tokens, completion_tokens = _estimate_tokens(messages, content)
            
        _log_token_usage(actual_user_id, model_name, prompt_tokens, completion_tokens)
        
        return content
    except Exception as exc:
        return json.dumps({"error": "LLM request failed."}, ensure_ascii=False)


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
        runnable = _chat_model(config, api_key, timeout=120, streaming=True)
        if response_format:
            runnable = runnable.bind(response_format=response_format)
            
        final_prompt_tokens = 0
        final_completion_tokens = 0
        model_name = config.get("model") or "gpt-4o-mini"
        accumulated_content = []
        
        for chunk in runnable.stream(messages):
            if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                meta = chunk.usage_metadata
                final_prompt_tokens = meta.get("input_tokens") or meta.get("prompt_tokens") or final_prompt_tokens
                final_completion_tokens = meta.get("output_tokens") or meta.get("completion_tokens") or final_completion_tokens
            elif hasattr(chunk, "response_metadata") and chunk.response_metadata:
                usage = chunk.response_metadata.get("token_usage")
                if isinstance(usage, dict):
                    final_prompt_tokens = usage.get("prompt_tokens") or final_prompt_tokens
                    final_completion_tokens = usage.get("completion_tokens") or final_completion_tokens
                    
            content = _content_to_text(chunk.content)
            if content:
                accumulated_content.append(content)
                yield content
                
        # Estimate if zero (fallback)
        if final_prompt_tokens == 0 and final_completion_tokens == 0:
            final_prompt_tokens, final_completion_tokens = _estimate_tokens(messages, "".join(accumulated_content))
            
        actual_user_id = user_id if user_id is not None else current_llm_user_id()
        _log_token_usage(actual_user_id, model_name, final_prompt_tokens, final_completion_tokens)
        
    except Exception as exc:
        yield "无法生成剧情：模型服务暂时不可用。"


def _extract_token_usage(response: Any) -> tuple[int, int, int]:
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        meta = response.usage_metadata
        prompt = meta.get("input_tokens") or meta.get("prompt_tokens") or 0
        completion = meta.get("output_tokens") or meta.get("completion_tokens") or 0
        total = meta.get("total_tokens") or (prompt + completion)
        return prompt, completion, total
    if hasattr(response, "response_metadata") and response.response_metadata:
        usage = response.response_metadata.get("token_usage")
        if isinstance(usage, dict):
            prompt = usage.get("prompt_tokens") or 0
            completion = usage.get("completion_tokens") or 0
            total = usage.get("total_tokens") or (prompt + completion)
            return prompt, completion, total
    return 0, 0, 0


def _estimate_tokens(messages: list[dict[str, str]], completion_text: str) -> tuple[int, int]:
    input_chars = sum(len(str(m.get("content") or "")) for m in messages)
    output_chars = len(completion_text)
    # Estimate: 1 char ≈ 0.8 tokens (average for Chinese/English mixed roleplay)
    prompt_tokens = int(input_chars * 0.8)
    completion_tokens = int(output_chars * 0.8)
    return max(prompt_tokens, 1), max(completion_tokens, 1)


def _log_token_usage(user_id: int | None, model_name: str, prompt_tokens: int, completion_tokens: int) -> None:
    if not user_id:
        return
    if prompt_tokens == 0 and completion_tokens == 0:
        return
    
    from database import engine
    from models import TokenUsageLog
    from sqlmodel import Session
    
    try:
        with Session(engine) as session:
            log = TokenUsageLog(
                user_id=user_id,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )
            session.add(log)
            session.commit()
    except Exception as exc:
        import sys
        print(f"Error logging token usage: {exc}", file=sys.stderr)
