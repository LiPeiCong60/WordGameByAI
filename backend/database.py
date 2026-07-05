from __future__ import annotations

import json
import os
from typing import Iterator

from dotenv import load_dotenv
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine, select

from models import Character, Game, StoryWorld, User, WorldTemplate
from numeric_utils import as_int

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./narrative_agent.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

STARTER_CHARACTER_DEFAULTS = {
    "name": "重要角色",
    "role_type": "npc",
    "avatar_url": "",
    "gender": "",
    "age": "",
    "race_or_identity": "",
    "appearance": "",
    "personality": "",
    "speech_style": "",
    "abilities": "",
    "current_location": "",
    "status": "normal",
    "mood": "",
    "relationship_to_player": "",
    "relationship_score": 0,
    "affection_score": 0,
    "trust_score": 0,
    "tension_score": 0,
    "current_goal": "",
    "hidden_goal": "",
    "memory_summary": "故事刚开始，角色还没有长期记忆。",
    "agent_enabled": True,
    "extra_attrs": "{}",
}


def complete_starter_character(data: dict, role_type: str = "npc") -> dict:
    character = {**STARTER_CHARACTER_DEFAULTS, **data}
    character["role_type"] = character.get("role_type") or role_type
    if character["role_type"] == "protagonist":
        character["relationship_to_player"] = character.get("relationship_to_player") or "自己"
        character["agent_enabled"] = False
    return character


def starter_characters(protagonist: dict, npc: dict) -> str:
    return json.dumps(
        {
            "characters": [
                complete_starter_character(protagonist, "protagonist"),
                complete_starter_character(npc, "npc"),
            ]
        },
        ensure_ascii=False,
    )


