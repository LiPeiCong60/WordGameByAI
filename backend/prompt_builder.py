from __future__ import annotations

import json
from typing import Any


def compact_context(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, default=str)


NARRATIVE_FORMAT_RULES = (
    "玩家行动是用户发给系统的推进指令，也是一种特殊旁白；不要把玩家行动原样照抄成旁白。"
    "玩家输入可能包含结构化字段：行动/背景/希望响应、主角台词、空白补全。"
    "行动/背景/希望响应用于表达玩家希望主角做什么、场景背景或希望剧情怎样响应；主角台词是主角真正说出口的话。"
    "如果主角台词为明确留空且空白补全关闭，主角本轮不主动说话。"
    "如果某个字段留空且空白补全开启，可以结合上下文补足必要动作或短对白，但不要过度替玩家做重大决定。"
    "剧情必须贴近主角视角，默认使用第二人称或主角名来推进。"
    "当玩家行动表达问话、寒暄、回复、表态、命令或任何对话意图时，必须先把它转译成主角对白，格式为 主角名：台词；如果主角名未知，用 你：台词。"
    "当玩家行动表达非语言动作时，必须把它转译成主角视角的行动描写。"
    "NPC 回答前通常应先出现主角行动或主角对白，不能只让 NPC 单方面说话。"
    "不要重复同一句对白，也不要让同一个 NPC 连续给出语义相同的回答。"
    "你生成的玩家可见剧情必须使用以下排版规则："
    "1. 角色行动、场景描写、环境描写、外貌/动作描写都单独成段，并用英文中括号 [] 包起来，例如：[主角推开窗，冷风灌进房间。]。"
    "2. 角色心理活动单独成段，并用英文小括号 () 包起来，例如：(他意识到自己不能再拖下去。)。"
    "3. 角色说话保持普通对白，格式为 角色名：台词，不加中括号，不加小括号，不加引号。"
    "4. 如果一段里既有动作又有说话，必须拆成两段：先写 [动作/描写]，再写 角色名：台词。"
    "5. 旁白或动作即使以角色名开头，也必须放进 []，例如：[周临的瞳孔骤然收缩。]，不能写成 周临的瞳孔骤然收缩。"
    "6. 不要使用项目符号、Markdown、解释文字或格式说明。"
)

STATE_HINT_INSTRUCTIONS = (
    "同时输出用户不可见的 state_hint，只用于即时同步角色软状态。"
    "state_hint 只允许包含 current_state_update 和 updated_characters。"
    "current_state_update 必须是简短自然语言字符串，不要输出对象或数组；如果时间、地点或场景阶段发生变化，必须写清楚，例如 当前时间:傍晚；当前位置:商场三楼蔚蓝女装店前；当前状况:林晚发来消息。"
    "updated_characters 每项必须指向已存在角色，使用 name 或 id；只允许字段 status, mood, relationship_to_player, "
    "relationship_score_delta, affection_score_delta, trust_score_delta, tension_score_delta, current_goal, current_location, memory_summary。"
    "如果剧情中角色移动、离开、抵达、打电话、发消息、等待过久、时间推进、气氛改变，必须同步更新相关角色的 current_location 和 mood；没有明确变化才保持不写。"
    "数值 delta 每轮必须在 -10 到 10 之间；不要生成任务结算或其他持久化系统字段。"
)

STATE_HINT_TAG_INSTRUCTIONS = (
    "正文结束后追加一段系统隐藏标签：<STATE_HINT>{...}</STATE_HINT>。"
    "标签内 JSON 遵守 state_hint 规则，只写 current_state_update 和 updated_characters。"
    "标签不会展示给玩家；不要使用 Markdown 或代码块。"
)

RELATION_METRIC_RULES = (
    "角色关系数值含义：relationship_to_player 是关系标签；relationship_score 表示外在立场/合作程度，可为负数，负数代表敌对或疏远；"
    "affection_score 是好感度，表示喜欢、在意、心软、偏爱；trust_score 是信任度，表示是否相信主角、是否愿意托付秘密或承担风险；"
    "tension_score 是情绪张力，表示暧昧、执念、压迫感、对抗吸引或危险拉扯。"
    "这些数值可以互相矛盾，不要强行统一。例如可以出现 relationship_to_player=仇人、relationship_score=-80、affection_score=90、trust_score=15、tension_score=95。"
)

