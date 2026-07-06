from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.getenv("MODEL_CONFIG_FILE", str(BASE_DIR / "model_configs.json")))

AGENT_NAMES = [
    "ProtagonistAgent",
    "NPCReactionAgent",
    "NarratorAgent",
    "NarratorStreamAgent",
    "OpeningAgent",
    "OpeningStreamAgent",
    "PatchAgent",
    "CheckerAgent",
    "LoreAgent",
    "ManagementAgent",
]


def _empty_config() -> dict:
    return {
        "models": {},
        "levels": {},
        "default_model_id": "",
        "default_level_id": "",
        "user_levels": {},
    }


def _read_config() -> dict:
    if not CONFIG_PATH.exists():
        return _empty_config()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _empty_config()
    if not isinstance(data, dict):
        return _empty_config()

    config = {
        **_empty_config(),
        **data,
        "models": data.get("models") if isinstance(data.get("models"), dict) else {},
        "levels": data.get("levels") if isinstance(data.get("levels"), dict) else {},
        "user_levels": data.get("user_levels") if isinstance(data.get("user_levels"), dict) else {},
    }
    _migrate_legacy_config(config, data)
    return config


def _migrate_legacy_config(config: dict, raw: dict) -> None:
    legacy_agent_models = raw.get("agent_models")
    if legacy_agent_models and not config["levels"]:
        config["levels"]["default"] = {
            "label": "默认档",
            "description": "由旧版全局 Agent 模型配置迁移而来。",
            "fallback_model_id": raw.get("default_model_id") or "",
            "agent_models": legacy_agent_models if isinstance(legacy_agent_models, dict) else {},
        }
        config["default_level_id"] = "default"
    legacy_user_models = raw.get("user_models")
    if legacy_user_models and not config["user_levels"] and not config["levels"]:
        config["levels"]["legacy"] = {
            "label": "旧版用户模型档",
            "description": "兼容旧版用户模型配置。",
            "fallback_model_id": raw.get("default_model_id") or "",
            "agent_models": {},
        }
        config["default_level_id"] = "legacy"


