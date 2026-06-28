# WordGameByAI

一个基于 FastAPI、Vue3 和 LangChain ChatOpenAI 的 AI 文字 RPG 应用框架，用结构化数据和多 Agent 叙事流水线管理长篇互动剧情。

[项目说明书](docs/项目说明书.md) | [安全说明](SECURITY.md)

## 项目简介

WordGameByAI 面向 AI 文字游戏、互动叙事 Demo 和 AI Agent 应用原型开发场景。项目尝试解决普通 LLM 聊天式文字游戏中常见的几个问题：世界观容易漂移、角色状态难以追踪、物品库存不一致、AI 生成的修改缺少安全边界。

项目把“剧情生成”拆成一套可管理的应用流程：前端提供存档、角色、物品、库存、世界观、事件和剧情推进界面；后端使用 FastAPI 提供 REST API 和流式剧情接口；数据库使用 SQLModel/SQLite 保存游戏状态；LLM 调用层基于 `langchain-openai` 的 `ChatOpenAI`，由多个职责明确的 Agent 模块完成主角行动理解、NPC 反应推演、剧情生成、状态补丁提取和一致性检查。

这不是一个单纯的聊天页面，而是一个围绕“AI 叙事 + 状态管理 + 数据安全写入”设计的 AI 应用框架。

## 项目亮点

- **LangChain 接入大模型**：通过 `langchain-openai` 的 `ChatOpenAI` 封装 OpenAI-compatible Chat Completions API，支持普通调用和流式输出。
- **多 Agent 角色分工流水线**：将主角行动、NPC 反应、旁白生成、状态补丁和一致性检查拆分为独立 Agent 模块，由 `game_engine.py` 统一编排。
- **结构化 Prompt 与 JSON 输出**：Agent Prompt 明确约束输出字段，使用 `response_format={"type": "json_object"}` 获取结构化结果，便于后端解析和落库。
- **完整的状态建模**：使用 SQLModel 建模 Game、StoryWorld、WorldLore、Character、Item、InventoryRecord、WorldEvent、TurnLog、TurnSnapshot 等核心实体。
- **FastAPI + Vue 前后端联调**：后端提供 REST/NDJSON 流式接口，前端使用 Axios 和 fetch stream 消费接口，支持剧情推进、管理台和数据编辑。
- **AI 写入安全控制**：ManagementAgent 只生成修改方案，用户确认后才执行；后端通过 action 白名单、字段白名单和库存强校验限制 AI 对数据的影响范围。

## 功能模块

| 模块 | 功能说明 |
| --- | --- |
| 存档管理 | 创建、编辑、删除、导入、导出游戏存档，维护题材、世界类型、文风规则和当前状态。 |
| 模板系统 | 内置都市恋爱、玄幻修真、丧尸末日、快穿任务、科幻远征和自定义空白模板，支持自定义模板管理。 |
| 世界/副本管理 | 维护 StoryWorld，支持任务目标、完成条件、失败条件、剧情偏移度和当前世界切换。 |
| 世界观管理 | 管理 WorldLore 条目，并通过 LoreAgent 将自然语言设定整理为结构化世界观数据。 |
| 角色系统 | 管理主角、NPC、反派、阵营代表等角色卡，支持头像上传和 `agent_enabled` 子 Agent 开关。 |
| 物品与库存 | 管理物品定义和 InventoryRecord，支持使用、装备、卸下、转移等强校验操作。 |
| 世界事件 | 维护背景事件、关键事件、伏笔事件、关系事件等 WorldEvent。 |
| 剧情推进 | 支持开场生成、玩家行动输入、流式剧情输出、回合记录、删除后续回合和重新生成。 |
| 管理 Agent | 通过自然语言生成存档修改方案，用户确认后执行白名单动作。 |
| 导入导出 | 导出完整存档 JSON，导入后重建游戏、角色、物品、库存、事件和回合记录。 |

## 技术栈

| 类别 | 技术 |
| --- | --- |
| 前端 | Vue 3、Vite、Vue Router、Pinia、Axios、lucide-vue-next、原生 CSS |
| 后端 | Python、FastAPI、SQLModel、Pydantic、Uvicorn |
| AI / 大模型 | LangChain、langchain-openai、ChatOpenAI、OpenAI-compatible API、结构化 JSON 输出 |
| 数据库 | SQLite，本地默认数据库文件为 `backend/narrative_agent.db` |
| 工程工具 | npm、Python venv、`.env` 配置、`.gitignore` 隐私排除、FastAPI Swagger 文档 |
| 运行环境 | 本地开发环境，后端默认 `localhost:8000`，前端默认 `localhost:5173` |

