from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import game_engine
import message_quota_service
import routers.admin as admin_router
import routers.management as management_router
import routers.templates as templates_router
from database import DEFAULT_TEMPLATES, normalize_template_character_fields
from auth_service import _sha256, login_user, register_user
from agents.protagonist_agent import run_protagonist_fallback
from json_utils import parse_json_field
from models import CaptchaChallenge, Character, Game, MessageUsage, RagMemory, TurnLog, User, WorldLore, WorldTemplate
from patch_applier import apply_state_patch
from rag_service import retrieve_related_memories, store_turn_memory
from routers.rag import rebuild_game_rag, search_rag_memories
from schemas import ManagementChatRequest, ManagementSessionCreate, RagSearchRequest, TemplateCreate, TemplateUpdate, TurnRequest
from starter_character_service import CHARACTER_FIELDS
from turn_history_service import delete_turns_from
from message_quota_service import require_message_quota


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
    db.commit()
    return game


def test_user() -> User:
    return User(id=1, username="tester", is_admin=True)


class DynamicRagTests(unittest.TestCase):
    def test_register_first_user_with_captcha_becomes_admin_and_can_login(self) -> None:
        with make_session() as db:
            captcha = CaptchaChallenge(
                id="captcha-test",
                answer_hash=_sha256("12"),
                expires_at=datetime.utcnow() + timedelta(minutes=5),
            )
            db.add(captcha)
            db.commit()

            session = register_user(db, "admin_test", "password123", "admin@example.com", "captcha-test", "12")
            self.assertTrue(session["user"]["is_admin"])
            self.assertTrue(session["token"])

            login_session = login_user(db, "admin_test", "password123")
            self.assertEqual(login_session["user"]["username"], "admin_test")

    def test_login_requires_valid_captcha_when_provided(self) -> None:
        with make_session() as db:
            register_captcha = CaptchaChallenge(
                id="captcha-register",
                answer_hash=_sha256("12"),
                expires_at=datetime.utcnow() + timedelta(minutes=5),
            )
            login_captcha = CaptchaChallenge(
                id="captcha-login",
                answer_hash=_sha256("9"),
                expires_at=datetime.utcnow() + timedelta(minutes=5),
            )
            db.add(register_captcha)
            db.add(login_captcha)
            db.commit()

            register_user(db, "login_captcha_user", "password123", "", "captcha-register", "12")
            with self.assertRaises(Exception) as raised:
                login_user(db, "login_captcha_user", "password123", "captcha-login", "8")
            self.assertEqual(getattr(raised.exception, "status_code", None), 400)

    def test_template_management_routes_allow_global_admin_session(self) -> None:
        with make_session() as db:
            admin = test_user()
            created = management_router.create_session(0, ManagementSessionCreate(title="模板测试"), db, admin)
            self.assertEqual(created.game_id, 0)
            self.assertEqual(created.owner_user_id, admin.id)

            sessions = management_router.list_sessions(0, db, admin)
            self.assertEqual(len(sessions), 1)

            original_chat = management_router.run_management_chat
            try:
                management_router.run_management_chat = lambda session_id, message, db, scope, user: {
                    "reply": "模板方案已生成。",
                    "proposal_id": 1,
                    "proposed_actions": [],
                    "requires_confirmation": False,
                }
                result = management_router.chat(created.id, ManagementChatRequest(message="补全模板", scope="模板"), db, admin)
            finally:
                management_router.run_management_chat = original_chat

            self.assertEqual(result["reply"], "模板方案已生成。")

            normal_user = User(id=2, username="normal", is_admin=False)
            normal_session = management_router.create_session(0, ManagementSessionCreate(title="我的模板测试"), db, normal_user)
            self.assertEqual(normal_session.owner_user_id, normal_user.id)
            normal_sessions = management_router.list_sessions(0, db, normal_user)
            self.assertEqual([item.id for item in normal_sessions], [normal_session.id])

            other_user = User(id=3, username="other", is_admin=False)
            with self.assertRaises(Exception) as raised:
                management_router.get_session_record(normal_session.id, db, other_user)
            self.assertEqual(getattr(raised.exception, "status_code", None), 403)

    def test_templates_are_public_for_admin_and_private_for_normal_users(self) -> None:
        with make_session() as db:
            admin = test_user()
            normal = User(id=2, username="normal", is_admin=False)
            other = User(id=3, username="other", is_admin=False)

            public_template = templates_router.create_template(TemplateCreate(name="公共奇幻", genre="奇幻", is_public=True), db, admin)
            admin_private_template = templates_router.create_template(TemplateCreate(name="管理员私有", genre="管理", is_public=False), db, admin)
            own_template = templates_router.create_template(TemplateCreate(name="我的校园", genre="校园"), db, normal)
            other_template = templates_router.create_template(TemplateCreate(name="别人末日", genre="末日"), db, other)

            self.assertIsNone(public_template.owner_user_id)
            self.assertEqual(admin_private_template.owner_user_id, admin.id)
            self.assertEqual(own_template.owner_user_id, normal.id)
            self.assertEqual(other_template.owner_user_id, other.id)

            visible_names = {template.name for template in templates_router.list_templates(db, normal)}
            self.assertIn("公共奇幻", visible_names)
            self.assertIn("我的校园", visible_names)
            self.assertNotIn("别人末日", visible_names)

            with self.assertRaises(Exception) as raised:
                templates_router.update_template(public_template.id, TemplateUpdate(tone="暗黑"), db, normal)
            self.assertEqual(getattr(raised.exception, "status_code", None), 403)

            updated = templates_router.update_template(own_template.id, TemplateUpdate(tone="轻松"), db, normal)
            self.assertEqual(updated.tone, "轻松")
            made_private = templates_router.update_template(public_template.id, TemplateUpdate(is_public=False), db, admin)
            self.assertEqual(made_private.owner_user_id, admin.id)

    def test_message_quota_limits_normal_users_and_allows_member_override(self) -> None:
        old_short_limit = message_quota_service.RATE_LIMIT_MAX_REQUESTS
        message_quota_service.RATE_LIMIT_MAX_REQUESTS = 100
        message_quota_service._recent_requests.clear()
        try:
            with make_session() as db:
                normal = User(id=2, username="normal", is_admin=False, is_member=False, daily_message_limit=20)
                db.add(normal)
                db.commit()
                for _ in range(20):
                    require_message_quota(db, normal)
                with self.assertRaises(Exception) as raised:
                    require_message_quota(db, normal)
                self.assertEqual(getattr(raised.exception, "status_code", None), 429)
                usage = db.exec(select(MessageUsage).where(MessageUsage.user_id == normal.id)).one()
                self.assertEqual(usage.message_count, 20)

                member = User(id=3, username="member", is_member=True, daily_message_limit=25)
                db.add(member)
                db.commit()
                for _ in range(25):
                    require_message_quota(db, member)
                with self.assertRaises(Exception) as member_raised:
                    require_message_quota(db, member)
                self.assertEqual(getattr(member_raised.exception, "status_code", None), 429)

            admin = User(id=4, username="admin", is_admin=True, daily_message_limit=1)
            for _ in range(3):
                result = require_message_quota(db, admin)
                self.assertIsNone(result["limit"])
        finally:
            message_quota_service.RATE_LIMIT_MAX_REQUESTS = old_short_limit
            message_quota_service._recent_requests.clear()

    def test_admin_can_set_non_member_quota_below_default_and_member_quota_above_default(self) -> None:
        with make_session() as db:
            admin = User(id=1, username="admin", is_admin=True)
            normal = User(id=2, username="normal", is_member=False, daily_message_limit=20)
            db.add(admin)
            db.add(normal)
            db.commit()

            updated = admin_router.update_user(normal.id, admin_router.AdminUserUpdate(daily_message_limit=10), admin, db)
            self.assertFalse(updated["is_member"])
            self.assertEqual(updated["daily_message_limit"], 10)
            self.assertEqual(updated["effective_daily_message_limit"], 10)
            listed_after_quota = {item["id"]: item for item in admin_router.list_users(admin, db)}
            self.assertEqual(listed_after_quota[normal.id]["daily_message_limit"], 10)
            self.assertEqual(listed_after_quota[normal.id]["effective_daily_message_limit"], 10)

            upgraded = admin_router.update_user(
                normal.id,
                admin_router.AdminUserUpdate(is_member=True, daily_message_limit=30),
                admin,
                db,
            )
            self.assertTrue(upgraded["is_member"])
            self.assertEqual(upgraded["daily_message_limit"], 30)
            self.assertEqual(upgraded["effective_daily_message_limit"], 30)
            listed_after_member = {item["id"]: item for item in admin_router.list_users(admin, db)}
            self.assertTrue(listed_after_member[normal.id]["is_member"])
            self.assertEqual(listed_after_member[normal.id]["daily_message_limit"], 30)

    def test_default_templates_include_all_starter_character_fields(self) -> None:
        for template in DEFAULT_TEMPLATES:
            payload = parse_json_field(template["default_character_fields"], default={})
            characters = payload.get("characters", [])
            self.assertTrue(characters, template["name"])
            for character in characters:
                missing = CHARACTER_FIELDS - set(character)
                self.assertFalse(missing, f"{template['name']} / {character.get('name')} missing {sorted(missing)}")
                self.assertTrue(character.get("appearance"), f"{template['name']} / {character.get('name')} missing appearance text")

    def test_existing_templates_are_backfilled_with_missing_character_fields(self) -> None:
        with make_session() as db:
            template = WorldTemplate(
                name="缺字段模板",
                genre="测试",
                owner_user_id=2,
                default_character_fields='{"characters":[{"name":"林晚","role_type":"npc"}]}',
            )
            db.add(template)
            db.commit()

            normalize_template_character_fields(db)

            refreshed = db.get(WorldTemplate, template.id)
            payload = parse_json_field(refreshed.default_character_fields, default={})
            character = payload["characters"][0]
            missing = CHARACTER_FIELDS - set(character)
            self.assertFalse(missing)
            self.assertEqual(character["name"], "林晚")
            self.assertEqual(refreshed.owner_user_id, 2)

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
                    "new_characters": [],
                    "updated_characters": [{"name": "许晚", "relationship_score": 40}],
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
                    "new_characters": [],
                    "updated_characters": [],
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

    def test_skip_state_update_finishes_without_patch_and_checker(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            called = {"patch": 0, "checker": 0, "narrator": 0}

            original_narrator = game_engine.run_narrator_agent
            original_patch = game_engine.run_patch_agent
            original_checker = game_engine.run_checker_agent
            try:
                def fake_narrator(context, user_input, protagonist_turn, npc_reactions):
                    called["narrator"] += 1
                    return {
                        "visible_story": "许晚抬眼看你，语气比刚才轻了一点。",
                        "state_hint": {
                            "current_state_update": "当前时间:傍晚；当前位置:商场三楼蔚蓝女装店前；当前状况:许晚接过热可可，气氛稍微缓和。",
                            "updated_characters": [
                                {
                                    "name": "许晚",
                                    "mood": "稍微缓和",
                                    "current_location": "商场三楼蔚蓝女装店前",
                                    "affection_score_delta": 5,
                                    "trust_score_delta": 3,
                                }
                            ],
                        },
                    }

                def fail_patch(context, user_input, npc_reactions, visible_story):
                    called["patch"] += 1
                    raise AssertionError("skip_state_update should not call PatchAgent")

                def fail_checker(context, visible_story, state_patch):
                    called["checker"] += 1
                    raise AssertionError("skip_state_update should not call CheckerAgent")

                game_engine.run_narrator_agent = fake_narrator
                game_engine.run_patch_agent = fail_patch
                game_engine.run_checker_agent = fail_checker

                result = game_engine.run_game_turn(
                    game.id,
                    "我向许晚递过去一杯热可可",
                    db,
                    fast_mode=True,
                    skip_state_update=True,
                )
            finally:
                game_engine.run_narrator_agent = original_narrator
                game_engine.run_patch_agent = original_patch
                game_engine.run_checker_agent = original_checker

            self.assertEqual(called["narrator"], 1)
            self.assertEqual(called["patch"], 0)
            self.assertEqual(called["checker"], 0)
            self.assertTrue(result["fast_mode"])
            self.assertTrue(result["skip_state_update"])
            self.assertTrue(result["checker_result"]["skipped"])
            self.assertTrue(result["checker_result"]["state_hint_applied"])
            self.assertIn("当前时间:傍晚", result["state_patch"]["current_state_update"])
            self.assertEqual(result["state_patch"]["updated_characters"][0]["mood"], "稍微缓和")
            self.assertEqual(result["state_patch"]["updated_characters"][0]["current_location"], "商场三楼蔚蓝女装店前")
            refreshed_npc = db.exec(select(Character).where(Character.game_id == game.id, Character.name == "许晚")).one()
            self.assertEqual(refreshed_npc.mood, "稍微缓和")
            self.assertEqual(refreshed_npc.current_location, "商场三楼蔚蓝女装店前")
            self.assertEqual(refreshed_npc.affection_score, 5)
            self.assertEqual(refreshed_npc.trust_score, 3)
            refreshed_game = db.get(Game, game.id)
            self.assertIn("当前时间:傍晚", refreshed_game.current_state)
            self.assertEqual(len(db.exec(select(TurnLog).where(TurnLog.game_id == game.id)).all()), 1)

    def test_async_state_update_returns_pending_without_blocking_patch_and_checker(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            called = {"patch": 0, "checker": 0, "scheduled": 0}

            original_narrator = game_engine.run_narrator_agent
            original_patch = game_engine.run_patch_agent
            original_checker = game_engine.run_checker_agent
            original_schedule = game_engine._schedule_async_state_update
            try:
                game_engine.run_narrator_agent = lambda context, user_input, protagonist_turn, npc_reactions: {
                    "visible_story": "许晚接过热可可，没有立刻移开视线。"
                }

                def fail_patch(context, user_input, npc_reactions, visible_story):
                    called["patch"] += 1
                    raise AssertionError("async_state_update should not block on PatchAgent")

                def fail_checker(context, visible_story, state_patch):
                    called["checker"] += 1
                    raise AssertionError("async_state_update should not block on CheckerAgent")

                def fake_schedule(game_id, turn_id, context, user_input, npc_reactions, visible_story):
                    called["scheduled"] += 1

                game_engine.run_patch_agent = fail_patch
                game_engine.run_checker_agent = fail_checker
                game_engine._schedule_async_state_update = fake_schedule

                result = game_engine.run_game_turn(
                    game.id,
                    "我递给许晚一杯热可可",
                    db,
                    fast_mode=True,
                    async_state_update=True,
                )
            finally:
                game_engine.run_narrator_agent = original_narrator
                game_engine.run_patch_agent = original_patch
                game_engine.run_checker_agent = original_checker
                game_engine._schedule_async_state_update = original_schedule

            self.assertEqual(called["patch"], 0)
            self.assertEqual(called["checker"], 0)
            self.assertEqual(called["scheduled"], 1)
            self.assertTrue(result["async_state_update"])
            self.assertTrue(result["checker_result"]["pending"])

            turn = db.exec(select(TurnLog).where(TurnLog.game_id == game.id)).one()
            checker_result = parse_json_field(turn.checker_result, default={})
            self.assertTrue(checker_result["pending"])

    def test_state_hint_applies_soft_character_state_immediately(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            npc = db.exec(select(Character).where(Character.game_id == game.id, Character.name == "许晚")).one()
            npc.relationship_score = 35
            npc.affection_score = 50
            npc.trust_score = 20
            npc.tension_score = 30
            db.add(npc)
            db.commit()

            patch = game_engine._apply_state_hint(
                game.id,
                {
                    "updated_characters": [
                        {
                            "name": "许晚",
                            "mood": "稍微缓和",
                            "current_location": "校门口",
                            "relationship_score_delta": 99,
                            "affection_score_delta": 6,
                            "trust_score_delta": -99,
                            "tension_score_delta": 4,
                        }
                    ]
                },
                db,
            )

            refreshed_npc = db.exec(select(Character).where(Character.game_id == game.id, Character.name == "许晚")).one()
            self.assertEqual(refreshed_npc.mood, "稍微缓和")
            self.assertEqual(refreshed_npc.current_location, "校门口")
            self.assertEqual(refreshed_npc.relationship_score, 45)
            self.assertEqual(refreshed_npc.affection_score, 56)
            self.assertEqual(refreshed_npc.trust_score, 10)
            self.assertEqual(refreshed_npc.tension_score, 34)
            self.assertTrue(patch["state_hint"])
            self.assertEqual(patch["updated_characters"][0]["relationship_score"], 45)

    def test_stream_state_hint_tag_is_hidden_from_visible_story(self) -> None:
        hint_box = {}
        chunks = list(
            game_engine._iter_visible_chunks_with_hint(
                [
                    "许晚看着你，声音低了一点。",
                    "<STATE_HINT>{\"updated_characters\":[{\"name\":\"许晚\",\"affection_score_delta\":4}]}",
                    "</STATE_HINT>",
                ],
                hint_box,
            )
        )

        self.assertEqual("".join(chunks), "许晚看着你，声音低了一点。")
        self.assertEqual(hint_box["state_hint"]["updated_characters"][0]["name"], "许晚")

    def test_async_state_update_finalize_applies_real_patch(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            turn = TurnLog(
                game_id=game.id,
                turn_number=1,
                user_input="我认真道歉。",
                ai_response="许晚沉默片刻，终于点了点头。",
                npc_reactions="{}",
                state_patch="{}",
                checker_result='{"pending": true}',
            )
            db.add(turn)
            db.commit()
            db.refresh(turn)

            original_patch = game_engine.run_patch_agent
            original_checker = game_engine.run_checker_agent
            try:
                game_engine.run_patch_agent = lambda context, user_input, npc_reactions, visible_story: {
                    "current_state_update": "许晚开始重新考虑主角的解释",
                    "new_characters": [],
                    "updated_characters": [{"name": "许晚", "relationship_score": 45, "affection_score": 55}],
                    "updated_story_world": {},
                    "player_choices": [],
                }
                game_engine.run_checker_agent = lambda context, visible_story, state_patch: {"ok": True, "issues": []}

                result = game_engine._finalize_async_state_update(
                    game.id,
                    turn.id,
                    game_engine.load_game_context(game.id, db),
                    "我认真道歉。",
                    {"reactions": []},
                    "许晚沉默片刻，终于点了点头。",
                    db,
                )
            finally:
                game_engine.run_patch_agent = original_patch
                game_engine.run_checker_agent = original_checker

            self.assertIsNotNone(result)
            refreshed_turn = db.get(TurnLog, turn.id)
            checker_result = parse_json_field(refreshed_turn.checker_result, default={})
            self.assertFalse(checker_result["pending"])
            self.assertTrue(checker_result["async_state_update"])

            refreshed_npc = db.exec(select(Character).where(Character.game_id == game.id, Character.name == "许晚")).one()
            self.assertEqual(refreshed_npc.relationship_score, 45)
            self.assertEqual(refreshed_npc.affection_score, 55)

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
            user = test_user()
            rebuild_result = rebuild_game_rag(game.id, db, user)
            self.assertTrue(rebuild_result["ok"])

            result = search_rag_memories(game.id, RagSearchRequest(query="许晚 雨夜 约定", top_k=4), db, user)
            self.assertTrue(result["items"])
            self.assertTrue(any("许晚" in item["content"] or "许晚" in item["title"] for item in result["items"]))

    def test_patch_applier_tolerates_semantic_numeric_values(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            result = apply_state_patch(
                game.id,
                {
                    "updated_characters": [{"name": "许晚", "relationship_score": "high"}],
                    "updated_story_world": {},
                },
                db,
            )

            self.assertTrue(result["ok"])
            character = db.exec(select(Character).where(Character.game_id == game.id, Character.name == "许晚")).first()
            self.assertEqual(character.relationship_score, 8)

    def test_turn_actions_fallback_to_game_and_turn_number_when_id_is_stale(self) -> None:
        with make_session() as db:
            game = seed_game(db)
            first = TurnLog(game_id=game.id, turn_number=1, user_input="第一轮", ai_response="第一轮剧情")
            second = TurnLog(game_id=game.id, turn_number=2, user_input="第二轮", ai_response="第二轮剧情")
            db.add(first)
            db.add(second)
            db.commit()

            result = delete_turns_from(9999, db, game_id=game.id, turn_number=1)

            self.assertTrue(result["ok"])
            remaining = db.exec(select(TurnLog).where(TurnLog.game_id == game.id)).all()
            self.assertEqual(remaining, [])


if __name__ == "__main__":
    unittest.main()
