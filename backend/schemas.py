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
    genre: str = ""
    world_type: str = ""
    tone: str = ""
    description: str = ""
    default_style_guide: str = ""
    default_rules: str = ""
    default_character_fields: str = "{}"


class TemplateUpdate(FlexibleModel):
    name: Optional[str] = None
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
    current_goal: Optional[str] = None
    hidden_goal: Optional[str] = None
    memory_summary: Optional[str] = None
    agent_enabled: Optional[bool] = None
    extra_attrs: Optional[str] = None


class ItemCreate(FlexibleModel):
    name: str
    item_type: str = "普通物品"
    description: str = ""
    status: str = "normal"
    rarity: str = "common"
    quantity_limit: int = 99
    is_stackable: bool = True
    is_equippable: bool = False
    is_consumable: bool = False
    is_key_item: bool = False
    is_tradeable: bool = True
    is_unique: bool = False
    usable_condition: str = ""
    effect_description: str = ""
    current_location: str = ""
    importance: int = 5
    extra_attrs: str = "{}"


class ItemUpdate(FlexibleModel):
    name: Optional[str] = None
    item_type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    rarity: Optional[str] = None
    quantity_limit: Optional[int] = None
    is_stackable: Optional[bool] = None
    is_equippable: Optional[bool] = None
    is_consumable: Optional[bool] = None
    is_key_item: Optional[bool] = None
    is_tradeable: Optional[bool] = None
    is_unique: Optional[bool] = None
    usable_condition: Optional[str] = None
    effect_description: Optional[str] = None
    current_location: Optional[str] = None
    importance: Optional[int] = None
    extra_attrs: Optional[str] = None


class InventoryCreate(FlexibleModel):
    item_id: int
    owner_type: str = "character"
    owner_id: Optional[int] = None
    owner_name: str = ""
    quantity: int = 1
    equipped: bool = False
    storage_location: str = ""
    item_state: str = "normal"
    note: str = ""


class InventoryUpdate(FlexibleModel):
    item_id: Optional[int] = None
    owner_type: Optional[str] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    quantity: Optional[int] = None
    equipped: Optional[bool] = None
    storage_location: Optional[str] = None
    item_state: Optional[str] = None
    note: Optional[str] = None


class TransferRequest(FlexibleModel):
    game_id: int
    item_id: int
    from_owner_type: str = "character"
    from_owner_id: Optional[int] = None
    from_owner_name: str = ""
    to_owner_type: str = "character"
    to_owner_id: Optional[int] = None
    to_owner_name: str = ""
    quantity: int = 1


class UseItemRequest(FlexibleModel):
    game_id: int
    character_id: int
    item_id: int
    quantity: int = 1
    context: Optional[str] = None


class EquipItemRequest(FlexibleModel):
    game_id: int
    character_id: int
    item_id: int


class EventCreate(FlexibleModel):
    title: str
    event_type: str = "背景事件"
    arc_name: str = ""
    related_world: str = ""
    summary: str = ""
    location: str = ""
    participants: str = ""
    consequence: str = ""
    status: str = "active"
    importance: int = 5
    extra_attrs: str = "{}"


class EventUpdate(FlexibleModel):
    title: Optional[str] = None
    event_type: Optional[str] = None
    arc_name: Optional[str] = None
    related_world: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[str] = None
    participants: Optional[str] = None
    consequence: Optional[str] = None
    status: Optional[str] = None
    importance: Optional[int] = None
    extra_attrs: Optional[str] = None


class TurnRequest(FlexibleModel):
    user_input: str = ""
    action_input: str = ""
    dialogue_input: str = ""
    auto_complete_blank: bool = True
    fast_mode: bool = False

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
    items: list[dict[str, Any]] = Field(default_factory=list)
    inventory_records: list[dict[str, Any]] = Field(default_factory=list)
    world_events: list[dict[str, Any]] = Field(default_factory=list)
    turn_logs: list[dict[str, Any]] = Field(default_factory=list)
    rag_memories: list[dict[str, Any]] = Field(default_factory=list)
    management_sessions: list[dict[str, Any]] = Field(default_factory=list)
    management_proposals: list[dict[str, Any]] = Field(default_factory=list)
