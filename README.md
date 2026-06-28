# NarrativeAgent Demo

NarrativeAgent Demo 是一个最小可运行的通用 AI 文字 RPG 引擎原型。它不是普通聊天机器人，而是围绕世界观、角色卡、物品库存、事件和多 Agent 剧情推进建立的结构化游戏 Demo。

项目说明书：[docs/项目说明书.md](docs/%E9%A1%B9%E7%9B%AE%E8%AF%B4%E6%98%8E%E4%B9%A6.md)

## 功能列表

- 自定义游戏题材、世界类型、文风、基础规则和当前状态。
- 内置都市恋爱、玄幻修真、丧尸末日、快穿任务、科幻远征、自定义空白模板。
- 管理 StoryWorld 世界 / 副本，快穿题材可创建多个副本。
- 管理 WorldLore 世界观条目，并可调用 LoreAgent 整理自然语言设定。
- 管理主角、NPC、反派、阵营代表角色卡，支持头像上传。
- 管理完整物品定义：装备、消耗品、关键道具、任务物品、资产、资源、载具、情报等。
- 使用统一 InventoryRecord 管理角色、队伍、地点、阵营、世界拥有的物品。
- 使用、装备、卸下、转移物品前强制检查数据库库存。
- 管理世界事件、关键事件、伏笔事件、关系事件等统一 WorldEvent。
- 通过 NPCReactionAgent、NarratorAgent、PatchAgent、CheckerAgent 推进一轮剧情。
- 保存 TurnLog、state_patch、checker_result，并在检查通过后应用状态变更。
- ManagementAgent 只在管理页面启用，先生成修改方案，用户确认后才写入数据库。
- 导入 / 导出完整存档 JSON。

## 技术栈

后端：Python、FastAPI、SQLite、SQLModel、Pydantic、LangChain、OpenAI-compatible API。

前端：Vue3、Vite、Vue Router、Pinia、Axios、lucide-vue-next、原生 CSS。

## 安装依赖

```bash
cd narrative-agent-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
```

## 配置 `.env`

```bash
cd narrative-agent-demo/backend
cp .env.example .env
```

