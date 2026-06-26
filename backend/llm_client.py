from __future__ import annotations

import json
import os
from typing import Any, Iterator

import httpx
from dotenv import load_dotenv

load_dotenv()


def call_llm(messages: list[dict[str, str]], response_format: dict[str, Any] | None = None) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        return json.dumps({"error": "LLM API key is not configured."}, ensure_ascii=False)

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
    }
    if response_format:
        payload["response_format"] = response_format

    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        return json.dumps({"error": f"LLM request failed: {exc}"}, ensure_ascii=False)


def call_llm_stream(messages: list[dict[str, str]], response_format: dict[str, Any] | None = None) -> Iterator[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        yield "无法生成剧情：LLM API key is not configured."
        return

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "stream": True,
    }
    if response_format:
        payload["response_format"] = response_format

    try:
        with httpx.Client(timeout=None) as client:
            with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    try:
                        payload = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = payload.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if content:
                        yield content
    except Exception as exc:
        yield f"无法生成剧情：LLM request failed: {exc}"
