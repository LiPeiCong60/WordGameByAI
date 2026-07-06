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
    owner_user_id: Optional[int] = Field(default=None, index=True)
    title: str = Field(max_length=200)
    genre: str = Field(default="", max_length=100)
    world_type: str = Field(default="", max_length=100)
    tone: str = Field(default="", max_length=200)
    narrative_perspective: str = Field(default="第二人称", max_length=50)
    style_guide: str = Field(default="", sa_column=Column(Text))
    rules_summary: str = Field(default="", sa_column=Column(Text))
    current_state: str = Field(default="", sa_column=Column(Text))
    current_story_world_id: Optional[int] = None


class User(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, max_length=80)
    email: str = Field(default="", index=True, max_length=200)
    password_hash: str = Field(default="", sa_column=Column(Text))
    is_admin: bool = False
    is_member: bool = False
    daily_message_limit: int = 20
    is_active: bool = True
    last_login_at: Optional[datetime] = None


class AuthToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    token_hash: str = Field(index=True, max_length=128)
    created_at: datetime = Field(default_factory=now_utc)
    expires_at: datetime = Field(index=True)
    revoked: bool = False


class CaptchaChallenge(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=80)
    answer_hash: str = Field(default="", sa_column=Column(Text))
    created_at: datetime = Field(default_factory=now_utc)
    expires_at: datetime = Field(index=True)
    used: bool = False


class MessageUsage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    usage_date: str = Field(index=True, max_length=20)
    message_count: int = 0
    updated_at: datetime = Field(default_factory=now_utc)


class TokenUsageLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    model_name: str = Field(index=True, max_length=150)
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    created_at: datetime = Field(default_factory=now_utc)


class WorldTemplate(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_user_id: Optional[int] = Field(default=None, index=True)
    name: str = Field(max_length=200)
    genre: str = Field(default="", max_length=100)
    world_type: str = Field(default="", max_length=100)
    tone: str = Field(default="", max_length=200)
    description: str = Field(default="", sa_column=Column(Text))
    default_style_guide: str = Field(default="", sa_column=Column(Text))
    default_rules: str = Field(default="", sa_column=Column(Text))
    default_character_fields: str = Field(default="{}", sa_column=Column(Text))


class StoryWorld(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    name: str = Field(max_length=200)
    world_type: str = Field(default="", max_length=100)
    summary: str = Field(default="", sa_column=Column(Text))
    current_status: str = Field(default="", sa_column=Column(Text))
    mission_objective: str = Field(default="", sa_column=Column(Text))
    completion_condition: str = Field(default="", sa_column=Column(Text))
    failure_condition: str = Field(default="", sa_column=Column(Text))
    plot_deviation: int = 0


class WorldLore(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    title: str = Field(max_length=200)
    category: str = Field(default="其他", max_length=80)
    content: str = Field(default="", sa_column=Column(Text))
    canon_level: str = Field(default="soft_canon", max_length=50)
    importance: int = 5


class Character(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    name: str = Field(max_length=120)
    role_type: str = Field(default="npc", max_length=50)
    avatar_url: str = Field(default="", max_length=500)
    gender: str = Field(default="", max_length=50)
    age: str = Field(default="", max_length=50)
    race_or_identity: str = Field(default="", max_length=200)
    appearance: str = Field(default="", sa_column=Column(Text))
    personality: str = Field(default="", sa_column=Column(Text))
    speech_style: str = Field(default="", sa_column=Column(Text))
    abilities: str = Field(default="", sa_column=Column(Text))
    current_location: str = Field(default="", max_length=300)
    status: str = Field(default="normal", max_length=80)
    mood: str = Field(default="", max_length=200)
    relationship_to_player: str = Field(default="", max_length=200)
    relationship_score: int = 0
    affection_score: int = 0
    trust_score: int = 0
    tension_score: int = 0
    current_goal: str = Field(default="", sa_column=Column(Text))
    hidden_goal: str = Field(default="", sa_column=Column(Text))
    memory_summary: str = Field(default="", sa_column=Column(Text))
    agent_enabled: bool = True
    extra_attrs: str = Field(default="{}", sa_column=Column(Text))


class RagMemory(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    source_type: str = Field(index=True, max_length=80)
    source_id: Optional[int] = Field(default=None, index=True)
    title: str = Field(default="", max_length=240)
    content: str = Field(default="", sa_column=Column(Text))
    tags: str = Field(default="", max_length=500)
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
    snapshot_json: str = Field(default="{}", sa_column=Column(Text(length=16777215)))
    created_at: datetime = Field(default_factory=now_utc)


class ManagementSession(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    owner_user_id: Optional[int] = Field(default=None, index=True)
    title: str = Field(default="管理对话", max_length=200)
    status: str = Field(default="active", max_length=50)


class ManagementProposal(TimestampMixin, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(index=True)
    session_id: int = Field(index=True)
    owner_user_id: Optional[int] = Field(default=None, index=True)
    user_request: str = Field(default="", sa_column=Column(Text))
    agent_response: str = Field(default="", sa_column=Column(Text))
    proposed_actions: str = Field(default="[]", sa_column=Column(Text))
    status: str = Field(default="pending_confirmation", max_length=50)
    applied_at: Optional[datetime] = None
