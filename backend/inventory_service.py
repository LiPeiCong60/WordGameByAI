from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from json_utils import parse_json_field
from models import Character, InventoryRecord, Item, WorldEvent

BAD_ITEM_STATES = {"lost", "broken", "consumed"}


def _touch(record) -> None:
    if hasattr(record, "updated_at"):
        record.updated_at = datetime.utcnow()


def _owner_filter(query, owner_type: str, owner_id: Optional[int] = None, owner_name: Optional[str] = None):
    query = query.where(InventoryRecord.owner_type == owner_type)
    if owner_id is not None:
        query = query.where(InventoryRecord.owner_id == owner_id)
    if owner_name:
        query = query.where(InventoryRecord.owner_name == owner_name)
    return query


def get_inventory_for_owner(
    db: Session, game_id: int, owner_type: str, owner_id: int | None = None, owner_name: str | None = None
) -> list[InventoryRecord]:
    query = select(InventoryRecord).where(InventoryRecord.game_id == game_id)
    return list(db.exec(_owner_filter(query, owner_type, owner_id, owner_name)).all())


def find_inventory_record(
    db: Session,
    game_id: int,
    owner_type: str,
    item_id: int,
    owner_id: int | None = None,
    owner_name: str | None = None,
) -> InventoryRecord | None:
    query = select(InventoryRecord).where(InventoryRecord.game_id == game_id, InventoryRecord.item_id == item_id)
    return db.exec(_owner_filter(query, owner_type, owner_id, owner_name)).first()


def check_owner_has_item(
    db: Session,
    game_id: int,
    owner_type: str,
    item_id: int,
    owner_id: int | None = None,
    owner_name: str | None = None,
    quantity: int = 1,
) -> tuple[bool, str | None, InventoryRecord | None]:
    record = find_inventory_record(db, game_id, owner_type, item_id, owner_id, owner_name)
    if not record:
        return False, "没有该物品的库存记录。", None
    if record.quantity <= 0:
        return False, "该物品库存数量为 0。", record
    if quantity > record.quantity:
        return False, f"库存不足，需要 {quantity}，当前只有 {record.quantity}。", record
    if record.item_state in BAD_ITEM_STATES:
        return False, f"物品状态为 {record.item_state}，无法使用。", record
    return True, None, record


def _get_character(db: Session, character_id: int) -> Character:
    character = db.get(Character, character_id)
    if not character:
        raise HTTPException(status_code=404, detail=f"找不到角色: {character_id}")
    return character


def _get_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"找不到物品: {item_id}")
    return item


def _key_item_allows_consume(item: Item) -> bool:
    extra = parse_json_field(item.extra_attrs, default={})
    return bool(extra.get("allow_consume") or "允许消耗" in (item.usable_condition or ""))


def use_item(
    db: Session, game_id: int, character_id: int, item_id: int, quantity: int = 1, context: str | None = None
) -> dict:
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="使用数量必须大于 0。")
    character = _get_character(db, character_id)
    if character.game_id != game_id:
        raise HTTPException(status_code=400, detail="角色不属于该游戏。")
    item = _get_item(db, item_id)
    if item.game_id != game_id:
        raise HTTPException(status_code=400, detail="物品不属于该游戏。")

    ok, message, record = check_owner_has_item(db, game_id, "character", item_id, owner_id=character_id, quantity=quantity)
    if not ok or record is None:
        raise HTTPException(status_code=400, detail=message or "角色没有该物品。")
    if item.status in BAD_ITEM_STATES:
        raise HTTPException(status_code=400, detail=f"物品全局状态为 {item.status}，无法使用。")
    if item.is_key_item and item.is_consumable and not _key_item_allows_consume(item):
        raise HTTPException(status_code=400, detail="关键物品不能被普通消耗。")
    if item.usable_condition and "不可使用" in item.usable_condition:
        raise HTTPException(status_code=400, detail="物品使用条件不满足。")

    if item.is_consumable:
        record.quantity -= quantity
        if record.quantity == 0:
            record.item_state = "consumed"
    _touch(record)

    event = WorldEvent(
        game_id=game_id,
        title=f"{character.name} 使用了 {item.name}",
        event_type="物品使用",
        summary=context or item.effect_description or f"{character.name} 使用了 {item.name}。",
        participants=character.name,
        importance=max(1, item.importance),
    )
    db.add(record)
    db.add(event)
    db.commit()
    db.refresh(record)
    return {"ok": True, "message": "使用成功。", "inventory_record": record, "event_id": event.id}


def transfer_item(
    db: Session,
    game_id: int,
    item_id: int,
    from_owner_name: str,
    to_owner_name: str,
    quantity: int = 1,
    from_owner_type: str = "character",
    from_owner_id: int | None = None,
    to_owner_type: str = "character",
    to_owner_id: int | None = None,
) -> dict:
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="转移数量必须大于 0。")
    item = _get_item(db, item_id)
    if item.game_id != game_id:
        raise HTTPException(status_code=400, detail="物品不属于该游戏。")
    if item.is_key_item and not item.is_tradeable:
        raise HTTPException(status_code=400, detail="该关键物品不可转移。")

    ok, message, source = check_owner_has_item(
        db, game_id, from_owner_type, item_id, owner_id=from_owner_id, owner_name=from_owner_name, quantity=quantity
    )
    if not ok or source is None:
        raise HTTPException(status_code=400, detail=message or "来源没有足够物品。")
    source.quantity -= quantity
    if source.quantity == 0:
        source.equipped = False
    _touch(source)

    target = find_inventory_record(db, game_id, to_owner_type, item_id, owner_id=to_owner_id, owner_name=to_owner_name)
    if target:
        target.quantity += quantity
        target.item_state = "normal" if target.item_state in BAD_ITEM_STATES else target.item_state
        _touch(target)
    else:
        target = InventoryRecord(
            game_id=game_id,
            item_id=item_id,
            owner_type=to_owner_type,
            owner_id=to_owner_id,
            owner_name=to_owner_name,
            quantity=quantity,
            item_state="normal",
        )
    db.add(source)
    db.add(target)
    db.commit()
    db.refresh(target)
    return {"ok": True, "message": "转移成功。", "from_record": source, "to_record": target}


def equip_item(db: Session, game_id: int, character_id: int, item_id: int) -> dict:
    character = _get_character(db, character_id)
    item = _get_item(db, item_id)
    if character.game_id != game_id or item.game_id != game_id:
        raise HTTPException(status_code=400, detail="角色或物品不属于该游戏。")
    if not item.is_equippable:
        raise HTTPException(status_code=400, detail="该物品不可装备。")
    ok, message, record = check_owner_has_item(db, game_id, "character", item_id, owner_id=character_id)
    if not ok or record is None:
        raise HTTPException(status_code=400, detail=message or "角色没有该物品。")
    record.equipped = True
    record.item_state = "equipped"
    _touch(record)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"ok": True, "message": "装备成功。", "inventory_record": record}


def unequip_item(db: Session, game_id: int, character_id: int, item_id: int) -> dict:
    character = _get_character(db, character_id)
    item = _get_item(db, item_id)
    if character.game_id != game_id or item.game_id != game_id:
        raise HTTPException(status_code=400, detail="角色或物品不属于该游戏。")
    ok, message, record = check_owner_has_item(db, game_id, "character", item_id, owner_id=character_id)
    if not ok or record is None:
        raise HTTPException(status_code=400, detail=message or "角色没有该物品。")
    record.equipped = False
    record.item_state = "normal"
    _touch(record)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"ok": True, "message": "卸下成功。", "inventory_record": record}
