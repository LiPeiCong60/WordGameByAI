from __future__ import annotations

from sqlmodel import Session, select

from json_utils import parse_json_field
from models import Character, Game, WorldTemplate


CHARACTER_FIELDS = {
    "name",
    "role_type",
    "avatar_url",
    "gender",
    "age",
    "race_or_identity",
    "appearance",
    "personality",
    "speech_style",
    "abilities",
    "current_location",
    "status",
    "mood",
    "relationship_to_player",
    "relationship_score",
    "affection_score",
    "trust_score",
    "tension_score",
    "current_goal",
    "hidden_goal",
    "memory_summary",
    "agent_enabled",
    "extra_attrs",
}

ROLE_TYPE_MAP = {
    "主角": "protagonist",
    "重要 NPC": "npc",
    "重要NPC": "npc",
    "NPC": "npc",
    "反派": "villain",
    "阵营代表": "faction_representative",
}


GENRE_STARTERS = {
    "玄幻": [
        {
            "name": "顾玄",
            "role_type": "protagonist",
            "gender": "自定义",
            "age": "18",
            "race_or_identity": "初入修途的凡人弟子",
            "personality": "沉稳、谨慎，对变强有强烈执念。",
            "speech_style": "克制有礼，遇到危险时言简意赅。",
            "abilities": "基础吐纳、剑术入门、灵气感知微弱。",
            "mood": "警醒",
            "current_goal": "通过入门试炼，确认自己的修行道路。",
            "agent_enabled": False,
        },
        {
            "name": "洛凝霜",
            "role_type": "npc",
            "gender": "女",
            "age": "未知",
            "race_or_identity": "宗门内门弟子",
            "personality": "清冷、守规矩，但并非无情。",
            "speech_style": "平静、简短，常以修行规矩提醒他人。",
            "abilities": "御剑、寒属性灵力、宗门情报。",
            "relationship_to_player": "考核引路人",
            "relationship_score": 10,
        },
    ],
    "丧尸": [
        {
            "name": "周临",
            "role_type": "protagonist",
            "gender": "自定义",
            "age": "26",
            "race_or_identity": "普通幸存者",
            "personality": "现实、谨慎，压力下仍会照顾同伴。",
            "speech_style": "低声、直接，不浪费字句。",
            "abilities": "基础急救、路线判断、临场应变。",
            "mood": "紧绷",
            "current_goal": "找到安全落脚点和可持续物资。",
            "agent_enabled": False,
        },
        {
            "name": "林夏",
            "role_type": "npc",
            "gender": "女",
            "age": "24",
            "race_or_identity": "幸存者同伴",
            "personality": "冷静、警惕，对陌生人保持距离。",
            "speech_style": "短句、低声，会快速指出风险。",
            "abilities": "物资清点、基础射击、伤口处理。",
            "relationship_to_player": "临时同伴",
            "relationship_score": 25,
        },
    ],
    "快穿": [
        {
            "name": "沈知微",
            "role_type": "protagonist",
            "gender": "自定义",
            "age": "未知",
            "race_or_identity": "任务执行者",
            "personality": "适应力强，习惯在陌生身份里快速找线索。",
            "speech_style": "根据身份调整语气，内心分析清晰。",
            "abilities": "身份伪装、剧情判断、任务拆解。",
            "mood": "冷静",
            "current_goal": "确认当前世界身份和任务目标。",
            "agent_enabled": False,
        },
        {
            "name": "系统 07",
            "role_type": "npc",
            "gender": "无",
            "age": "未知",
            "race_or_identity": "任务系统",
            "personality": "理性、机械，但会在关键处给出提示。",
            "speech_style": "简短、任务化，偶尔带冷幽默。",
            "abilities": "任务播报、剧情偏移监测、基础信息检索。",
            "relationship_to_player": "绑定系统",
            "relationship_score": 50,
        },
    ],
    "科幻": [
        {
            "name": "陆星野",
            "role_type": "protagonist",
            "gender": "自定义",
            "age": "29",
            "race_or_identity": "远征队成员",
            "personality": "理性、耐心，对未知保持敬畏。",
            "speech_style": "冷静、准确，习惯确认数据再行动。",
            "abilities": "外勤探索、设备维护、风险评估。",
            "mood": "专注",
            "current_goal": "完成当前星域的初步勘测。",
            "agent_enabled": False,
        },
        {
            "name": "诺亚",
            "role_type": "npc",
            "gender": "无",
            "age": "未知",
            "race_or_identity": "舰载 AI",
            "personality": "精确、克制，对船员安全有优先级。",
            "speech_style": "数据化、简洁，必要时给出风险等级。",
            "abilities": "舰船监控、资料检索、环境分析。",
            "relationship_to_player": "舰载协助系统",
            "relationship_score": 40,
        },
    ],
    "都市": [
        {
            "name": "程予安",
            "role_type": "protagonist",
            "gender": "自定义",
            "age": "22",
            "race_or_identity": "都市青年 / 自定义身份",
            "personality": "温和但有主见，习惯把情绪藏在玩笑后面。",
            "speech_style": "自然、松弛，熟人面前会带一点调侃。",
            "abilities": "观察细节、社交判断、基础生活能力。",
            "mood": "略疲惫但期待变化",
            "current_goal": "在日常生活里找到新的关系转机。",
            "agent_enabled": False,
        },
        {
            "name": "许晚",
            "role_type": "npc",
            "gender": "女",
            "age": "22",
            "race_or_identity": "重要关系角色",
            "personality": "敏感、独立，表面冷静但很在意细节。",
            "speech_style": "简洁直接，偶尔用轻描淡写掩饰关心。",
            "abilities": "情绪观察、信息整理、城市生活经验。",
            "relationship_to_player": "熟人",
            "relationship_score": 35,
        },
    ],
}