TIME_AND_CONTACT_RULES = (
    "时间是剧情判断因素：必须参考当前状态中的时间、最近回合的时间推进、题材作息和场景营业/上课/通勤/夜间等常识。"
    "NPC 不一定只能同场景出现；如果 NPC 的 current_goal、关系/好感/信任/张力、最近记忆或时间点让他有动机，可以通过电话、短信、社交软件、广播、托人传话、门外等待等方式主动联系主角。"
    "主动联系必须有合理触发原因，例如到了约定时间、担心主角、吃醋、任务催促、发现线索、情绪绷不住、距离虽远但可以通讯。"
    "不要让所有 NPC 都主动联系；每轮最多选择少数最相关角色。若时间太晚、角色忙碌、关系不足或没有动机，应保持沉默。"
)


def build_protagonist_messages(context: dict[str, Any], user_input: str) -> list[dict[str, str]]:
    protagonist = context.get("protagonist") or {}
    protagonist_name = protagonist.get("name") or "你"
    return [
        {
            "role": "system",
            "content": (
                "你是 ProtagonistAgent，专门扮演玩家当前存档里的主角。"
                "你只负责把玩家输入的推进指令，转译成主角在游戏世界中真正做出的行为、说出的话和内心反应。"
                "你不是旁白总控，也不能替 NPC 回答。必须符合主角的人设、状态、心情、位置、能力和当前目标。"
                "如果游戏上下文包含 retrieved_memories，它们是本轮检索到的相关长期记忆和世界观，应优先用于保持连续性。"
                "如果玩家输入包含结构化字段，要优先遵守：行动/背景/希望响应决定动作和场景意图，主角台词决定主角说出口的话。"
                "当主角台词字段有内容时，必须原意保留为主角对白，不要改成旁白；当主角台词明确留空且空白补全关闭时，不要生成主角对白。"
                "当行动字段留空且空白补全开启时，可以根据当前上下文补一个轻量自然动作；空白补全关闭时不要擅自添加强动作。"
                "如果玩家输入像问话、寒暄、回应、表态、命令、请求或直接说一句话，你必须生成主角对白。"
                f"主角对白格式必须是 {protagonist_name}：台词。"
                "如果玩家输入是动作，就生成主角行动描写。"
                "如果玩家输入同时包含动作和话语，必须拆成行动段和对白段。"
                f"{NARRATIVE_FORMAT_RULES}"
                "只输出 JSON: {\"visible_story\":\"...\", \"intent_summary\":\"...\"}。"
                "visible_story 只写主角自己的行为、对白、心理，不写 NPC 反应，不写结果总结。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"游戏上下文:\n{compact_context(context)}\n\n"
                f"玩家推进指令:{user_input}\n\n"
                "请生成主角智能体输出。"
            ),
        },
    ]


def build_npc_reaction_messages(
    context: dict[str, Any], user_input: str, protagonist_turn: dict[str, Any] | None = None
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是 NPC 行为推演器。你不是旁白。你只判断重要 NPC 在当前场景下会怎么想、怎么做、想表达什么。"
                "NPC 必须符合自己的性格、心情、关系、能力、目标和题材设定。"
                f"{RELATION_METRIC_RULES}"
                "NPC 反应要同时参考立场、好感、信任和张力：立场决定行为边界，好感决定是否心软和偏爱，信任决定是否相信主角，张力决定暧昧或拉扯强度。"
                f"{TIME_AND_CONTACT_RULES}"
                "如果游戏上下文包含 retrieved_memories，它们是本轮检索到的相关长期记忆和世界观，应优先用于判断 NPC 是否应该记得旧事。"
                "你必须基于 ProtagonistAgent 已经生成的主角行为/对白来反应，而不是直接对玩家原始指令反应。"
                "不要让所有启用子 Agent 的 NPC 都默认出场。必须先结合当前地点、角色当前位置、最近剧情、用户行动、主角输出和当前状态判断哪些 NPC 自然在场、会抵达、会通讯或需要反应。"
                "如果没有 NPC 应该自然出现或反应，reactions 必须返回空数组，不能硬安排 NPC 出场。"
                "如果某个 NPC 不在当前场景且没有合理抵达/通讯理由，不要输出该 NPC 的反应。"
                "输出 JSON，字段包含 reactions、selected_npcs、omitted_npcs、selection_reason。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"游戏上下文:\n{compact_context(context)}\n\n"
                f"玩家原始指令:{user_input}\n\n"
                f"ProtagonistAgent 输出:\n{json.dumps(protagonist_turn or {}, ensure_ascii=False)}"
            ),
        },
    ]


