from __future__ import annotations

import sys
import unittest
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import game_engine
from agents.protagonist_agent import run_protagonist_fallback
from models import Character, Game, RagMemory, TurnLog, WorldEvent, WorldLore
from patch_applier import apply_state_patch
from rag_service import retrieve_related_memories, store_turn_memory
from routers.rag import rebuild_game_rag, search_rag_memories
from schemas import RagSearchRequest, TurnRequest


def make_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def seed_game(db: Session) -> Game:
    game = Game(title="雨夜恋爱测试", genre="都市恋爱", world_type="现代都市", tone="细腻")
    db.add(game)
    db.commit()
    db.refresh(game)
    db.add(
        WorldLore(
            game_id=game.id,
            title="银月城约定",
            category="关系设定",
            content="许晚和主角曾在银月城的雨夜做过约定，之后不能假装忘记。",
            canon_level="hard_canon",
            importance=9,
        )
    )
    db.add(
        Character(
            game_id=game.id,
            name="程予安",
            role_type="protagonist",
            personality="温和但有主见",
            speech_style="自然，偶尔调侃",
            current_goal="修复和许晚的关系",
            agent_enabled=False,
        )
    )
    db.add(
        Character(
            game_id=game.id,
            name="许晚",
            role_type="npc",
            personality="敏感、独立，表面冷静但在意细节",
            speech_style="简洁直接",
            relationship_to_player="熟人",
            relationship_score=35,
            memory_summary="许晚记得银月城雨夜约定，也记得主角曾经失约。",
            agent_enabled=True,
        )
    )
    db.add(
        WorldEvent(
            game_id=game.id,
            title="雨夜误会",
            event_type="关系事件",
            summary="主角曾在雨夜迟到，许晚因此误会他不重视约定。",
            participants="程予安,许晚",
            importance=8,
        )
    )
    db.commit()
    return game


