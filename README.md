# WordGameByAI

一个基于 FastAPI、Vue3 和 LangChain ChatOpenAI 的 AI 文字 RPG 应用框架，用结构化数据和多 Agent 叙事流水线管理长篇互动剧情。

[项目说明书](docs/项目说明书.md) | [公网部署准备清单](docs/公网部署准备清单.md) | [安全说明](SECURITY.md)

## 项目简介

WordGameByAI 面向 AI 文字游戏、互动叙事 Demo 和 AI Agent 应用原型开发场景。项目尝试解决普通 LLM 聊天式文字游戏中常见的几个问题：世界观容易漂移、角色状态难以追踪、人物关系变化不稳定、AI 生成的修改缺少安全边界。

项目把“剧情生成”拆成一套可管理的应用流程：前端提供存档、模板、角色、世界观、世界/副本和剧情推进界面；后端使用 FastAPI 提供 REST API 和流式剧情接口；数据库使用 SQLModel/SQLite 保存游戏状态；LLM 调用层基于 `langchain-openai` 的 `ChatOpenAI`，由多个职责明确的 Agent 模块完成主角行动理解、NPC 反应推演、剧情生成、状态补丁提取和一致性检查。

这不是一个单纯的聊天页面，而是一个围绕“AI 叙事 + 状态管理 + 数据安全写入”设计的 AI 应用框架。

## 项目亮点

- **LangChain 接入大模型**：通过 `langchain-openai` 的 `ChatOpenAI` 封装 OpenAI-compatible Chat Completions API，支持普通调用和流式输出。
- **多 Agent 角色分工流水线**：将主角行动、NPC 反应、旁白生成、状态补丁和一致性检查拆分为独立 Agent 模块，由 `game_engine.py` 统一编排。
- **结构化 Prompt 与 JSON 输出**：Agent Prompt 明确约束输出字段，使用 `response_format={"type": "json_object"}` 获取结构化结果，便于后端解析和落库。
- **动态记忆 RAG**：将世界观、角色记忆和每轮剧情摘要写入 `RagMemory`，每轮生成前按玩家输入检索相关长期记忆并注入 Agent 上下文。
- **行动与台词分离输入**：剧情推进时可分别填写“玩家希望的行动/背景/响应”和“主角实际说出口的话”，并支持空白项由系统结合上下文补全。
- **快速 / 精细双模式生成**：快速模式跳过前置主角/NPC 独立 LLM 推演，更快开始流式输出；精细模式完整执行多 Agent 推演，适合复杂剧情。
- **完整的状态建模**：使用 SQLModel 建模 Game、StoryWorld、WorldLore、Character、TurnLog、TurnSnapshot 等核心实体。
- **FastAPI + Vue 前后端联调**：后端提供 REST/NDJSON 流式接口，前端使用 Axios 和 fetch stream 消费接口，支持剧情推进、管理台和数据编辑。
- **AI 写入安全控制**：ManagementAgent 只生成修改方案，用户确认后才执行；后端通过 action 白名单和字段白名单限制 AI 对数据的影响范围。

## 功能模块