def _write_config(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CONFIG_PATH.with_suffix(f"{CONFIG_PATH.suffix}.tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, CONFIG_PATH)
    try:
        CONFIG_PATH.chmod(0o600)
    except OSError:
        pass


def _validate_config_id(value: str, label: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise ValueError(f"{label} ID 不能为空。")
    if not all(char.isalnum() or char in "_-." for char in value):
        raise ValueError(f"{label} ID 只能包含字母、数字、下划线、短横线和点。")
    return value


def _model_payload(model_id: str, model: dict) -> dict:
    return {
        "id": model_id,
        "label": model.get("label") or model_id,
        "base_url": model.get("base_url") or "",
        "model": model.get("model") or "",
        "temperature": model.get("temperature", 0.7),
        "enabled": bool(model.get("enabled", True)),
        "has_api_key": bool(model.get("api_key")),
    }


def _level_payload(level_id: str, level: dict) -> dict:
    agent_models = level.get("agent_models") if isinstance(level.get("agent_models"), dict) else {}
    return {
        "id": level_id,
        "label": level.get("label") or level_id,
        "description": level.get("description") or "",
        "fallback_model_id": level.get("fallback_model_id") or "",
        "agent_models": dict(agent_models),
    }


def public_model_config() -> dict:
    data = _read_config()
    return {
        "models": [_model_payload(model_id, model) for model_id, model in sorted(data["models"].items())],
        "levels": [_level_payload(level_id, level) for level_id, level in sorted(data["levels"].items())],
        "default_model_id": data.get("default_model_id") or "",
        "default_level_id": data.get("default_level_id") or "",
        "user_levels": dict(data.get("user_levels") or {}),
        "agent_names": AGENT_NAMES,
        "config_path": str(CONFIG_PATH),
    }


def user_level_id(user_id: int | None) -> str:
    if user_id is None:
        return ""
    return str((_read_config().get("user_levels") or {}).get(str(user_id)) or "")


def upsert_model(payload: dict[str, Any]) -> dict:
    model_id = _validate_config_id(str(payload.get("id") or ""), "模型")
    data = _read_config()
    old = data["models"].get(model_id, {})
    model = {
        **old,
        "label": str(payload.get("label") or old.get("label") or model_id).strip(),
        "base_url": str(payload.get("base_url") or old.get("base_url") or "").strip().rstrip("/"),
        "model": str(payload.get("model") or old.get("model") or "").strip(),
        "temperature": float(payload.get("temperature", old.get("temperature", 0.7))),
        "enabled": bool(payload.get("enabled", old.get("enabled", True))),
    }
    if payload.get("clear_api_key"):
        model.pop("api_key", None)
    elif payload.get("api_key"):
        model["api_key"] = str(payload["api_key"]).strip()
    data["models"][model_id] = model
    if not data.get("default_model_id"):
        data["default_model_id"] = model_id
    _write_config(data)
    return _model_payload(model_id, model)


def delete_model(model_id: str) -> dict:
    data = _read_config()
    if model_id not in data["models"]:
        raise KeyError(model_id)
    data["models"].pop(model_id)
    if data.get("default_model_id") == model_id:
        data["default_model_id"] = next(iter(data["models"]), "")
    for level in data["levels"].values():
        if level.get("fallback_model_id") == model_id:
            level["fallback_model_id"] = ""
        agent_models = level.get("agent_models") if isinstance(level.get("agent_models"), dict) else {}
        level["agent_models"] = {key: value for key, value in agent_models.items() if value != model_id}
    _write_config(data)
    return {"ok": True}


def upsert_level(payload: dict[str, Any]) -> dict:
    level_id = _validate_config_id(str(payload.get("id") or ""), "模型等级")
    data = _read_config()
    fallback_model_id = str(payload.get("fallback_model_id") or "").strip()
    if fallback_model_id and fallback_model_id not in data["models"]:
        raise KeyError(fallback_model_id)

    agent_models = payload.get("agent_models") if isinstance(payload.get("agent_models"), dict) else {}
    cleaned_agent_models = {}
    for agent_name, model_id in agent_models.items():
        if agent_name not in AGENT_NAMES or not model_id:
            continue
        if model_id not in data["models"]:
            raise KeyError(model_id)
        cleaned_agent_models[agent_name] = model_id

    old = data["levels"].get(level_id, {})
    level = {
        **old,
        "label": str(payload.get("label") or old.get("label") or level_id).strip(),
        "description": str(payload.get("description") or old.get("description") or "").strip(),
        "fallback_model_id": fallback_model_id,
        "agent_models": cleaned_agent_models,
    }
    data["levels"][level_id] = level
    if not data.get("default_level_id"):
        data["default_level_id"] = level_id
    _write_config(data)
    return _level_payload(level_id, level)


def delete_level(level_id: str) -> dict:
    data = _read_config()
    if level_id not in data["levels"]:
        raise KeyError(level_id)
    data["levels"].pop(level_id)
    if data.get("default_level_id") == level_id:
        data["default_level_id"] = next(iter(data["levels"]), "")
    data["user_levels"] = {key: value for key, value in data["user_levels"].items() if value != level_id}
    _write_config(data)
    return {"ok": True}


def set_default_level(level_id: str | None) -> dict:
    data = _read_config()
    level_id = level_id or ""
    if level_id and level_id not in data["levels"]:
        raise KeyError(level_id)
    data["default_level_id"] = level_id
    _write_config(data)
    return public_model_config()


def set_default_model(model_id: str | None) -> dict:
    data = _read_config()
    model_id = model_id or ""
    if model_id and model_id not in data["models"]:
        raise KeyError(model_id)
    data["default_model_id"] = model_id
    _write_config(data)
    return public_model_config()


def set_user_level(user_id: int, level_id: str | None) -> dict:
    data = _read_config()
    key = str(user_id)
    if level_id:
        if level_id not in data["levels"]:
            raise KeyError(level_id)
        data["user_levels"][key] = level_id
    else:
        data["user_levels"].pop(key, None)
    _write_config(data)
    return public_model_config()


def resolve_model_config(agent_name: str | None = None, user_id: int | None = None) -> dict:
    data = _read_config()
    level_id = ""
    if user_id is not None:
        level_id = data["user_levels"].get(str(user_id), "")
    if not level_id:
        level_id = data.get("default_level_id") or ""

    level = data["levels"].get(level_id) if level_id else None
    agent_models = level.get("agent_models") if isinstance(level, dict) and isinstance(level.get("agent_models"), dict) else {}
    model_id = ""
    if agent_name:
        model_id = agent_models.get(agent_name, "")
    if not model_id and isinstance(level, dict):
        model_id = level.get("fallback_model_id") or ""
    if not model_id:
        model_id = data.get("default_model_id") or ""

    model = data["models"].get(model_id) if model_id else None
    if model and model.get("enabled", True):
        return {
            "source": "config",
            "id": model_id,
            "level_id": level_id,
            "agent_name": agent_name or "",
            "label": model.get("label") or model_id,
            "model": model.get("model") or "",
            "base_url": (model.get("base_url") or "https://api.openai.com/v1").rstrip("/"),
            "api_key": model.get("api_key") or "",
            "temperature": float(model.get("temperature", 0.7)),
        }

    return {
        "source": "env",
        "id": "env",
        "level_id": level_id,
        "agent_name": agent_name or "",
        "label": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        "api_key": os.getenv("OPENAI_API_KEY") or "",
        "temperature": 0.7,
    }
