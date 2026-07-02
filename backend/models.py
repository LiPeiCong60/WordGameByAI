from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


def now_utc() -> datetime:
    return datetime.utcnow()


class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=now_utc)
    updated_at: datetime = Field(default_factory=now_utc)


class Game(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    genre: str = ""
    world_type: str = ""
    tone: str = ""
    narrative_perspective: str = "第二人称"
    style_guide: str = Field(default="", sa_column=Column(Text))
    rules_summary: str = Field(default="", sa_column=Column(Text))
    current_state: str = Field(default="", sa_column=Column(Text))
    current_story_world_id: Optional[int] = None


class WorldTemplate(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    genre: str = ""
    world_type: str = ""
    tone: str = ""
    description: str = Field(default="", sa_column=Column(Text))
    default_style_guide: str = Field(default="", sa_column=Column(Text))
    default_rules: str = Field(default="", sa_column=Column(Text))
    default_character_fields: str = Field(default="{}", sa_column=Column(Text))


class StoryWorld(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    name: str
    world_type: str = ""
    summary: str = Field(default="", sa_column=Column(Text))
    current_status: str = Field(default="", sa_column=Column(Text))
    mission_objective: str = Field(default="", sa_column=Column(Text))
    completion_condition: str = Field(default="", sa_column=Column(Text))
    failure_condition: str = Field(default="", sa_column=Column(Text))
    plot_deviation: int = 0


class WorldLore(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    title: str
    category: str = "其他"
    content: str = Field(default="", sa_column=Column(Text))
    canon_level: str = "soft_canon"
    importance: int = 5


class Character(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    name: str
    role_type: str = "npc"
    avatar_url: str = ""
    gender: str = ""
    age: str = ""
    race_or_identity: str = ""
    appearance: str = Field(default="", sa_column=Column(Text))
    personality: str = Field(default="", sa_column=Column(Text))
    speech_style: str = Field(default="", sa_column=Column(Text))
    abilities: str = Field(default="", sa_column=Column(Text))
    current_location: str = ""
    status: str = "normal"
    mood: str = ""
    relationship_to_player: str = ""
    relationship_score: int = 0
    current_goal: str = Field(default="", sa_column=Column(Text))
    hidden_goal: str = Field(default="", sa_column=Column(Text))
    memory_summary: str = Field(default="", sa_column=Column(Text))
    agent_enabled: bool = True
    extra_attrs: str = Field(default="{}", sa_column=Column(Text))


class Item(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    name: str
    item_type: str = "普通物品"
    description: str = Field(default="", sa_column=Column(Text))
    status: str = "normal"
    rarity: str = "common"
    quantity_limit: int = 99
    is_stackable: bool = True
    is_equippable: bool = False
    is_consumable: bool = False
    is_key_item: bool = False
    is_tradeable: bool = True
    is_unique: bool = False
    usable_condition: str = Field(default="", sa_column=Column(Text))
    effect_description: str = Field(default="", sa_column=Column(Text))
    current_location: str = ""
    importance: int = 5
    extra_attrs: str = Field(default="{}", sa_column=Column(Text))


class InventoryRecord(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    item_id: int = Field(index=True)
    owner_type: str = "character"
    owner_id: Optional[int] = Field(default=None, index=True)
    owner_name: str = ""
    quantity: int = 1
    equipped: bool = False
    storage_location: str = ""
    item_state: str = "normal"
    note: str = Field(default="", sa_column=Column(Text))


class WorldEvent(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    title: str
    event_type: str = "背景事件"
    arc_name: str = ""
    related_world: str = ""
    summary: str = Field(default="", sa_column=Column(Text))
    location: str = ""
    participants: str = Field(default="", sa_column=Column(Text))
    consequence: str = Field(default="", sa_column=Column(Text))
    status: str = "active"
    importance: int = 5
    extra_attrs: str = Field(default="{}", sa_column=Column(Text))


class RagMemory(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    source_type: str = Field(index=True)
    source_id: Optional[int] = Field(default=None, index=True)
    title: str = ""
    content: str = Field(default="", sa_column=Column(Text))
    tags: str = ""
    importance: int = 5
    embedding_json: str = Field(default="{}", sa_column=Column(Text))
    extra_attrs: str = Field(default="{}", sa_column=Column(Text))


class TurnLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    turn_number: int
    user_input: str = Field(default="", sa_column=Column(Text))
    ai_response: str = Field(default="", sa_column=Column(Text))
    npc_reactions: str = Field(default="{}", sa_column=Column(Text))
    state_patch: str = Field(default="{}", sa_column=Column(Text))
    checker_result: str = Field(default="{}", sa_column=Column(Text))
    created_at: datetime = Field(default_factory=now_utc)


class TurnSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    turn_id: Optional[int] = Field(default=None, index=True)
    turn_number: int = Field(index=True)
    snapshot_json: str = Field(default="{}", sa_column=Column(Text))
    created_at: datetime = Field(default_factory=now_utc)


class ManagementSession(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    title: str = "管理对话"
    status: str = "active"


class ManagementProposal(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    session_id: int = Field(index=True)
    user_request: str = Field(default="", sa_column=Column(Text))
    agent_response: str = Field(default="", sa_column=Column(Text))
    proposed_actions: str = Field(default="[]", sa_column=Column(Text))
    status: str = "pending_confirmation"
    applied_at: Optional[datetime] = None