| 模块 | 功能说明 |
| --- | --- |
| 存档管理 | 创建、编辑、删除、导入、导出游戏存档，维护题材、世界类型、文风规则和当前状态。 |
| 账号权限 | 支持注册、登录、验证码校验和 Bearer Token 鉴权；第一个注册用户自动成为管理员。 |
| 管理后台 | 管理员可查看用户、存档和基础统计，普通用户只能访问自己的存档。 |
| 模板系统 | 内置都市恋爱、玄幻修真、丧尸末日、快穿任务、科幻远征和自定义空白模板；公共模板所有用户可见，普通用户可创建仅自己可见的私人模板。 |
| 世界/副本管理 | 维护 StoryWorld，支持任务目标、完成条件、失败条件、剧情偏移度和当前世界切换。 |
| 世界观管理 | 管理 WorldLore 条目，并通过 LoreAgent 将自然语言设定整理为结构化世界观数据。 |
| 角色系统 | 管理主角、NPC、反派、阵营代表等角色卡，支持头像上传和 `agent_enabled` 子 Agent 开关。 |
| 动态记忆 RAG | 使用本地哈希向量检索世界观、角色长期记忆和剧情摘要，支持重建、检索和随剧情推进更新。 |
| 剧情推进 | 支持开场生成、行动/台词拆分输入、空白补全、快速/精细生成、流式剧情输出、回合记录、删除后续回合和重新生成。 |
| 管理 Agent | 通过自然语言生成存档修改方案，用户确认后执行白名单动作。 |
| 导入导出 | 导出完整存档 JSON，导入后重建游戏、世界、设定、角色和回合记录。 |

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
│   ├── routers/                     # API 路由：games、characters、turns、management 等
│   ├── uploads/                     # 用户上传目录，实际文件默认不提交
│   ├── database.py                  # 数据库连接、表初始化、默认模板种子数据
│   ├── game_engine.py               # 剧情推进编排：加载上下文、调用 Agent、保存回合和快照
│   ├── llm_client.py                # LangChain ChatOpenAI 调用封装
│   ├── main.py                      # FastAPI 应用入口、CORS、静态文件、路由注册
│   ├── management_service.py        # ManagementAgent 方案确认、白名单动作执行
│   ├── models.py                    # SQLModel 数据模型
│   ├── numeric_utils.py             # AI 生成数值字段的容错转换
│   ├── prompt_builder.py            # Agent Prompt 构造与结构化输出约束
│   ├── rag_service.py               # 动态记忆 RAG 索引、检索、回合记忆写入
│   └── schemas.py                   # Pydantic 请求模型
├── frontend/                        # Vue3 前端
│   ├── src/
│   │   ├── api/                     # Axios/fetch API 封装
│   │   ├── components/              # 剧情日志、角色卡、管理 Agent 面板等组件
│   │   ├── router/                  # 前端路由
│   │   ├── stores/                  # Pinia 状态管理
│   │   ├── styles/                  # 全局样式
│   │   ├── utils/                   # 标签、预设、初始角色等工具
│   │   └── views/                   # 存档、游戏、模板、综合管理等页面
│   ├── package.json                 # 前端依赖和脚本
│   └── vite.config.js               # Vite 配置
├── docs/
│   └── 项目说明书.md                 # 更完整的项目说明文档
├── tests/                           # 后端单元测试：RAG、快速模式、状态补丁、结构化输入等
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
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
AUTH_TOKEN_TTL_DAYS=14
NON_MEMBER_DAILY_MESSAGE_LIMIT=20
MESSAGE_RATE_LIMIT_WINDOW_SECONDS=60
MESSAGE_RATE_LIMIT_MAX_REQUESTS=10
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
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
AUTH_TOKEN_TTL_DAYS=14
```

| 变量 | 说明 | 是否必填 |
| --- | --- | --- |
| `OPENAI_API_KEY` | 大模型 API Key。真实密钥只放本地 `.env`，不要提交到 Git。 | 调用 Agent 时必填 |
| `OPENAI_BASE_URL` | OpenAI-compatible API 地址，可接入兼容 OpenAI 协议的模型服务。 | 否，默认 OpenAI API |
| `OPENAI_MODEL` | 使用的模型名称。 | 否，默认 `gpt-4o-mini` |
| `DATABASE_URL` | SQLModel 数据库连接地址。 | 否，默认本地 SQLite |
| `CORS_ALLOW_ORIGINS` | 允许访问后端 API 的前端域名，公网部署时必须改成你的 HTTPS 域名。 | 否，本地开发地址 |
| `AUTH_TOKEN_TTL_DAYS` | 登录 token 有效天数。 | 否，默认 `14` |
| `NON_MEMBER_DAILY_MESSAGE_LIMIT` | 非会员每日可发送的大模型消息数上限。管理员和会员可在后台按用户调整。 | 否，默认 `20` |
| `MESSAGE_RATE_LIMIT_WINDOW_SECONDS` | 消息短窗限流窗口秒数。 | 否，默认 `60` |
| `MESSAGE_RATE_LIMIT_MAX_REQUESTS` | 单用户短窗内最多消息请求数。 | 否，默认 `10` |
| `VITE_API_BASE_URL` | 前端 API 地址，运行前端时可通过环境变量传入。 | 否，默认 `http://localhost:8000/api` |

## API 接口说明

以下列出主要接口，完整参数和响应可在启动后端后访问 `http://localhost:8000/docs` 查看。