## 项目结构

```text
WordGameByAI/
├── backend/                         # FastAPI 后端服务
│   ├── agents/                      # 各类 Agent：主角、NPC、旁白、补丁、检查、管理、设定整理
│   ├── routers/                     # API 路由：games、characters、items、turns、management 等
│   ├── uploads/                     # 用户上传目录，实际文件默认不提交
│   ├── database.py                  # 数据库连接、表初始化、默认模板种子数据
│   ├── game_engine.py               # 剧情推进编排：加载上下文、调用 Agent、保存回合和快照
│   ├── inventory_service.py         # 库存使用、装备、卸下、转移的后端强校验
│   ├── llm_client.py                # LangChain ChatOpenAI 调用封装
│   ├── main.py                      # FastAPI 应用入口、CORS、静态文件、路由注册
│   ├── management_service.py        # ManagementAgent 方案确认、白名单动作执行
│   ├── models.py                    # SQLModel 数据模型
│   ├── prompt_builder.py            # Agent Prompt 构造与结构化输出约束
│   └── schemas.py                   # Pydantic 请求模型
├── frontend/                        # Vue3 前端
│   ├── src/
│   │   ├── api/                     # Axios/fetch API 封装
│   │   ├── components/              # 剧情日志、角色卡、库存面板、管理 Agent 面板等组件
│   │   ├── router/                  # 前端路由
│   │   ├── stores/                  # Pinia 状态管理
│   │   ├── styles/                  # 全局样式
│   │   ├── utils/                   # 标签、预设、初始角色等工具
│   │   └── views/                   # 存档、游戏、模板、角色、物品、库存、世界、事件等页面
│   ├── package.json                 # 前端依赖和脚本
│   └── vite.config.js               # Vite 配置
├── docs/
│   └── 项目说明书.md                 # 更完整的项目说明文档
├── .gitignore                       # 忽略密钥、数据库、上传文件、依赖和构建产物
├── SECURITY.md                      # 安全与隐私说明
├── requirements.txt                 # 后端依赖
└── README.md
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/LiPeiCong60/WordGameByAI.git
cd WordGameByAI
```

### 2. 安装后端依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填入自己的模型服务配置：

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./narrative_agent.db
```

如果不配置 API Key，系统仍可启动，但 Agent 调用会返回 `LLM API key is not configured.`。

### 4. 启动后端

```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000
```

后端地址：

- API 根路径：`http://localhost:8000/api`
- Swagger 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/health`

### 5. 启动前端

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：

```text
http://localhost:5173
```

如果需要修改后端 API 地址，可以在启动时指定：

```bash
VITE_API_BASE_URL=http://localhost:8000/api npm run dev
```

## 环境变量说明

后端环境变量位于 `backend/.env`，仓库只提交 `backend/.env.example`。

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./narrative_agent.db
```

| 变量 | 说明 | 是否必填 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 大模型 API Key。真实密钥只放本地 `.env`，不要提交到 Git。 | 调用 Agent 时必填 |
| `OPENAI_BASE_URL` | OpenAI-compatible API 地址，可接入兼容 OpenAI 协议的模型服务。 | 否，默认 OpenAI API |
| `OPENAI_MODEL` | 使用的模型名称。 | 否，默认 `gpt-4o-mini` |
| `DATABASE_URL` | SQLModel 数据库连接地址。 | 否，默认本地 SQLite |
| `VITE_API_BASE_URL` | 前端 API 地址，运行前端时可通过环境变量传入。 | 否，默认 `http://localhost:8000/api` |

## API 接口说明

以下列出主要接口，完整参数和响应可在启动后端后访问 `http://localhost:8000/docs` 查看。

