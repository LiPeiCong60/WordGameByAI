from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

import crud
from database import get_session
from inventory_service import equip_item, get_inventory_for_owner, transfer_item, unequip_item, use_item
from models import Game, InventoryRecord
from schemas import EquipItemRequest, InventoryCreate, InventoryUpdate, TransferRequest, UseItemRequest

router = APIRouter()


@router.post("/games/{game_id}/inventory")
def create_inventory_record(game_id: int, payload: InventoryCreate, db: Session = Depends(get_session)):
    crud.get_or_404(db, Game, game_id, "游戏")
    return crud.create_record(db, InventoryRecord, payload, extra={"game_id": game_id})


@router.get("/games/{game_id}/inventory")
def list_inventory(game_id: int, db: Session = Depends(get_session)):
    return crud.list_by_game(db, InventoryRecord, game_id)


@router.get("/characters/{character_id}/inventory")
def list_character_inventory(character_id: int, db: Session = Depends(get_session)):
    return get_inventory_for_owner(db, 0, "character", owner_id=character_id) if False else [
        row for row in crud.list_records(db, InventoryRecord) if row.owner_type == "character" and row.owner_id == character_id
    ]


@router.get("/inventory/{record_id}")
def get_inventory_record(record_id: int, db: Session = Depends(get_session)):
    return crud.get_or_404(db, InventoryRecord, record_id, "库存记录")


@router.patch("/inventory/{record_id}")
def update_inventory_record(record_id: int, payload: InventoryUpdate, db: Session = Depends(get_session)):
    record = crud.get_or_404(db, InventoryRecord, record_id, "库存记录")
    return crud.update_record(db, record, payload)


@router.delete("/inventory/{record_id}")
def delete_inventory_record(record_id: int, db: Session = Depends(get_session)):
    record = crud.get_or_404(db, InventoryRecord, record_id, "库存记录")
    return crud.delete_record(db, record)


@router.post("/inventory/transfer")
def transfer_inventory(payload: TransferRequest, db: Session = Depends(get_session)):
    return transfer_item(
        db,
        payload.game_id,
        payload.item_id,
        payload.from_owner_name,
        payload.to_owner_name,
        payload.quantity,
        payload.from_owner_type,
        payload.from_owner_id,
        payload.to_owner_type,
        payload.to_owner_id,
    )


@router.post("/inventory/use")
def use_inventory_item(payload: UseItemRequest, db: Session = Depends(get_session)):
    return use_item(db, payload.game_id, payload.character_id, payload.item_id, payload.quantity, payload.context)


@router.post("/inventory/equip")
def equip_inventory_item(payload: EquipItemRequest, db: Session = Depends(get_session)):
    return equip_item(db, payload.game_id, payload.character_id, payload.item_id)


@router.post("/inventory/unequip")
def unequip_inventory_item(payload: EquipItemRequest, db: Session = Depends(get_session)):
    return unequip_item(db, payload.game_id, payload.character_id, payload.item_id)