class DynamicRagTests(unittest.TestCase):
    def test_static_game_context_is_indexed_and_retrieved(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            items = retrieve_related_memories(game.id, "许晚还记得银月城雨夜约定吗", db, top_k=5)
            source_types = {item["source_type"] for item in items}

            self.assertIn("world_lore", source_types)
            self.assertIn("character", source_types)
            self.assertTrue(any("许晚" in item["content"] for item in items))

    def test_turn_memory_is_stored_after_story_progress(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            turn = TurnLog(game_id=game.id, turn_number=1, user_input="我向许晚解释雨夜迟到的原因。", ai_response="")
            db.add(turn)
            db.commit()
            db.refresh(turn)

            memory = store_turn_memory(
                game.id,
                turn,
                "许晚听完解释后，态度缓和。",
                {"reactions": [{"name": "许晚", "summary": "态度缓和"}]},
                {"current_state_update": "雨夜误会开始解除", "updated_characters": [{"name": "许晚", "relationship_score": 42}]},
                {"ok": True},
                db,
            )
            self.assertIsNotNone(memory)

            items = retrieve_related_memories(game.id, "误会解除 许晚 态度缓和", db, top_k=3)
            self.assertTrue(any(item["source_type"] == "turn_summary" for item in items))

    def test_game_engine_retrieves_before_agents_and_updates_after_turn(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            captured = {}

            original_protagonist = game_engine.run_protagonist_agent
            original_npc = game_engine.run_npc_reaction_agent
            original_narrator = game_engine.run_narrator_agent
            original_patch = game_engine.run_patch_agent
            original_checker = game_engine.run_checker_agent
            try:
                game_engine.run_protagonist_agent = lambda context, user_input: {
                    "visible_story": "程予安：你还记得银月城那个雨夜吗？",
                    "intent_summary": "询问旧约定",
                }
                game_engine.run_npc_reaction_agent = lambda context, user_input, protagonist_turn: {
                    "reactions": [{"name": "许晚", "summary": "想起雨夜约定"}]
                }

                def fake_narrator(context, user_input, protagonist_turn, npc_reactions):
                    captured["narrator_context"] = context
                    return {"visible_story": "许晚：我当然记得。"}

                game_engine.run_narrator_agent = fake_narrator
                game_engine.run_patch_agent = lambda context, user_input, npc_reactions, visible_story: {
                    "current_state_update": "许晚提起银月城雨夜约定",
                    "new_events": [],
                    "new_characters": [],
                    "ambient_characters": [],
                    "updated_characters": [{"name": "许晚", "relationship_score": 40}],
                    "new_items": [],
                    "updated_items": [],
                    "inventory_updates": [],
                    "updated_story_world": {},
                    "player_choices": [],
                }
                game_engine.run_checker_agent = lambda context, visible_story, state_patch: {"ok": True, "issues": []}

                result = game_engine.run_game_turn(game.id, "我问许晚是否还记得银月城雨夜约定", db)
            finally:
                game_engine.run_protagonist_agent = original_protagonist
                game_engine.run_npc_reaction_agent = original_npc
                game_engine.run_narrator_agent = original_narrator
                game_engine.run_patch_agent = original_patch
                game_engine.run_checker_agent = original_checker

            self.assertTrue(captured["narrator_context"]["retrieved_memories"])
            self.assertTrue(result["retrieved_memories"])
            self.assertIsNotNone(result["rag_memory_id"])
            stored = db.exec(select(RagMemory).where(RagMemory.game_id == game.id, RagMemory.source_type == "turn_summary")).all()
            self.assertEqual(len(stored), 1)

    def test_fast_mode_skips_front_loaded_agents(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            called = {"protagonist": 0, "npc": 0, "narrator": 0}

            original_protagonist = game_engine.run_protagonist_agent
            original_npc = game_engine.run_npc_reaction_agent
            original_narrator = game_engine.run_narrator_agent
            original_patch = game_engine.run_patch_agent
            original_checker = game_engine.run_checker_agent
            try:
                def fail_protagonist(context, user_input):
                    called["protagonist"] += 1
                    raise AssertionError("fast mode should not call ProtagonistAgent")

                def fail_npc(context, user_input, protagonist_turn):
                    called["npc"] += 1
                    raise AssertionError("fast mode should not call NPCReactionAgent")

                def fake_narrator(context, user_input, protagonist_turn, npc_reactions):
                    called["narrator"] += 1
                    return {"visible_story": "许晚：我当然记得。"}

                game_engine.run_protagonist_agent = fail_protagonist
                game_engine.run_npc_reaction_agent = fail_npc
                game_engine.run_narrator_agent = fake_narrator
                game_engine.run_patch_agent = lambda context, user_input, npc_reactions, visible_story: {
                    "current_state_update": "快速模式生成完成",
                    "new_events": [],
                    "new_characters": [],
                    "ambient_characters": [],
                    "updated_characters": [],
                    "new_items": [],
                    "updated_items": [],
                    "inventory_updates": [],
                    "updated_story_world": {},
                    "player_choices": [],
                }
                game_engine.run_checker_agent = lambda context, visible_story, state_patch: {"ok": True, "issues": []}

                result = game_engine.run_game_turn(game.id, "许晚还记得雨夜约定吗", db, fast_mode=True)
            finally:
                game_engine.run_protagonist_agent = original_protagonist
                game_engine.run_npc_reaction_agent = original_npc
                game_engine.run_narrator_agent = original_narrator
                game_engine.run_patch_agent = original_patch
                game_engine.run_checker_agent = original_checker

            self.assertEqual(called["protagonist"], 0)
            self.assertEqual(called["npc"], 0)
            self.assertEqual(called["narrator"], 1)
            self.assertTrue(result["fast_mode"])

    def test_structured_turn_request_keeps_action_and_dialogue_separate(self) -> None:
        payload = TurnRequest(
            user_input="旧输入",
            action_input="带杯热可可下楼，观察她的反应",
            dialogue_input="今天怎么想起我了，大忙人",
            auto_complete_blank=False,
        )

        text = payload.effective_user_input()

        self.assertIn("行动/背景/希望响应：带杯热可可下楼，观察她的反应", text)
        self.assertIn("主角台词：今天怎么想起我了，大忙人", text)
        self.assertIn("空白补全：关闭", text)
        self.assertNotIn("旧输入", text)

    def test_structured_fast_fallback_outputs_action_and_dialogue(self) -> None:
        context = {"protagonist": {"name": "程予安"}}
        user_input = TurnRequest(
            action_input="带杯热可可下楼",
            dialogue_input="今天怎么想起我了，大忙人",
            auto_complete_blank=False,
        ).effective_user_input()

        result = run_protagonist_fallback(context, user_input)

        self.assertIn("[程予安 带杯热可可下楼]", result["visible_story"])
        self.assertIn("程予安：今天怎么想起我了，大忙人", result["visible_story"])
        self.assertNotIn("玩家回合输入", result["visible_story"])

    def test_rag_router_rebuild_and_search(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            rebuild_result = rebuild_game_rag(game.id, db)
            self.assertTrue(rebuild_result["ok"])

            result = search_rag_memories(game.id, RagSearchRequest(query="许晚 雨夜 约定", top_k=4), db)
            self.assertTrue(result["items"])
            self.assertTrue(any("许晚" in item["content"] or "许晚" in item["title"] for item in result["items"]))

    def test_patch_applier_tolerates_semantic_numeric_values(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            result = apply_state_patch(
                game.id,
                {
                    "new_events": [
                        {
                            "title": "模型语义重要度",
                            "event_type": "agreement",
                            "summary": "模型把重要度写成 normal。",
                            "importance": "normal",
                        }
                    ],
                    "updated_characters": [{"name": "许晚", "relationship_score": "high"}],
                    "updated_story_world": {},
                },
                db,
            )

            self.assertTrue(result["ok"])
            event = db.exec(select(WorldEvent).where(WorldEvent.game_id == game.id, WorldEvent.title == "模型语义重要度")).first()
            character = db.exec(select(Character).where(Character.game_id == game.id, Character.name == "许晚")).first()
            self.assertEqual(event.importance, 5)
            self.assertEqual(character.relationship_score, 8)


if __name__ == "__main__":
    unittest.main()