| 方法 | 路径 | 功能说明 | 请求参数简述 |
| --- | --- | --- | --- |
| `GET` | `/api/health` | 健康检查 | 无 |
| `GET` | `/api/auth/captcha` | 获取注册验证码 | 无 |
| `POST` | `/api/auth/register` | 注册并登录 | Body: `RegisterRequest` |
| `POST` | `/api/auth/login` | 登录 | Body: `LoginRequest` |
| `GET` | `/api/auth/me` | 获取当前登录用户 | Header: `Authorization: Bearer <token>` |
| `GET` | `/api/admin/summary` | 管理后台统计 | 管理员权限 |
| `GET` | `/api/admin/users` | 管理后台用户列表 | 管理员权限 |
| `PATCH` | `/api/admin/users/{user_id}` | 启停用户、授予或取消管理员权限 | 管理员权限 |
| `GET` | `/api/admin/games` | 管理后台存档列表 | 管理员权限 |
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
| `POST` | `/api/games/{game_id}/opening` | 生成开场白 | Path: `game_id` |
| `POST` | `/api/games/{game_id}/opening/stream` | 流式生成开场白 | Path: `game_id`，返回 NDJSON |
| `POST` | `/api/games/{game_id}/turn` | 推进一轮剧情 | Path: `game_id`，Body: `TurnRequest` |
| `POST` | `/api/games/{game_id}/turn/stream` | 流式推进剧情 | Path: `game_id`，Body: `TurnRequest`，返回 NDJSON |
| `GET` | `/api/games/{game_id}/rag/memories` | 获取当前存档 RAG 记忆 | Path: `game_id` |
| `POST` | `/api/games/{game_id}/rag/search` | 检索相关长期记忆 | Path: `game_id`，Body: `{ query, top_k }` |
| `POST` | `/api/games/{game_id}/rag/rebuild` | 重建当前存档 RAG 记忆 | Path: `game_id` |
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

## 权限与隐私模型

- 第一个注册用户会自动成为管理员。
- 普通用户只能查看、编辑、删除自己的存档。
- 管理员可以查看后台统计、用户列表和所有存档列表。
- 公共模板 `owner_user_id = null`，所有用户可见；管理员创建的是公共模板。
- 普通用户创建的模板带有自己的 `owner_user_id`，只有自己和管理员可见。
- 真实 `.env`、本地 SQLite 数据库、上传头像、构建产物和依赖目录都被 `.gitignore` 排除，不应提交到 GitHub。

## 公网部署

详细清单见 [公网部署准备清单](docs/公网部署准备清单.md)。核心原则：

- 后端只监听内网地址，例如 `127.0.0.1:8010`，不要把后端端口直接暴露公网。
- 用 Nginx / Caddy 通过 `/api` 反向代理到 FastAPI，通过 `/uploads` 提供上传资源。
- 前端构建时设置 `VITE_API_BASE_URL=https://你的域名/api`。
- 生产环境只在服务器私有 `.env` 中配置真实 `OPENAI_API_KEY`。
- 正式多人使用建议从 SQLite 迁移到 PostgreSQL，并配置备份。

### TurnRequest 示例

剧情推进接口兼容旧版 `{ "user_input": "..." }`，也支持更适合文字 RPG 的结构化输入：

```json
{
  "action_input": "带杯热可可下楼，观察她的反应，希望气氛自然一点",
  "dialogue_input": "今天怎么想起我了，大忙人",
  "auto_complete_blank": true,
  "fast_mode": true
}
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `user_input` | 旧版单文本输入，仍然兼容。 |
| `action_input` | 玩家希望主角执行的行动、场景背景或希望剧情怎样响应。 |
| `dialogue_input` | 主角本轮实际说出口的台词。 |
| `auto_complete_blank` | 某个输入为空时，是否允许系统结合上下文补动作或短对白。关闭时，台词留空表示主角明确不主动说话。 |
| `fast_mode` | 是否启用快速模式。快速模式减少前置 LLM 调用，更快开始流式输出。 |

## 动态记忆 RAG 流程

```text
世界观 / 角色记忆 / 世界事件 / 历史回合
        ↓
sync_rag_memories / store_turn_memory
        ↓
RagMemory 本地向量索引
        ↓
retrieve_related_memories 按本轮输入检索
        ↓
注入 ProtagonistAgent / NPCReactionAgent / NarratorAgent 上下文
        ↓
生成剧情后写入新的回合摘要记忆
```

这个 RAG 不是只在开局加载固定知识库，而是会随着剧情推进持续更新。每轮剧情保存后，系统会把可复用的剧情摘要、NPC 反应、状态变化和检查结果写成新的长期记忆，后续回合可以按语义检索回来。

## 测试与构建

后端单元测试：

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
python -m compileall backend tests
```

前端构建：

```bash
cd frontend
npm run build
```

## 安全与隐私

项目只提交源码和公开配置模板，不提交真实 `.env`、API Key、本地 SQLite 数据库、游戏存档、用户上传头像、虚拟环境、依赖目录和构建产物。详细说明见 [SECURITY.md](SECURITY.md)。

如果密钥曾被误提交，应立即在对应平台轮换密钥，并在公开仓库前清理 Git 历史。