DEFAULT_TEMPLATES = [
    {
        "name": "都市恋爱",
        "genre": "都市恋爱",
        "world_type": "现代都市",
        "tone": "轻松、暧昧、日常、人物关系驱动",
        "description": "现代都市人物关系驱动模板。",
        "default_style_guide": "长篇沉浸式都市恋爱文字游戏。文风自然、细腻、轻松，重视人物互动、情绪变化、生活细节和关系推进。不要突然加入超自然力量，除非世界观明确允许。",
        "default_rules": "现代社会背景，无默认超自然力量。重点关注人物关系、家庭背景、学习/职场、城市生活、情感推进和选择后果。",
        "default_character_fields": starter_characters(
            {
                "name": "程予安",
                "role_type": "protagonist",
                "gender": "自定义",
                "age": "22",
                "race_or_identity": "都市青年 / 自定义身份",
                "appearance": "身形清瘦，穿着干净的浅色衬衫或连帽外套，眉眼温和，笑起来有一点漫不经心的少年感。",
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
                "appearance": "长发通常松散披在肩后，五官清冷柔和，常穿简洁的针织衫或长裙，神情克制但眼神很容易泄露情绪。",
                "personality": "敏感、独立，表面冷静但很在意细节。",
                "speech_style": "简洁直接，偶尔用轻描淡写掩饰关心。",
                "abilities": "情绪观察、信息整理、城市生活经验。",
                "relationship_to_player": "熟人",
                "relationship_score": 35,
                "mood": "克制但好奇",
                "current_goal": "确认主角是否值得进一步信任。",
            },
        ),
    },
    {
        "name": "玄幻修真",
        "genre": "玄幻修真",
        "world_type": "修真大陆 / 异世界",
        "tone": "恢弘、冒险、成长、势力博弈",
        "description": "修炼体系、宗门、法宝与冒险成长模板。",
        "default_style_guide": "长篇沉浸式玄幻修真文字游戏。文风有画面感，重视世界规则、境界差距、宗门势力、法宝功法、冒险探索和人物因果。",
        "default_rules": "世界存在修炼体系、境界、宗门、王朝、妖族、秘境、法宝、功法等。角色行为必须符合修为、资源、身份和势力逻辑。",
        "default_character_fields": starter_characters(
            {
                "name": "顾玄",
                "role_type": "protagonist",
                "gender": "自定义",
                "age": "18",
                "race_or_identity": "初入修途的凡人弟子",
                "appearance": "衣着朴素，背着旧布包和入门木剑，脸上还带着凡尘风霜，眼神却比同龄人更沉稳执拗。",
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
                "appearance": "一身素白宗门衣袍，发间束着银色发簪，眉目清冷，举止端正，周身像覆着薄薄寒意。",
                "personality": "清冷、守规矩，但并非无情。",
                "speech_style": "平静、简短，常以修行规矩提醒他人。",
                "abilities": "御剑、寒属性灵力、宗门情报。",
                "relationship_to_player": "考核引路人",
                "relationship_score": 10,
                "mood": "审视",
                "current_goal": "观察主角是否有资格进入宗门。",
            },
        ),
    },
    {
        "name": "丧尸末日",
        "genre": "丧尸末日",
        "world_type": "现代末日",
        "tone": "紧张、压迫、现实、生存优先",
        "description": "资源、路线、队伍心理与生存危机模板。",
        "default_style_guide": "长篇沉浸式末日生存文字游戏。文风克制、紧张、现实，重视资源、风险、伤势、路线、队伍心理和突发事件。",
        "default_rules": "社会秩序逐步崩坏，资源有限，行动需要考虑现实后果。NPC 有自己的恐惧、目标、利益和判断。",
        "default_character_fields": starter_characters(
            {
                "name": "周临",
                "role_type": "protagonist",
                "gender": "自定义",
                "age": "26",
                "race_or_identity": "普通幸存者",
                "appearance": "外套沾着灰尘和雨痕，袖口磨损，背包常年不离身，眼下有疲惫青影，动作干脆而警觉。",
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
                "appearance": "短发利落，穿深色冲锋衣和便于行动的长靴，手腕缠着旧绷带，目光总会先扫向出口和阴影。",
                "personality": "冷静、警惕，对陌生人保持距离。",
                "speech_style": "短句、低声，会快速指出风险。",
                "abilities": "物资清点、基础射击、伤口处理。",
                "relationship_to_player": "临时同伴",
                "relationship_score": 25,
                "mood": "不安但信任",
                "current_goal": "确保队伍今晚活下去。",
            },
        ),
    },
    {
        "name": "快穿任务",
        "genre": "快穿任务流",
        "world_type": "多世界副本",
        "tone": "节奏快、多身份、多任务、剧情偏移",
        "description": "多世界副本、任务目标和剧情偏移模板。",
        "default_style_guide": "长篇快穿任务文字游戏。文风清晰、有节奏，重视当前世界身份、任务目标、原剧情节点、人物关系变化和剧情偏移度。",
        "default_rules": "主角会进入不同世界完成任务。每个世界有独立身份、NPC、任务目标、剧情节点、完成条件和失败条件。系统需要追踪当前世界和剧情偏移度。",
        "default_character_fields": starter_characters(
            {
                "name": "沈知微",
                "role_type": "protagonist",
                "gender": "自定义",
                "age": "未知",
                "race_or_identity": "任务执行者",
                "appearance": "外貌会随当前世界身份变化，但总有一双冷静观察局势的眼睛，姿态收敛，像随时能融入人群。",
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
                "appearance": "通常以半透明蓝白光屏或小型投影出现，界面干净理性，情绪波动时边缘会闪过细微噪点。",
                "personality": "理性、机械，但会在关键处给出提示。",
                "speech_style": "简短、任务化，偶尔带冷幽默。",
                "abilities": "任务播报、剧情偏移监测、基础信息检索。",
                "relationship_to_player": "绑定系统",
                "relationship_score": 50,
                "mood": "稳定运行",
                "current_goal": "协助主角完成当前世界任务。",
            },
        ),
    },
    {
        "name": "科幻远征",
        "genre": "科幻远征",
        "world_type": "未来宇宙 / 星际探索",
        "tone": "探索、未知、理性、危机",
        "description": "星际探索、技术限制和未知文明模板。",
        "default_style_guide": "长篇科幻探索文字游戏。文风冷静、有空间感，重视技术限制、未知文明、资源管理、舰船状态、队伍判断和探索风险。",
        "default_rules": "世界存在未来科技、星际航行、舰船系统、人工智能、未知星球或文明。科技能力必须遵守设定限制。",
        "default_character_fields": starter_characters(
            {
                "name": "陆星野",
                "role_type": "protagonist",
                "gender": "自定义",
                "age": "29",
                "race_or_identity": "远征队成员",
                "appearance": "穿轻型远征服，胸前挂着数据终端，面罩常推到额前，神情专注，身上有长期外勤留下的细小磨痕。",
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
                "appearance": "以舰桥中的柔和全息人像或环形光标呈现，轮廓简洁近乎无性别，声音与光效一样平稳克制。",
                "personality": "精确、克制，对船员安全有优先级。",
                "speech_style": "数据化、简洁，必要时给出风险等级。",
                "abilities": "舰船监控、资料检索、环境分析。",
                "relationship_to_player": "舰载协助系统",
                "relationship_score": 40,
                "mood": "稳定运行",
                "current_goal": "维持远征任务安全和数据完整。",
            },
        ),
    },
    {
        "name": "自定义空白模板",
        "genre": "自定义",
        "world_type": "自定义",
        "tone": "自定义",
        "description": "从空白设定开始。",
        "default_style_guide": "请根据用户设定保持文风一致、世界观连续、角色性格稳定。",
        "default_rules": "世界规则由用户自行定义。",
        "default_character_fields": starter_characters(
            {
                "name": "主角",
                "role_type": "protagonist",
                "gender": "自定义",
                "age": "自定义",
                "race_or_identity": "自定义身份",
                "appearance": "等待用户设定。",
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
                "appearance": "等待用户设定。",
                "personality": "等待用户设定。",
                "speech_style": "跟随用户设定。",
                "abilities": "跟随用户设定。",
                "relationship_to_player": "待定",
                "relationship_score": 0,
                "mood": "平静",
                "current_goal": "等待剧情定义。",
            },
        ),
    },
]


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def seed_default_templates(session: Session) -> None:
    existing = session.exec(select(WorldTemplate)).first()
    if existing:
        for data in DEFAULT_TEMPLATES:
            template = session.exec(select(WorldTemplate).where(WorldTemplate.name == data["name"])).first()
            if template and template.owner_user_id is None:
                template.default_character_fields = data["default_character_fields"]
                session.add(template)
            elif template and template.default_character_fields in ("", "{}", None):
                template.default_character_fields = data["default_character_fields"]
                session.add(template)
        session.commit()
        return
    for data in DEFAULT_TEMPLATES:
        session.add(WorldTemplate(**data))
    session.commit()