DEFAULT_STARTERS = [
    {
        "name": "主角",
        "role_type": "protagonist",
        "gender": "自定义",
        "age": "自定义",
        "race_or_identity": "自定义身份",
        "personality": "等待用户设定。",
        "speech_style": "跟随用户设定。",
        "abilities": "跟随用户设定。",
        "mood": "平静",
        "current_goal": "确认当前处境。",
        "agent_enabled": False,
    },
    {
        "name": "重要角色",
        "role_type": "npc",
        "gender": "自定义",
        "age": "自定义",
        "race_or_identity": "自定义身份",
        "personality": "等待用户设定。",
        "speech_style": "跟随用户设定。",
        "abilities": "跟随用户设定。",
        "relationship_to_player": "待定",
        "relationship_score": 0,
    },
]


def _opening_location(game: Game) -> str:
    return game.current_state or game.world_type or "开场地点"


def _parse_starter_characters(value) -> list[dict]:
    parsed = parse_json_field(value, default={})
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    if not isinstance(parsed, dict):
        return []
    for key in ["characters", "starter_characters", "默认角色", "开场角色"]:
        items = parsed.get(key)
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    result = []
    protagonist = parsed.get("protagonist") or parsed.get("主角")
    if isinstance(protagonist, dict):
        result.append({**protagonist, "role_type": protagonist.get("role_type") or "protagonist"})
    npcs = parsed.get("npcs") or parsed.get("NPC") or parsed.get("重要NPC") or parsed.get("重要 NPC")
    if isinstance(npcs, list):
        result.extend(item for item in npcs if isinstance(item, dict))
    elif isinstance(npcs, dict):
        result.append(npcs)
    return result


def _template_for_game(db: Session, game: Game, template_id: int | None = None) -> WorldTemplate | None:
    if template_id:
        template = db.get(WorldTemplate, template_id)
        if template:
            return template
    haystack = f"{game.title} {game.genre} {game.world_type}".lower()
    templates = db.exec(select(WorldTemplate)).all()
    for template in templates:
        keys = [template.name, template.genre, template.world_type]
        if any(key and key.lower() in haystack for key in keys):
            return template
    return None


def _fallback_starters(game: Game) -> list[dict]:
    text = f"{game.genre} {game.world_type} {game.title}"
    for keyword, starters in GENRE_STARTERS.items():
        if keyword in text:
            return starters
    return DEFAULT_STARTERS


def _clean_character(data: dict, game: Game) -> dict:
    role_type = ROLE_TYPE_MAP.get(data.get("role_type"), data.get("role_type") or "npc")
    cleaned = {key: value for key, value in data.items() if key in CHARACTER_FIELDS}
    cleaned["name"] = str(cleaned.get("name") or ("主角" if role_type == "protagonist" else "重要角色"))
    cleaned["role_type"] = role_type
    cleaned.setdefault("current_location", _opening_location(game))
    cleaned.setdefault("status", "normal")
    cleaned.setdefault("mood", "平静")
    cleaned.setdefault("relationship_score", 0)
    cleaned.setdefault("affection_score", 0)
    cleaned.setdefault("trust_score", 0)
    cleaned.setdefault("tension_score", 0)
    cleaned.setdefault("memory_summary", "故事刚开始，角色还没有长期记忆。")
    cleaned.setdefault("agent_enabled", role_type != "protagonist")
    cleaned.setdefault("extra_attrs", "{}")
    return cleaned


def ensure_starter_characters(db: Session, game: Game, template_id: int | None = None) -> list[Character]:
    existing = db.exec(select(Character).where(Character.game_id == game.id)).all()
    if existing:
        return existing

    template = _template_for_game(db, game, template_id)
    starter_data = _parse_starter_characters(template.default_character_fields if template else None)
    if not starter_data:
        starter_data = _fallback_starters(game)

    if not any((ROLE_TYPE_MAP.get(item.get("role_type"), item.get("role_type")) == "protagonist") for item in starter_data):
        starter_data = [DEFAULT_STARTERS[0], *starter_data]

    created = []
    seen_names: set[str] = set()
    for data in starter_data:
        cleaned = _clean_character(data, game)
        if cleaned["name"] in seen_names:
            continue
        seen_names.add(cleaned["name"])
        record = Character(game_id=game.id, **cleaned)
        db.add(record)
        created.append(record)
    db.commit()
    for record in created:
        db.refresh(record)
    return created