def build_narrator_messages(
    context: dict[str, Any],
    user_input: str,
    protagonist_turn: dict[str, Any],
    npc_reactions: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是一个长篇 AI 文字 RPG 游戏主持人。必须保持世界观连续、角色性格稳定、文风和叙事视角一致。"
                f"{RELATION_METRIC_RULES}"
                "如果游戏上下文包含 retrieved_memories，它们是本轮检索到的相关长期记忆和世界观，必须用于保持剧情连续，不能与其冲突。"
                "不得推翻 hard_canon 设定，不得让角色凭空获得能力或关键情报。"
                "根据 Game.genre、world_type、tone 判断题材，不要写串。当前核心玩法聚焦人物关系、情绪变化和世界状态。"
                f"{TIME_AND_CONTACT_RULES}"
                "NPCReactionAgent 可能返回空反应，这表示当前没有 NPC 需要自然出场；不要为了热闹而强行安排 NPC 出现。"
                "即使 NPCReactionAgent 返回空反应，旁白也可以基于时间、目标、关系和记忆安排最相关 NPC 主动联系主角，但必须有合理原因。"
                "ProtagonistAgent 的主角输出会由系统放在正文开头，你不要重复它。"
                "你只需要接着写 NPC、环境和后续反馈；如果后续主角需要继续说话，也必须使用主角名对白格式。"
                f"{NARRATIVE_FORMAT_RULES}"
                f"{STATE_HINT_INSTRUCTIONS}"
                "输出必须是 JSON: {\"visible_story\":\"...\",\"state_hint\":{\"current_state_update\":\"...\",\"updated_characters\":[]}}，visible_story 字符串内也必须遵守上述排版规则。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"游戏上下文:\n{compact_context(context)}\n\n"
                f"玩家原始指令:{user_input}\n\n"
                f"ProtagonistAgent 输出，已作为正文开头，禁止重复:\n{json.dumps(protagonist_turn, ensure_ascii=False)}\n\n"
                f"NPCReactionAgent 输出:\n{json.dumps(npc_reactions, ensure_ascii=False)}"
            ),
        },
    ]


def build_narrator_stream_messages(
    context: dict[str, Any],
    user_input: str,
    protagonist_turn: dict[str, Any],
    npc_reactions: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是一个长篇 AI 文字 RPG 游戏主持人。必须保持世界观连续、角色性格稳定、文风和叙事视角一致。"
                f"{RELATION_METRIC_RULES}"
                "如果游戏上下文包含 retrieved_memories，它们是本轮检索到的相关长期记忆和世界观，必须用于保持剧情连续，不能与其冲突。"
                "不得推翻 hard_canon 设定，不得让角色凭空获得能力或关键情报。"
                "根据 Game.genre、world_type、tone 判断题材，不要写串。当前核心玩法聚焦人物关系、情绪变化和世界状态。"
                f"{TIME_AND_CONTACT_RULES}"
                "NPCReactionAgent 可能返回空反应，这表示当前没有 NPC 需要自然出场；不要为了热闹而强行安排 NPC 出现。"
                "即使 NPCReactionAgent 返回空反应，旁白也可以基于时间、目标、关系和记忆安排最相关 NPC 主动联系主角，但必须有合理原因。"
                "ProtagonistAgent 的主角输出会由系统放在正文开头，你不要重复它。"
                "你只需要接着写 NPC、环境和后续反馈；如果后续主角需要继续说话，也必须使用主角名对白格式。"
                f"{NARRATIVE_FORMAT_RULES}"
                f"{STATE_HINT_INSTRUCTIONS}"
                f"{STATE_HINT_TAG_INSTRUCTIONS}"
                "除最后隐藏标签外，前面的内容必须是玩家可见剧情正文，不要解释。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"游戏上下文:\n{compact_context(context)}\n\n"
                f"玩家原始指令:{user_input}\n\n"
                f"ProtagonistAgent 输出，已作为正文开头，禁止重复:\n{json.dumps(protagonist_turn, ensure_ascii=False)}\n\n"
                f"NPCReactionAgent 输出:\n{json.dumps(npc_reactions, ensure_ascii=False)}"
            ),
        },
    ]