可配置：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./narrative_agent.db
```

如果没有配置 API Key，系统不会崩溃。Agent 接口会返回友好错误：`LLM API key is not configured.`

项目通过 `langchain-openai` 的 `ChatOpenAI` 封装调用 OpenAI-compatible Chat Completions API，`OPENAI_BASE_URL` 可指向兼容 OpenAI 协议的模型服务。

## 安全与隐私

仓库只提交源码和公开配置模板。真实 `.env`、API Key、本地 SQLite 数据库、游戏存档、剧情回合记录、用户上传头像、虚拟环境、依赖目录和构建产物都不应提交。

公开配置请使用 `backend/.env.example`。本地运行时复制为 `backend/.env` 后再填入私有配置。

## 启动后端

```bash
cd narrative-agent-demo/backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000
```

接口文档：http://localhost:8000/docs

## 启动前端

```bash
cd narrative-agent-demo/frontend
npm run dev
```

前端默认访问：http://localhost:5173

如需修改 API 地址：

```bash
VITE_API_BASE_URL=http://localhost:8000/api npm run dev
```

## 创建游戏与模板

打开游戏页，选择世界观模板。模板会填入题材、世界类型、基调、默认文风和世界规则摘要，用户仍可手动修改。都市、玄幻、快穿等题材都可以独立创建游戏。

模板页可查看默认模板，也可新增、编辑、删除自定义模板。

## 世界 / 副本

在“世界”页新增 StoryWorld，填写世界类型、摘要、当前状态、任务目标、完成条件、失败条件和剧情偏移度。普通都市 / 玄幻游戏可只有一个 StoryWorld；快穿游戏可创建多个 StoryWorld，并用旗帜按钮设为当前世界。

## 世界观

在“设定”页新增 WorldLore，设置分类、canon_level、importance 和内容。LoreAgent 整理功能只返回 JSON，不自动保存；用户确认后再填入表单保存。

## 角色与头像

在“角色”页新增主角或 NPC。角色卡字段包括头像、姓名、角色类型、性别、年龄、身份 / 种族、外貌、性格、说话风格、能力、状态、心情、位置、与主角关系、关系值、目标、隐藏目标、记忆摘要、agent_enabled 和 extra_attrs JSON。

保存角色后可以上传头像。头像会保存到 `backend/uploads/characters/`，数据库保存 `avatar_url`，FastAPI 通过 `/uploads` 提供静态访问。

## 物品与库存

在“物品”页新增物品，设置 item_type、状态、稀有度、堆叠上限、可装备、可消耗、关键物品、可交易、唯一、使用条件、效果说明、位置、重要度和 extra_attrs。

物品定义只放在 Item 表。具体归属、数量、装备状态、存放位置和物品当前状态都放在 InventoryRecord 表。

可在“物品”页将物品分配给角色、队伍、地点、阵营或世界，也可在“库存”页直接创建库存记录。

## 使用、装备、卸下、转移物品

“库存”页的操作会调用后端 inventory_service：

- 主角或 NPC 没有库存记录时不能使用该物品。
- 数量不足时拒绝使用或转移。
- lost、broken、consumed 状态不能正常使用。
- 消耗品使用成功后扣数量。
- 非消耗品默认不减少数量。
- 关键物品默认不能普通消耗，除非 extra_attrs 或 usable_condition 明确允许。
- 装备物品前必须确认角色拥有该物品。
- 转移物品前必须确认来源拥有者有足够数量。

## 世界事件

在“事件”页新增 WorldEvent，设置事件类型、arc_name、related_world、摘要、地点、参与者、后果、状态、重要度和 extra_attrs。

## 剧情推进

在“进行”页输入玩家行动。后端执行：

1. 读取 Game、当前 StoryWorld、WorldLore、主角、NPC、Item、InventoryRecord、WorldEvent、最近 TurnLog。
2. 调用 NPCReactionAgent 推演 NPC 反应。
3. 调用 NarratorAgent 生成可见剧情。
4. 调用 PatchAgent 提取 state_patch。
5. 调用 CheckerAgent 检查连续性和库存合法性。
6. 检查通过则调用 PatchApplier 写入状态。
7. 保存 TurnLog 并返回剧情、NPC 反应、state_patch 和 checker_result。

第一版文本输入中的“我使用某物品”主要由 CheckerAgent 拦截；强校验使用请通过库存页的“使用”按钮。

## ManagementAgent

ManagementAgent 只在“管理”页工作，不参与普通剧情生成。它读取当前游戏上下文，和用户讨论要修改的世界观、角色、物品、库存、事件或当前状态，然后生成 proposed_actions。

修改方案会保存为 ManagementProposal，状态为 `pending_confirmation`。用户点击“确认执行”后，后端才会执行方案。执行时只允许白名单 action，禁止任意 SQL、删除数据库、绕过库存校验、绕过关键物品保护、修改 API Key 或系统配置。

支持的 action：

`update_game`、`create_story_world`、`update_story_world`、`create_lore`、`update_lore`、`create_character`、`update_character`、`create_item`、`update_item`、`create_inventory_record`、`update_inventory_record`、`transfer_item`、`use_item`、`equip_item`、`unequip_item`、`create_event`、`update_event`。

## 导入 / 导出存档

游戏页可导出完整 JSON，包含：

- game
- story_worlds
- world_lore
- characters
- items
- inventory_records
- world_events
- turn_logs
- management_sessions
- management_proposals

导入时会创建新的 Game，并重建世界、角色、物品和库存关系。

## 当前 Demo 限制

- Agent 是同步函数调用，没有队列、缓存或流式输出。
- 文本输入中的物品使用意图没有完整自然语言解析。
- CheckerAgent 依赖 LLM；没有 API Key 时只返回友好错误，不进行真实语义检查。
- 前端是 MVP 管理台，偏向完整数据管理而非最终游戏 UI。
- SQLite 适合本地 Demo，多用户并发需要替换数据库和权限系统。

## 后续扩展方向

- RAG 世界观检索。
- PostgreSQL / pgvector。
- 存档版本化和回档。
- 文风润色 Agent。
- 更强的规则引擎和一致性检查。
- 阵营 Agent、地点 Agent、任务 Agent。
- 文本输入前置意图解析和库存预校验。
- 流式剧情生成与长篇记忆压缩。
