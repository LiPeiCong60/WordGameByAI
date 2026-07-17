from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from json_utils import safe_json_loads
from auth_service import _sha256, issue_token, refresh_user_session, revoke_user_session
from management_service import apply_management_proposal
from models import AuthToken, Game, ManagementProposal, TurnLog, User, WorldLore
from prompt_builder import compact_context
from routers.mobile import list_game_turns
from story_quality_service import analyze_story_quality
from turn_concurrency_service import acquire_game_turn_lease, release_game_turn_lease


def make_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


class ProductionHardeningTests(unittest.TestCase):
    def test_compact_context_is_valid_prioritized_json_and_redacts_hidden_text(self) -> None:
        context = {
            "game": {"title": "测试"},
            "templates": [{"name": f"模板{i}", "default_character_fields": "x" * 5000} for i in range(20)],
            "retrieved_memories": [{"content": "雨夜约定；隐藏目标:不能告诉主角；仍然记得"}],
            "recent_turns": [{"ai_response": "上一轮"}],
        }
        text = compact_context(context, max_chars=1200, redact_hidden=True)
        payload = json.loads(text)
        self.assertEqual(payload["game"]["title"], "测试")
        self.assertIn("retrieved_memories", payload)
        self.assertNotIn("隐藏目标", text)
        self.assertNotIn("default_character_fields", text)

    def test_json_parser_repairs_code_fence_and_trailing_comma(self) -> None:
        parsed = safe_json_loads('```json\n{"ok": true, "items": [1,2,],}\n```')
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["items"], [1, 2])

    def test_management_actions_roll_back_as_one_transaction(self) -> None:
        with make_session() as db:
            game = Game(title="事务测试")
            user = User(username="admin", password_hash="x", is_admin=True)
            db.add(game)
            db.add(user)
            db.commit()
            db.refresh(game)
            db.refresh(user)
            proposal = ManagementProposal(
                game_id=game.id,
                session_id=1,
                user_request="先创建设定再更新不存在的世界",
                proposed_actions=json.dumps(
                    [
                        {"action": "create_lore", "fields": {"title": "不应保留", "content": "临时"}},
                        {"action": "update_story_world", "target_id": 99999, "fields": {"name": "失败"}},
                    ],
                    ensure_ascii=False,
                ),
                status="pending_confirmation",
            )
            db.add(proposal)
            db.commit()
            db.refresh(proposal)

            with self.assertRaises(HTTPException):
                apply_management_proposal(proposal.id, db, user)

            lore = db.exec(select(WorldLore).where(WorldLore.game_id == game.id)).all()
            self.assertEqual(lore, [])
            self.assertEqual(db.get(ManagementProposal, proposal.id).status, "failed")

    def test_game_turn_lease_blocks_parallel_generation(self) -> None:
        with make_session() as db:
            game = Game(title="并发测试")
            db.add(game)
            db.commit()
            db.refresh(game)
            acquire_game_turn_lease(db, game.id, "request-a")
            with self.assertRaises(HTTPException) as raised:
                acquire_game_turn_lease(db, game.id, "request-b")
            self.assertEqual(raised.exception.status_code, 409)
            release_game_turn_lease(db, game.id, "request-a")
            acquire_game_turn_lease(db, game.id, "request-b")
            release_game_turn_lease(db, game.id, "request-b")

    def test_mobile_turn_api_is_cursor_paginated(self) -> None:
        with make_session() as db:
            user = User(username="mobile", password_hash="x")
            db.add(user)
            db.commit()
            db.refresh(user)
            game = Game(title="移动端", owner_user_id=user.id)
            db.add(game)
            db.commit()
            db.refresh(game)
            for number in range(1, 5):
                db.add(TurnLog(game_id=game.id, turn_number=number, ai_response=f"第{number}轮"))
            db.commit()

            first = list_game_turns(game.id, 2, None, db, user)
            self.assertEqual([item["turn_number"] for item in first.items], [3, 4])
            self.assertTrue(first.has_more)
            second = list_game_turns(game.id, 2, first.next_cursor, db, user)
            self.assertEqual([item["turn_number"] for item in second.items], [1, 2])

    def test_story_quality_distinguishes_format_and_content(self) -> None:
        format_result = analyze_story_quality("这是没有格式的裸文本。\n还是裸文本。")
        self.assertEqual(format_result["likely_cause"], "format_or_parser")
        content_result = analyze_story_quality("[雨停了。]")
        self.assertEqual(content_result["likely_cause"], "prompt_context_or_model")

    def test_story_quality_detects_glued_dialogue_segments(self) -> None:
        result = analyze_story_quality(
            "[手机亮起。]许晚：刚洗完澡。许晚：空调坏了。[远处响起闷雷。]"
        )
        codes = {issue["code"] for issue in result["format_issues"]}
        self.assertIn("glued_segments", codes)
        self.assertEqual(result["likely_cause"], "format_or_parser")

    def test_refresh_rotation_and_logout_revoke_both_tokens(self) -> None:
        with make_session() as db:
            user = User(username="session-user", password_hash="x")
            db.add(user)
            db.commit()
            db.refresh(user)
            first = issue_token(db, user)
            second = refresh_user_session(db, first["refresh_token"])

            old_refresh = db.exec(
                select(AuthToken).where(AuthToken.token_hash == _sha256(first["refresh_token"]))
            ).one()
            self.assertTrue(old_refresh.revoked)

            revoke_user_session(db, second["token"], second["refresh_token"])
            active_hashes = {_sha256(second["token"]), _sha256(second["refresh_token"])}
            revoked = db.exec(select(AuthToken).where(AuthToken.token_hash.in_(active_hashes))).all()
            self.assertEqual(len(revoked), 2)
            self.assertTrue(all(token.revoked for token in revoked))


if __name__ == "__main__":
    unittest.main()