def build_opening_messages(context: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是 NarrativeAgent 的开场主持人。你只负责为一个还没有任何剧情回合的新存档生成开场白。"
                "如果游戏上下文包含 retrieved_memories，它们是本轮检索到的相关世界观、角色记忆和历史剧情，应作为开场连续性的参考。"
                "必须结合当前存档的 title、genre、world_type、tone、style_guide、rules_summary，以及 templates 中最匹配的模板。"
                "模板匹配优先级：模板 name/genre/world_type 与当前存档 genre/world_type/title 相符；如果没有完全匹配，就使用最接近的题材规则。"
                "开场必须从主角视角切入，给出时间、地点、当前处境、主角正在做什么，以及一个自然可行动的开局钩子。"
                f"{TIME_AND_CONTACT_RULES}"
                "可以让重要 NPC 出现，但必须结合角色当前位置、关系和题材逻辑；不要为了热闹强行让所有 NPC 出场。"
                "不要写系统说明、玩法提示、选项列表或 Markdown。不要出现“玩家指令”。"
                f"{NARRATIVE_FORMAT_RULES}"
                "只输出 JSON: {\"visible_story\":\"...\"}。"
            ),
        },
        {
            "role": "user",
            "content": f"当前新存档上下文:\n{compact_context(context)}\n\n请生成第一段开场白。",
        },
    ]


def build_opening_stream_messages(context: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是 NarrativeAgent 的开场主持人。你只负责为一个还没有任何剧情回合的新存档生成开场白。"
                "如果游戏上下文包含 retrieved_memories，它们是本轮检索到的相关世界观、角色记忆和历史剧情，应作为开场连续性的参考。"
                "必须结合当前存档的 title、genre、world_type、tone、style_guide、rules_summary，以及 templates 中最匹配的模板。"
                "模板匹配优先级：模板 name/genre/world_type 与当前存档 genre/world_type/title 相符；如果没有完全匹配，就使用最接近的题材规则。"
                "开场必须从主角视角切入，给出时间、地点、当前处境、主角正在做什么，以及一个自然可行动的开局钩子。"
                f"{TIME_AND_CONTACT_RULES}"
                "可以让重要 NPC 出现，但必须结合角色当前位置、关系和题材逻辑；不要为了热闹强行让所有 NPC 出场。"
                "不要写系统说明、玩法提示、选项列表或 Markdown。不要出现“玩家指令”。"
                f"{NARRATIVE_FORMAT_RULES}"
                "直接输出玩家可见剧情正文，不要 JSON，不要解释。"
            ),
        },
        {
            "role": "user",
            "content": f"当前新存档上下文:\n{compact_context(context)}\n\n请生成第一段开场白。",
        },
    ]


def build_patch_messages(
    context: dict[str, Any], user_input: str, npc_reactions: dict[str, Any], visible_story: str
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是状态变化提取器。你不能写剧情。只能从玩家输入、NPC 反应、剧情正文中提取明确发生的状态变化。"
                "不要编造未发生的变化。当前项目以人物关系、情绪变化、目标、位置和世界状态为核心。"
                "时间变化也属于世界状态：如果剧情明确推进到新时间段、等待了一段时间、进入夜晚/清晨/课间/下班后等，应写入 current_state_update。"
                "你还要判断新出现的人物是否应该进入可管理角色表。"
                "重要 NPC 判定：有明确姓名或独立身份、会反复出场、与主角存在关系/目标/冲突、掌握关键情报、对剧情有持续影响。"
                f"{RELATION_METRIC_RULES}"
                "重要 NPC 放入 new_characters，字段包括 name, role_type, gender, age, race_or_identity, appearance, personality, speech_style, abilities, current_location, status, mood, relationship_to_player, relationship_score, affection_score, trust_score, tension_score, current_goal, hidden_goal, memory_summary, agent_enabled, importance, management_reason, extra_attrs。"
                "已存在角色发生明确情绪、关系、位置、目标或通讯状态变化时，放入 updated_characters，可更新 name/id, status, mood, relationship_to_player, relationship_score, affection_score, trust_score, tension_score, current_goal, current_location, memory_summary, extra_attrs。"
                "agent_enabled 默认 true；如果只是可管理但不需要单独子智能体，可设 false。"
                "背景角色/群体判定：路人、一群军人、猎户们、店员、守卫、围观者、无名群众、一次性功能角色。"
                "背景角色/群体不要放入 new_characters；它们只保留在剧情正文和回合记忆里。"
                "不要生成任务结算或其他持久化系统字段。"
                "只输出 JSON，必须包含这些顶层字段：current_state_update, new_characters, updated_characters, updated_story_world, player_choices。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"已有存档:\n{compact_context(context)}\n\n玩家行动:{user_input}\n\n"
                f"NPC 反应:{json.dumps(npc_reactions, ensure_ascii=False)}\n\n剧情正文:{visible_story}"
            ),
        },
    ]


