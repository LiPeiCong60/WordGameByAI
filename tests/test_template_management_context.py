from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from json_utils import parse_json_field
from management_service import (
    create_management_proposal,
    create_management_session,
    list_management_messages,
    load_management_history,
    run_management_chat,
)
from models import ManagementProposal, User
from prompt_builder import build_management_messages


def make_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def template_action(name: str = "潮汐心动") -> dict:
    return {
        "action": "create_template",
        "fields": {
            "name": name,
            "genre": "都市恋爱",
            "world_type": "现代滨海小城",
            "tone": "清新、细腻、慢热",
            "description": "围绕海边小城生活与重逢展开的恋爱故事。",
            "default_style_guide": "自然细腻，重视生活感和人物关系。",
            "default_rules": "现代现实背景，无超自然能力。",
            "default_character_fields": {
                "characters": [
                    {
                        "name": "林屿",
                        "role_type": "protagonist",
                        "gender": "自定义",
                        "age": "22",
                        "relationship_to_player": "自己",
                        "agent_enabled": False,
                    },
                    {
                        "name": "夏栀",
                        "role_type": "npc",
                        "gender": "女",
                        "age": "22",
                        "relationship_to_player": "旧识",
                        "agent_enabled": True,
                    },
                ]
            },
        },
    }


class TemplateManagementContextTests(unittest.TestCase):
    def _user(self, db: Session, username: str) -> User:
        user = User(username=username, password_hash="x")
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def test_clear_template_request_retries_as_executable_proposal(self) -> None:
        with make_session() as db:
            user = self._user(db, "template-owner")
            chat = create_management_session(0, db, "模板智能助手", user.id)
            calls: list[dict] = []

            def fake_agent(context, message, scope, history=None, *, force_action=False):
                calls.append(
                    {
                        "message": message,
                        "scope": scope,
                        "history": history,
                        "force_action": force_action,
                    }
                )
                if not force_action:
                    return {
                        "reply": "还需要名称、基调和角色信息。",
                        "proposed_actions": [],
                    }
                return {
                    "reply": "已自动补全滨海小城恋爱模板，请确认创建。",
                    "proposed_actions": [template_action()],
                }

            with patch("management_service.run_management_agent", side_effect=fake_agent):
                result = run_management_chat(
                    chat.id,
                    "我想生成一个滨海小城的恋爱模板。",
                    db,
                    "模板",
                    user,
                )

            self.assertEqual([item["force_action"] for item in calls], [False, True])
            self.assertTrue(result["requires_confirmation"])
            self.assertEqual(result["proposed_actions"][0]["action"], "create_template")
            encoded_characters = result["proposed_actions"][0]["fields"]["default_character_fields"]
            self.assertIsInstance(encoded_characters, str)
            self.assertEqual(len(parse_json_field(encoded_characters)["characters"]), 2)
            proposal = db.get(ManagementProposal, result["proposal_id"])
            self.assertEqual(proposal.status, "pending_confirmation")

    def test_auto_generate_follow_up_uses_only_current_session_history(self) -> None:
        with make_session() as db:
            user = self._user(db, "history-owner")
            current = create_management_session(0, db, "当前会话", user.id)
            other = create_management_session(0, db, "其他会话", user.id)
            create_management_proposal(
                0,
                current.id,
                user.id,
                "我想生成一个滨海小城的恋爱模板。",
                "我可以为你补全细节。",
                [],
                db,
            )
            create_management_proposal(
                0,
                other.id,
                user.id,
                "另一会话的秘密模板内容",
                "不得泄露",
                [],
                db,
            )

            def fake_agent(context, message, scope, history=None, *, force_action=False):
                self.assertEqual(message, "你帮我自动生成吧")
                self.assertEqual(len(history), 1)
                self.assertIn("滨海小城", history[0]["user_request"])
                self.assertNotIn("秘密", str(history))
                return {
                    "reply": "已继承上一轮要求并生成完整方案。",
                    "proposed_actions": [template_action("滨海心事")],
                }

            with patch("management_service.run_management_agent", side_effect=fake_agent):
                result = run_management_chat(
                    current.id,
                    "你帮我自动生成吧",
                    db,
                    "模板",
                    user,
                )

            self.assertTrue(result["requires_confirmation"])
            history = load_management_history(db, current.id)
            self.assertEqual([item["user_request"] for item in history], [
                "我想生成一个滨海小城的恋爱模板。",
                "你帮我自动生成吧",
            ])
            messages = list_management_messages(db, current.id)
            self.assertEqual(len(messages), 2)
            self.assertFalse(messages[0]["requires_confirmation"])
            self.assertTrue(messages[1]["requires_confirmation"])

    def test_current_template_context_retries_update_and_attaches_target(self) -> None:
        with make_session() as db:
            user = self._user(db, "editor-owner")
            chat = create_management_session(0, db, "编辑模板", user.id)
            request = (
                '【当前编辑上下文】\n{"current_template_id":37,"name":"旧模板"}'
                '\n\n【用户请求】\n让它变得更悬疑一点'
            )

            def fake_agent(context, message, scope, history=None, *, force_action=False):
                if not force_action:
                    return {"reply": "需要更多信息。", "proposed_actions": []}
                return {
                    "reply": "已增强悬疑线索。",
                    "proposed_actions": [
                        {
                            "action": "update_template",
                            "fields": {"tone": "悬疑、克制、层层反转"},
                        }
                    ],
                }

            with patch("management_service.run_management_agent", side_effect=fake_agent):
                result = run_management_chat(chat.id, request, db, "模板", user)

            action = result["proposed_actions"][0]
            self.assertEqual(action["action"], "update_template")
            self.assertEqual(action["target_id"], 37)
            self.assertEqual(list_management_messages(db, chat.id)[0]["user_request"], "让它变得更悬疑一点")

    def test_prompt_preserves_history_as_untrusted_role_messages(self) -> None:
        messages = build_management_messages(
            {"templates": [{"name": "都市恋爱"}]},
            "你帮我自动生成吧",
            "模板",
            history=[
                {
                    "user_request": "我想生成一个滨海小城的恋爱模板。",
                    "agent_response": "请补充细节。",
                    "proposed_actions": [],
                    "status": "draft",
                }
            ],
            force_action=True,
        )

        self.assertEqual([item["role"] for item in messages], ["system", "user", "assistant", "user"])
        self.assertIn("结构化修复重试", messages[0]["content"])
        self.assertIn("UNTRUSTED_PAST_USER_REQUEST", messages[1]["content"])
        self.assertIn("滨海小城", messages[1]["content"])
        self.assertIn("UNTRUSTED_PAST_ASSISTANT_RESPONSE", messages[2]["content"])
        self.assertIn("UNTRUSTED_USER_REQUEST", messages[-1]["content"])

    def test_history_is_bounded_to_recent_twelve_turns(self) -> None:
        with make_session() as db:
            user = self._user(db, "bounded-owner")
            chat = create_management_session(0, db, "长会话", user.id)
            for index in range(15):
                create_management_proposal(
                    0,
                    chat.id,
                    user.id,
                    f"第{index}轮 " + "海" * 100,
                    "回复 " + "风" * 100,
                    [],
                    db,
                )

            history = load_management_history(db, chat.id)
            self.assertEqual(len(history), 12)
            self.assertTrue(history[0]["user_request"].startswith("第3轮"))
            self.assertTrue(history[-1]["user_request"].startswith("第14轮"))
            self.assertLessEqual(len(str(history)), 24000)


if __name__ == "__main__":
    unittest.main()
