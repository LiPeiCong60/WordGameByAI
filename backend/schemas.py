from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class FlexibleModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class GameCreate(FlexibleModel):
    title: str
    template_id: Optional[int] = None
    genre: str = ""
    world_type: str = ""
    tone: str = ""
    narrative_perspective: str = "第二人称"
    style_guide: str = ""
    rules_summary: str = ""
    current_state: str = ""
    current_story_world_id: Optional[int] = None


class CaptchaResponse(FlexibleModel):
    captcha_id: str
    svg: str
    expires_in: int = 600


class RegisterRequest(FlexibleModel):
    username: str
    password: str
    email: str = ""
    captcha_id: str
    captcha_answer: str


class LoginRequest(FlexibleModel):
    username: str
    password: str
    captcha_id: str
    captcha_answer: str


class AuthUserResponse(FlexibleModel):
    id: int
    username: str
    email: str = ""
    is_admin: bool = False
    is_member: bool = False
    daily_message_limit: int = 20


class AuthTokenResponse(FlexibleModel):
    token: str
    token_type: str = "bearer"
    expires_at: str
    user: AuthUserResponse


class AdminUserUpdate(FlexibleModel):
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    is_member: Optional[bool] = None
    daily_message_limit: Optional[int] = None


class GameUpdate(FlexibleModel):
    title: Optional[str] = None
    genre: Optional[str] = None
    world_type: Optional[str] = None
    tone: Optional[str] = None
    narrative_perspective: Optional[str] = None
    style_guide: Optional[str] = None
    rules_summary: Optional[str] = None
    current_state: Optional[str] = None
    current_story_world_id: Optional[int] = None


class TemplateCreate(FlexibleModel):
    name: str
    is_public: bool = False
    genre: str = ""
    world_type: str = ""
    tone: str = ""
    description: str = ""
    default_style_guide: str = ""
    default_rules: str = ""
    default_character_fields: str = "{}"


class TemplateUpdate(FlexibleModel):
    name: Optional[str] = None
    is_public: Optional[bool] = None
    genre: Optional[str] = None
    world_type: Optional[str] = None
    tone: Optional[str] = None
    description: Optional[str] = None
    default_style_guide: Optional[str] = None
    default_rules: Optional[str] = None
    default_character_fields: Optional[str] = None


class StoryWorldCreate(FlexibleModel):
    name: str
    world_type: str = ""
    summary: str = ""
    current_status: str = ""
    mission_objective: str = ""
    completion_condition: str = ""
    failure_condition: str = ""
    plot_deviation: int = 0


class StoryWorldUpdate(FlexibleModel):
    name: Optional[str] = None
    world_type: Optional[str] = None
    summary: Optional[str] = None
    current_status: Optional[str] = None
    mission_objective: Optional[str] = None
    completion_condition: Optional[str] = None
    failure_condition: Optional[str] = None
    plot_deviation: Optional[int] = None


class LoreCreate(FlexibleModel):
    title: str
    category: str = "其他"
    content: str = ""
    canon_level: str = "soft_canon"
    importance: int = 5


class LoreUpdate(FlexibleModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    canon_level: Optional[str] = None
    importance: Optional[int] = None


class LoreOrganizeRequest(FlexibleModel):
    text: str


class CharacterCreate(FlexibleModel):
    name: str
    role_type: str = "npc"
    avatar_url: str = ""
    gender: str = ""
    age: str = ""
    race_or_identity: str = ""
    appearance: str = ""
    personality: str = ""
    speech_style: str = ""
    abilities: str = ""
    current_location: str = ""
    status: str = "normal"
    mood: str = ""
    relationship_to_player: str = ""
    relationship_score: int = 0
    affection_score: int = 0
    trust_score: int = 0
    tension_score: int = 0
    current_goal: str = ""
    hidden_goal: str = ""
    memory_summary: str = ""
    agent_enabled: bool = True
    extra_attrs: str = "{}"


class CharacterUpdate(FlexibleModel):
    name: Optional[str] = None
    role_type: Optional[str] = None
    avatar_url: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None
    race_or_identity: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    speech_style: Optional[str] = None
    abilities: Optional[str] = None
    current_location: Optional[str] = None
    status: Optional[str] = None
    mood: Optional[str] = None
    relationship_to_player: Optional[str] = None
    relationship_score: Optional[int] = None
    affection_score: Optional[int] = None
    trust_score: Optional[int] = None
    tension_score: Optional[int] = None
    current_goal: Optional[str] = None
    hidden_goal: Optional[str] = None
    memory_summary: Optional[str] = None
    agent_enabled: Optional[bool] = None
    extra_attrs: Optional[str] = None


class TurnRequest(FlexibleModel):
    user_input: str = ""
    action_input: str = ""
    dialogue_input: str = ""
    auto_complete_blank: bool = True
    fast_mode: bool = False
    skip_state_update: bool = False
    async_state_update: bool = False

    def effective_user_input(self) -> str:
        action = (self.action_input or "").strip()
        dialogue = (self.dialogue_input or "").strip()
        fallback = (self.user_input or "").strip()
        if not action and not dialogue:
            return fallback

        lines = ["【玩家回合输入】"]
        if action:
            lines.append(f"行动/背景/希望响应：{action}")
        elif self.auto_complete_blank:
            lines.append("行动/背景/希望响应：<留空，允许系统结合上下文推测主角自然动作或当前处境>")
        else:
            lines.append("行动/背景/希望响应：<留空，无额外动作，只按台词或当前场景推进>")

        if dialogue:
            lines.append(f"主角台词：{dialogue}")
        elif self.auto_complete_blank:
            lines.append("主角台词：<留空，允许系统在必要时补一句符合人设的短对白；不必要时保持沉默>")
        else:
            lines.append("主角台词：<留空，主角本轮明确不主动说话>")

        lines.append(f"空白补全：{'开启' if self.auto_complete_blank else '关闭'}")
        return "\n".join(lines)


class RagSearchRequest(FlexibleModel):
    query: str
    top_k: int = 6


class ManagementSessionCreate(FlexibleModel):
    title: str = "管理对话"


class ManagementChatRequest(FlexibleModel):
    message: str
    scope: str = ""


class ImportPayload(FlexibleModel):
    game: dict[str, Any]
    story_worlds: list[dict[str, Any]] = Field(default_factory=list)
    world_lore: list[dict[str, Any]] = Field(default_factory=list)
    characters: list[dict[str, Any]] = Field(default_factory=list)
    turn_logs: list[dict[str, Any]] = Field(default_factory=list)
    rag_memories: list[dict[str, Any]] = Field(default_factory=list)
    management_sessions: list[dict[str, Any]] = Field(default_factory=list)
    management_proposals: list[dict[str, Any]] = Field(default_factory=list)