| 方法 | 路径 | 功能说明 | 请求参数简述 |
| --- | --- | --- | --- |
| `GET` | `/api/health` | 健康检查 | 无 |
| `POST` | `/api/games` | 创建游戏存档 | Body: `GameCreate`，可传 `template_id` |
| `GET` | `/api/games` | 获取存档列表 | 无 |
| `GET` | `/api/games/{game_id}` | 获取单个存档 | Path: `game_id` |
| `PATCH` | `/api/games/{game_id}` | 更新存档信息 | Path: `game_id`，Body: `GameUpdate` |
| `DELETE` | `/api/games/{game_id}` | 删除存档及关联数据 | Path: `game_id` |
| `GET` | `/api/templates` | 获取模板列表 | 无 |
| `POST` | `/api/templates` | 创建模板 | Body: `TemplateCreate` |
| `PATCH` | `/api/templates/{template_id}` | 更新模板 | Path: `template_id`，Body: `TemplateUpdate` |
| `DELETE` | `/api/templates/{template_id}` | 删除模板 | Path: `template_id` |
| `POST` | `/api/games/{game_id}/story-worlds` | 创建世界/副本 | Path: `game_id`，Body: `StoryWorldCreate` |
| `GET` | `/api/games/{game_id}/story-worlds` | 获取世界/副本列表 | Path: `game_id` |
| `POST` | `/api/games/{game_id}/story-worlds/{world_id}/set-current` | 设置当前世界 | Path: `game_id`, `world_id` |
| `POST` | `/api/games/{game_id}/lore` | 创建世界观条目 | Path: `game_id`，Body: `LoreCreate` |
| `GET` | `/api/games/{game_id}/lore` | 获取世界观列表 | Path: `game_id` |
| `POST` | `/api/games/{game_id}/lore/organize` | 使用 LoreAgent 整理设定 | Path: `game_id`，Body: `{ text }` |
| `POST` | `/api/games/{game_id}/characters` | 创建角色 | Path: `game_id`，Body: `CharacterCreate` |
| `GET` | `/api/games/{game_id}/characters` | 获取角色列表 | Path: `game_id` |
| `POST` | `/api/characters/{character_id}/avatar` | 上传角色头像 | FormData: `file` |
| `POST` | `/api/games/{game_id}/items` | 创建物品 | Path: `game_id`，Body: `ItemCreate` |
| `GET` | `/api/games/{game_id}/items` | 获取物品列表 | Path: `game_id` |
| `POST` | `/api/games/{game_id}/inventory` | 创建库存记录 | Path: `game_id`，Body: `InventoryCreate` |
| `GET` | `/api/games/{game_id}/inventory` | 获取库存列表 | Path: `game_id` |
| `POST` | `/api/inventory/use` | 使用物品 | Body: `UseItemRequest` |
| `POST` | `/api/inventory/equip` | 装备物品 | Body: `EquipItemRequest` |
| `POST` | `/api/inventory/unequip` | 卸下物品 | Body: `EquipItemRequest` |
| `POST` | `/api/inventory/transfer` | 转移物品 | Body: `TransferRequest` |
| `POST` | `/api/games/{game_id}/events` | 创建世界事件 | Path: `game_id`，Body: `EventCreate` |
| `GET` | `/api/games/{game_id}/events` | 获取世界事件列表 | Path: `game_id` |
| `POST` | `/api/games/{game_id}/opening` | 生成开场白 | Path: `game_id` |
| `POST` | `/api/games/{game_id}/opening/stream` | 流式生成开场白 | Path: `game_id`，返回 NDJSON |
| `POST` | `/api/games/{game_id}/turn` | 推进一轮剧情 | Path: `game_id`，Body: `{ user_input }` |
| `POST` | `/api/games/{game_id}/turn/stream` | 流式推进剧情 | Path: `game_id`，Body: `{ user_input }`，返回 NDJSON |
| `DELETE` | `/api/turns/{turn_id}/from-here` | 删除该回合及之后剧情 | Path: `turn_id` |
| `POST` | `/api/turns/{turn_id}/regenerate` | 重新生成指定回合 | Path: `turn_id` |
| `POST` | `/api/turns/{turn_id}/regenerate/stream` | 流式重新生成指定回合 | Path: `turn_id`，返回 NDJSON |
| `POST` | `/api/games/{game_id}/management/sessions` | 创建管理会话 | Path: `game_id`，Body: `ManagementSessionCreate` |
| `GET` | `/api/games/{game_id}/management/sessions` | 获取管理会话列表 | Path: `game_id` |
| `POST` | `/api/management/sessions/{session_id}/chat` | 发送管理 Agent 消息 | Path: `session_id`，Body: `{ message, scope }` |
| `POST` | `/api/management/proposals/{proposal_id}/apply` | 确认执行修改方案 | Path: `proposal_id` |
| `POST` | `/api/management/proposals/{proposal_id}/reject` | 拒绝修改方案 | Path: `proposal_id` |
| `GET` | `/api/games/{game_id}/export` | 导出存档 JSON | Path: `game_id` |
| `POST` | `/api/games/import` | 导入存档 JSON | Body: `ImportPayload` |

## 安全与隐私

项目只提交源码和公开配置模板，不提交真实 `.env`、API Key、本地 SQLite 数据库、游戏存档、用户上传头像、虚拟环境、依赖目录和构建产物。详细说明见 [SECURITY.md](SECURITY.md)。

如果密钥曾被误提交，应立即在对应平台轮换密钥，并在公开仓库前清理 Git 历史。
