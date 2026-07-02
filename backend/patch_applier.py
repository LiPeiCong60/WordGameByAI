from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from json_utils import dump_json_field, merge_json_field, parse_json_field
from models import Character, Game, InventoryRecord, Item, StoryWorld, WorldEvent
from numeric_utils import as_int


def _touch(record) -> None:
    if hasattr(record, "updated_at"):
        record.updated_at = datetime.utcnow()


AMBIENT_NAME_MARKERS = ("一群", "路人", "群众", "人群", "军人们", "士兵们", "猎户们", "守卫们", "店员们", "围观者")


def _truthy(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "是", "启用", "重要"}
    return bool(value)


def _as_int(value, default: int = 0) -> int:
    return as_int(value, default)


def _looks_ambient_name(name: str) -> bool:
    return any(marker in name for marker in AMBIENT_NAME_MARKERS)


def _find_character(db: Session, game_id: int, name: str | None = None, character_id: int | None = None) -> Character | None:
    if character_id:
        character = db.get(Character, _as_int(character_id))
        return character if character and character.game_id == game_id else None
    if not name:
        return None
    return db.exec(select(Character).where(Character.game_id == game_id, Character.name == name)).first()


def _find_item(db: Session, game_id: int, name: str | None = None, item_id: int | None = None) -> Item | None:
    if item_id:
        item = db.get(Item, _as_int(item_id))
        return item if item and item.game_id == game_id else None
    if not name:
        return None
    return db.exec(select(Item).where(Item.game_id == game_id, Item.name == name)).first()


def _owner_payload(db: Session, game_id: int, update: dict, prefix: str = "") -> tuple[str, int | None, str]:
    owner_type = update.get(f"{prefix}owner_type") or update.get("owner_type") or "character"
    owner_id = update.get(f"{prefix}owner_id")
    owner_id = _as_int(owner_id) if owner_id not in (None, "") else None
    owner_name = update.get(f"{prefix}owner_name") or update.get("owner_name") or ""
    if owner_type == "character":
        character = _find_character(db, game_id, owner_name, owner_id)
        if character:
            return "character", character.id, character.name
    return owner_type, owner_id, owner_name


def _find_inventory_record(
    db: Session,
    game_id: int,
    item_id: int,
    owner_type: str,
    owner_id: int | None,
    owner_name: str,
) -> InventoryRecord | None:
    query = select(InventoryRecord).where(
        InventoryRecord.game_id == game_id,
        InventoryRecord.item_id == item_id,
        InventoryRecord.owner_type == owner_type,
    )
    if owner_id is not None:
        query = query.where(InventoryRecord.owner_id == owner_id)
    elif owner_name:
        query = query.where(InventoryRecord.owner_name == owner_name)
    return db.exec(query).first()


def _upsert_inventory_record(
    db: Session,
    game_id: int,
    item_id: int,
    owner_type: str,
    owner_id: int | None,
    owner_name: str,
    quantity: int,
    update: dict,
) -> InventoryRecord:
    record = _find_inventory_record(db, game_id, item_id, owner_type, owner_id, owner_name)
    if record:
        record.quantity = max(0, record.quantity + quantity)
    else:
        record = InventoryRecord(
            game_id=game_id,
            item_id=item_id,
            owner_type=owner_type,
            owner_id=owner_id,
            owner_name=owner_name,
            quantity=max(0, quantity),
        )
    if update.get("item_state"):
        record.item_state = update["item_state"]
    elif record.quantity > 0 and record.item_state in {"lost", "broken", "consumed"}:
        record.item_state = "normal"
    if "equipped" in update:
        record.equipped = _truthy(update.get("equipped"))
    if update.get("storage_location"):
        record.storage_location = update["storage_location"]
    if update.get("context"):
        record.note = update["context"]
    _touch(record)
    db.add(record)
    return record