def build_checker_messages(context: dict[str, Any], visible_story: str, state_patch: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是一致性检查器。检查剧情和 state_patch 是否违反已有存档，重点检查人物关系、心情、目标、位置、世界状态是否自洽。"
                "state_patch 只应包含角色、世界和玩家选项相关字段。只输出 JSON。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"已有存档:\n{compact_context(context)}\n\n剧情正文:{visible_story}\n\n"
                f"state_patch:{json.dumps(state_patch, ensure_ascii=False)}"
            ),
        },
    ]


def build_lore_messages(text: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "你是世界观资料整理器。把用户输入的自然语言设定整理成 WorldLore JSON。不能擅自扩写太多。"
                "不自动保存，只返回整理结果。输出字段: title, category, content, canon_level, importance。"
            ),
        },
        {"role": "user", "content": text},
    ]


def build_management_messages(context: dict[str, Any], message: str, scope: str = "") -> list[dict[str, str]]:
    scope_text = scope or "综合管理"
    return [
        {
            "role": "system",
            "content": (
                "你是 NarrativeAgent 的存档管理智能体，不负责剧情生成。你只帮助用户讨论和修改当前存档及其下属数据。"
                "你可以读取当前上下文，解释修改建议，并输出 proposed_actions。你不能直接修改数据库，不能生成任意 SQL，"
                "只能生成白名单 action。所有修改必须等待用户确认后由后端执行。输出 JSON。"
                "你需要先和用户讨论需求；如果信息不足，reply 里先提出问题，proposed_actions 为空。"
                "当用户意图明确时，输出 proposed_actions。"
                "proposed_actions 必须是 JSON 数组，不要把数组或 action 对象再编码成字符串。"
                "每个 action 必须使用 {\"action\": \"create_template\", \"fields\": {...}} 这种结构；字段放在 fields 内，不要使用 params。"
                "白名单 action 包括 update_game, create/update/delete_story_world, create/update/delete_lore, "
                "create/update/delete_character, create/update/delete_template。"
                "创建/更新/删除必须使用对应模型允许字段，不要输出未列字段，不要输出 SQL。"
                f"{RELATION_METRIC_RULES}"
                "如果 scope 是 存档，优先使用 update_game 修改当前存档的标题、题材、世界类型、基调、叙事视角、文风规则、世界规则摘要和当前状态。"
                "如果 scope 是 模板，只能输出 create_template、update_template、delete_template，不要输出任何存档内 action。"
                "模板是存档的类，存档是模板实例化后的对象；修改模板不会自动修改已创建存档，只影响后续用模板创建的新存档。"
                "如果用户请求里包含 current_template_id，说明正在编辑已有模板；除非用户明确要求新建模板，否则必须使用 update_template，并把 target_id 设为 current_template_id。"
                "模板 action 的字段只能包含 name, genre, world_type, tone, description, default_style_guide, default_rules, default_character_fields。"
                "default_character_fields 可以是对象或数组，后端会保存为 JSON 字符串。"
                "你可以结合 recent_turns、characters 和 current_story_world 判断当前剧情里哪个 NPC 自然出现、哪个 NPC 不该出现；如果用户要求安排 NPC 出场，优先通过角色位置、目标或当前状态来表达，不要强迫所有 NPC 同时出现。"
                "如果当前板块 scope 不是综合管理，优先只处理该板块相关数据；确实需要跨板块时，在 reply 里说明原因。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"当前板块 scope:{scope_text}\n\n"
                f"游戏上下文:\n{compact_context(context)}\n\n用户请求:{message}"
            ),
        },
    ]