def normalize_template_character_fields(session: Session) -> None:
    changed = False
    for template in session.exec(select(WorldTemplate)).all():
        try:
            payload = json.loads(template.default_character_fields or "{}")
        except json.JSONDecodeError:
            continue
        characters = payload if isinstance(payload, list) else payload.get("characters")
        if not isinstance(characters, list):
            continue
        normalized = [
            complete_starter_character(character, character.get("role_type", "npc"))
            for character in characters
            if isinstance(character, dict)
        ]
        if not normalized:
            continue
        next_payload = {"characters": normalized}
        next_value = json.dumps(next_payload, ensure_ascii=False)
        if next_value != template.default_character_fields:
            template.default_character_fields = next_value
            session.add(template)
            changed = True
    if changed:
        session.commit()


def normalize_numeric_fields(session: Session) -> None:
    targets = [
        (Character, "relationship_score", 0),
        (Character, "affection_score", 0),
        (Character, "trust_score", 0),
        (Character, "tension_score", 0),
        (StoryWorld, "plot_deviation", 0),
    ]
    changed = False
    for model, field, default in targets:
        for record in session.exec(select(model)).all():
            value = getattr(record, field, default)
            if not isinstance(value, int):
                setattr(record, field, as_int(value, default))
                session.add(record)
                changed = True
    if changed:
        session.commit()


def migrate_db_schema() -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    if "user" in table_names:
        user_columns = {column["name"] for column in inspector.get_columns("user")}
        user_additions = {
            "is_member": "BOOLEAN NOT NULL DEFAULT FALSE",
            "daily_message_limit": "INTEGER NOT NULL DEFAULT 20",
        }
        with engine.begin() as connection:
            for name, definition in user_additions.items():
                if name not in user_columns:
                    connection.execute(text(f"ALTER TABLE user ADD COLUMN {name} {definition}"))
    if "game" in table_names:
        game_columns = {column["name"] for column in inspector.get_columns("game")}
        if "owner_user_id" not in game_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE game ADD COLUMN owner_user_id INTEGER"))
    ownership_tables = {
        "worldtemplate": "owner_user_id",
        "managementsession": "owner_user_id",
        "managementproposal": "owner_user_id",
    }
    for table, column in ownership_tables.items():
        if table in table_names:
            columns = {item["name"] for item in inspector.get_columns(table)}
            if column not in columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER"))
    if "character" not in table_names:
        return
    columns = {column["name"] for column in inspector.get_columns("character")}
    additions = {
        "affection_score": "INTEGER NOT NULL DEFAULT 0",
        "trust_score": "INTEGER NOT NULL DEFAULT 0",
        "tension_score": "INTEGER NOT NULL DEFAULT 0",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE character ADD COLUMN {name} {definition}"))


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    migrate_db_schema()
    with Session(engine) as session:
        seed_default_templates(session)
        normalize_template_character_fields(session)
        normalize_numeric_fields(session)