def apply_state_patch(game_id: int, state_patch: dict, db: Session) -> dict:
    warnings: list[str] = []
    game = db.get(Game, game_id)
    if not game:
        return {"ok": False, "warnings": [f"找不到游戏: {game_id}"]}

    if state_patch.get("current_state_update"):
        game.current_state = state_patch["current_state_update"]
        _touch(game)
        db.add(game)

    for event in state_patch.get("new_events") or []:
        if isinstance(event, dict):
            db.add(
                WorldEvent(
                    game_id=game_id,
                    title=event.get("title") or event.get("summary") or "未命名事件",
                    event_type=event.get("event_type", "剧情事件"),
                    arc_name=event.get("arc_name", ""),
                    related_world=event.get("related_world", ""),
                    summary=event.get("summary", ""),
                    location=event.get("location", ""),
                    participants=event.get("participants", ""),
                    consequence=event.get("consequence", ""),
                    status=event.get("status", "active"),
                    importance=_as_int(event.get("importance"), 5),
                    extra_attrs=event.get("extra_attrs", "{}"),
                )
            )

    for character_patch in state_patch.get("new_characters") or []:
        if not isinstance(character_patch, dict):
            continue
        name = (character_patch.get("name") or "").strip()
        if not name:
            continue
        if _looks_ambient_name(name):
            warnings.append(f"疑似背景群体，未创建为可管理 NPC: {name}")
            continue
        if db.exec(select(Character).where(Character.game_id == game_id, Character.name == name)).first():
            continue
        importance = _as_int(character_patch.get("importance"), 7)
        extra_attrs = parse_json_field(character_patch.get("extra_attrs"), default={})
        if not isinstance(extra_attrs, dict):
            extra_attrs = {}
        extra_attrs.update(
            {
                "自动发现": True,
                "重要度": importance,
                "加入原因": character_patch.get("management_reason", ""),
            }
        )
        db.add(
            Character(
                game_id=game_id,
                name=name,
                role_type=character_patch.get("role_type", "npc"),
                gender=character_patch.get("gender", ""),
                age=character_patch.get("age", ""),
                race_or_identity=character_patch.get("race_or_identity", ""),
                appearance=character_patch.get("appearance", ""),
                personality=character_patch.get("personality", ""),
                speech_style=character_patch.get("speech_style", ""),
                abilities=character_patch.get("abilities", ""),
                current_location=character_patch.get("current_location", ""),
                status=character_patch.get("status", "normal"),
                mood=character_patch.get("mood", ""),
                relationship_to_player=character_patch.get("relationship_to_player", ""),
                relationship_score=_as_int(character_patch.get("relationship_score"), 0),
                current_goal=character_patch.get("current_goal", ""),
                hidden_goal=character_patch.get("hidden_goal", ""),
                memory_summary=character_patch.get("memory_summary", ""),
                agent_enabled=_truthy(character_patch.get("agent_enabled"), True),
                extra_attrs=dump_json_field(extra_attrs),
            )
        )

    for ambient in state_patch.get("ambient_characters") or []:
        if isinstance(ambient, dict):
            db.add(
                WorldEvent(
                    game_id=game_id,
                    title=f"背景角色：{ambient.get('label') or ambient.get('name') or '未命名群体'}",
                    event_type="背景角色",
                    summary=ambient.get("summary") or ambient.get("role_in_scene") or "",
                    location=ambient.get("location", ""),
                    participants=ambient.get("label") or ambient.get("name") or "",
                    importance=_as_int(ambient.get("importance"), 2),
                    extra_attrs=dump_json_field({"自动记录": True, "分类": ambient.get("category", "背景角色")}),
                )
            )

    for item in state_patch.get("updated_characters") or []:
        name = item.get("name") if isinstance(item, dict) else None
        if not name:
            continue
        character = db.exec(select(Character).where(Character.game_id == game_id, Character.name == name)).first()
        if not character:
            warnings.append(f"找不到角色，未应用更新: {name}")
            continue
        for key in [
            "status",
            "mood",
            "relationship_to_player",
            "current_goal",
            "current_location",
            "memory_summary",
        ]:
            if key in item:
                setattr(character, key, item[key])
        if "relationship_score" in item:
            character.relationship_score = _as_int(item.get("relationship_score"), character.relationship_score)
        if "extra_attrs" in item:
            character.extra_attrs = merge_json_field(character.extra_attrs, item["extra_attrs"])
        _touch(character)
        db.add(character)

    for item_patch in state_patch.get("new_items") or []:
        if not isinstance(item_patch, dict):
            continue
        name = (item_patch.get("name") or "").strip()
        if not name:
            continue
        if db.exec(select(Item).where(Item.game_id == game_id, Item.name == name)).first():
            continue
        extra_attrs = parse_json_field(item_patch.get("extra_attrs"), default={})
        if not isinstance(extra_attrs, dict):
            extra_attrs = {}
        extra_attrs.update({"自动发现": True})
        db.add(
            Item(
                game_id=game_id,
                name=name,
                item_type=item_patch.get("item_type", "普通物品"),
                description=item_patch.get("description", ""),
                status=item_patch.get("status", "normal"),
                rarity=item_patch.get("rarity", "common"),
                quantity_limit=_as_int(item_patch.get("quantity_limit"), 99),
                is_stackable=_truthy(item_patch.get("is_stackable"), True),
                is_equippable=_truthy(item_patch.get("is_equippable"), False),
                is_consumable=_truthy(item_patch.get("is_consumable"), False),
                is_key_item=_truthy(item_patch.get("is_key_item"), False),
                is_tradeable=_truthy(item_patch.get("is_tradeable"), True),
                is_unique=_truthy(item_patch.get("is_unique"), False),
                usable_condition=item_patch.get("usable_condition", ""),
                effect_description=item_patch.get("effect_description", ""),
                current_location=item_patch.get("current_location", ""),
                importance=_as_int(item_patch.get("importance"), 5),
                extra_attrs=dump_json_field(extra_attrs),
            )
        )

    for item_patch in state_patch.get("updated_items") or []:
        name = item_patch.get("name") if isinstance(item_patch, dict) else None
        if not name:
            continue
        item = db.exec(select(Item).where(Item.game_id == game_id, Item.name == name)).first()
        if not item:
            warnings.append(f"找不到物品，未应用更新: {name}")
            continue
        for key in ["status", "current_location"]:
            if key in item_patch:
                setattr(item, key, item_patch[key])
        if "importance" in item_patch:
            item.importance = _as_int(item_patch.get("importance"), item.importance)
        if "extra_attrs" in item_patch:
            item.extra_attrs = merge_json_field(item.extra_attrs, item_patch["extra_attrs"])
        _touch(item)
        db.add(item)

    story_world_patch = state_patch.get("updated_story_world") or {}
    if isinstance(story_world_patch, dict) and story_world_patch:
        world = None
        if story_world_patch.get("id"):
            world = db.get(StoryWorld, story_world_patch["id"])
        elif story_world_patch.get("name"):
            world = db.exec(
                select(StoryWorld).where(StoryWorld.game_id == game_id, StoryWorld.name == story_world_patch["name"])
            ).first()
        if world:
            for key in [
                "name",
                "world_type",
                "summary",
                "current_status",
                "mission_objective",
                "completion_condition",
                "failure_condition",
            ]:
                if key in story_world_patch:
                    setattr(world, key, story_world_patch[key])
            if "plot_deviation" in story_world_patch:
                world.plot_deviation = _as_int(story_world_patch.get("plot_deviation"), world.plot_deviation)
            _touch(world)
            db.add(world)
        else:
            warnings.append("找不到 StoryWorld，未应用 updated_story_world。")

    db.commit()

    for update in state_patch.get("inventory_updates") or []:
        try:
            if not isinstance(update, dict):
                continue
            action = update.get("action")
            item = _find_item(db, game_id, update.get("item_name") or update.get("name"), update.get("item_id"))
            if not item:
                warnings.append(f"找不到物品，未应用库存更新: {update.get('item_name') or update.get('item_id')}")
                continue
            quantity = max(1, _as_int(update.get("quantity"), 1))
            owner_type, owner_id, owner_name = _owner_payload(db, game_id, update)
            if action in {"add", "gain", "obtain"}:
                _upsert_inventory_record(db, game_id, item.id, owner_type, owner_id, owner_name, quantity, update)
            elif action in {"remove", "lose", "lost", "consume"}:
                record = _find_inventory_record(db, game_id, item.id, owner_type, owner_id, owner_name)
                if not record:
                    warnings.append(f"找不到库存记录，未扣减: {item.name}")
                    continue
                record.quantity = max(0, record.quantity - quantity)
                if record.quantity == 0:
                    record.equipped = False
                    record.item_state = "consumed" if action == "consume" else "lost"
                _touch(record)
                db.add(record)
            elif action == "transfer":
                from_type, from_id, from_name = _owner_payload(db, game_id, update, "from_")
                to_type, to_id, to_name = _owner_payload(db, game_id, update, "to_")
                source = _find_inventory_record(db, game_id, item.id, from_type, from_id, from_name)
                if not source or source.quantity < quantity:
                    warnings.append(f"来源库存不足，未转移: {item.name}")
                    continue
                source.quantity -= quantity
                if source.quantity == 0:
                    source.equipped = False
                _touch(source)
                db.add(source)
                _upsert_inventory_record(db, game_id, item.id, to_type, to_id, to_name, quantity, update)
            elif action == "equip":
                record = _find_inventory_record(db, game_id, item.id, owner_type, owner_id, owner_name)
                if not record:
                    record = _upsert_inventory_record(db, game_id, item.id, owner_type, owner_id, owner_name, 1, update)
                record.equipped = True
                record.item_state = "equipped"
                _touch(record)
                db.add(record)
            elif action == "unequip":
                record = _find_inventory_record(db, game_id, item.id, owner_type, owner_id, owner_name)
                if record:
                    record.equipped = False
                    record.item_state = "normal"
                    _touch(record)
                    db.add(record)
            elif action == "set_state":
                record = _find_inventory_record(db, game_id, item.id, owner_type, owner_id, owner_name)
                if record:
                    if "quantity" in update:
                        record.quantity = max(0, _as_int(update.get("quantity"), record.quantity))
                    if update.get("item_state"):
                        record.item_state = update["item_state"]
                    if "equipped" in update:
                        record.equipped = _truthy(update.get("equipped"))
                    _touch(record)
                    db.add(record)
            else:
                warnings.append(f"暂未处理库存 patch action: {action}")
        except Exception as exc:
            warnings.append(f"库存更新失败: {exc}")

    db.commit()
    return {"ok": True, "warnings": warnings}
