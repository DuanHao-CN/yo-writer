# AI Agent SaaS 平台 — 产品需求文档 & 技术设计文档

> **项目代号**: YoAgent
> **版本**: v1.0
> **日期**: 2026-03-17
> **作者**: Architecture Team

---

## 目录

1. [产品愿景与目标](#1-产品愿景与目标)
2. [用户画像与使用场景](#2-用户画像与使用场景)
3. [系统架构总览](#3-系统架构总览)
4. [核心模块设计](#4-核心模块设计)
5. [数据模型设计](#5-数据模型设计)
6. [API 设计规范](#6-api-设计规范)
7. [Agent 编排引擎（LangGraph）](#7-agent-编排引擎langgraph)
8. [工具协议层（FastMCP）](#8-工具协议层fastmcp)
9. [前端交互层（CopilotKit）](#9-前端交互层copilotkit)
10. [代码执行沙箱](#10-代码执行沙箱)
11. [多租户与安全设计](#11-多租户与安全设计)
12. [部署架构](#12-部署架构)
13. [分阶段交付路线图](#13-分阶段交付路线图)
14. [非功能性需求](#14-非功能性需求)
15. [风险与缓解策略](#15-风险与缓解策略)

---

## 1. 产品愿景与目标

### 1.1 愿景

构建一个 **Agent-as-a-Service** 平台，让用户（开发者与非技术用户）能够通过可视化界面与代码两种方式，创建、配置、运行和部署 AI Agent，并接入数据源、外部工具和安全的代码执行环境。

### 1.2 核心价值主张

| 维度 | 价值 |
|------|------|
| **降低门槛** | 非技术用户通过 Chat + 拖拽即可构建 Agent |
| **开发者友好** | 开发者通过 Python SDK / API 全面控制 Agent 逻辑 |
| **工具生态** | 基于 MCP 协议的标准化工具接入，支持一键集成数百种外部服务 |
| **安全执行** | 隔离沙箱环境运行用户代码，确保平台安全 |
| **可观测性** | Agent 运行全链路可追踪、可回放、可调试 |

### 1.3 成功指标（北极星指标）

| 指标 | 目标（上线 6 个月内） |
|------|----------------------|
| 月活跃 Agent 数 | 10,000+ |
| Agent 平均任务完成率 | > 85% |
| P99 首 token 响应延迟 | < 2s |
| 平台可用性 | 99.9% |
| 付费转化率（Free → Pro） | > 5% |

---

## 2. 用户画像与使用场景

### 2.1 用户画像

#### Persona A — 独立开发者 / AI Builder

- 熟悉 Python，了解 LLM 基本概念
- 希望快速构建有工具调用能力的 Agent
- 关注：SDK 易用性、文档完善度、调试体验

#### Persona B — 企业技术团队

- 需要将 AI Agent 集成到内部业务系统
- 关注：多租户隔离、SSO、审计日志、SLA
- 期望：私有化部署选项、自定义 LLM Provider

#### Persona C — 非技术业务用户

- 通过 Chat UI 与预构建 Agent 交互
- 期望：自然语言驱动，无需编程即可完成任务
- 关注：交互流畅度、Agent 准确性

### 2.2 核心使用场景

| 场景 | 描述 | 涉及模块 |
|------|------|----------|
| **创建自定义 Agent** | 用户定义 Agent 的系统提示词、工具集、执行流程 | Agent Builder, LangGraph |
| **接入外部工具** | 连接数据库、API、SaaS 服务作为 Agent 的可用工具 | FastMCP, Tool Registry |
| **对话式交互** | 通过 Chat UI 与 Agent 实时对话，支持流式响应 | CopilotKit, AG-UI |
| **代码生成与执行** | Agent 生成 Python 代码并在安全沙箱中执行 | Python Sandbox |
| **Agent 发布与共享** | 将 Agent 发布为 API 端点或嵌入式组件 | Deployment, API Gateway |
| **运行监控与调试** | 查看 Agent 执行链路、token 消耗、工具调用记录 | Observability |

---

## 3. 系统架构总览

### 3.1 架构分层图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client Layer                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Web App      │  │  Embed SDK   │  │  REST / WebSocket API    │  │
│  │  (Next.js +   │  │  (iframe /   │  │  (Third-party            │  │
│  │   CopilotKit) │  │   Web Comp.) │  │   integrations)          │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘  │
└─────────┼─────────────────┼─────────────────────┼──────────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       API Gateway (Nginx / Traefik)                  │
│            Rate Limiting · Auth · SSL Termination                    │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐ ┌────────────────┐ ┌─────────────────┐
│   Auth Service   │ │   Core API     │ │   AG-UI Endpoint│
│   (FastAPI)      │ │   (FastAPI)    │ │   (FastAPI +    │
│   - JWT / OAuth  │ │   - Agent CRUD │ │    CopilotKit)  │
│   - RBAC         │ │   - Tool Mgmt  │ │   - Streaming   │
│   - API Keys     │ │   - Workspace  │ │   - Chat        │
└──────┬───────────┘ └────┬───────────┘ └────┬────────────┘
       │                  │                   │
       │                  ▼                   ▼
       │        ┌──────────────────────────────────────┐
       │        │       Agent Runtime Layer             │
       │        │  ┌─────────────────────────────────┐ │
       │        │  │   LangGraph Orchestration Engine │ │
       │        │  │   - StateGraph 编排              │ │
       │        │  │   - Checkpointer 持久化          │ │
       │        │  │   - Streaming 支持               │ │
       │        │  └────────────┬────────────────────┘ │
       │        │               │                      │
       │        │  ┌────────────▼────────────────────┐ │
       │        │  │   Tool Execution Layer (FastMCP)│ │
       │        │  │   - MCP Server Registry         │ │
       │        │  │   - Tool Discovery & Routing    │ │
       │        │  │   - Namespace Isolation          │ │
       │        │  └────────────┬────────────────────┘ │
       │        │               │                      │
       │        │  ┌────────────▼────────────────────┐ │
       │        │  │   Code Sandbox (Python)         │ │
       │        │  │   - gVisor / nsjail 隔离        │ │
       │        │  │   - 资源限额                     │ │
       │        │  │   - uv 依赖管理                  │ │
       │        │  └─────────────────────────────────┘ │
       │        └──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Data Layer                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │PostgreSQL│  │  Redis   │  │   S3 /   │  │  Vector Store     │  │
│  │(Core DB) │  │(Cache +  │  │  MinIO   │  │  (pgvector /      │  │
│  │          │  │ PubSub)  │  │(Files)   │  │   Qdrant)         │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 技术栈确认

| 层级 | 技术选型 | 职责 |
|------|----------|------|
| **前端** | Next.js + CopilotKit | Agent Chat UI、Generative UI、Agent Builder |
| **API 网关** | Traefik / Nginx | 路由、限流、SSL、负载均衡 |
| **后端框架** | FastAPI (Python) | REST API、WebSocket、AG-UI Endpoint |
| **Agent 编排** | LangGraph | 状态图编排、条件分支、多 Agent 协作 |
| **工具协议** | FastMCP | MCP 工具注册、发现、路由、认证 |
| **代码沙箱** | Python Sandbox (gVisor/nsjail) | 安全隔离的 Python 代码执行 |
| **包管理** | uv | Python 依赖安装与虚拟环境管理 |
| **数据库** | PostgreSQL + pgvector | 结构化数据 + 向量检索 |
| **缓存** | Redis | 会话缓存、限流计数器、PubSub |
| **对象存储** | S3 / MinIO | 文件上传、Agent 产物存储 |
| **消息队列** | Redis Streams / NATS | 异步任务分发、Agent 事件流 |
| **可观测性** | OpenTelemetry + Grafana | 分布式追踪、指标监控、日志聚合 |

### 3.3 请求流转（核心链路）

```
用户消息 → CopilotKit (AG-UI Protocol)
        → FastAPI AG-UI Endpoint
        → LangGraph StateGraph.invoke()
           ├── LLM Node → LLM Provider (OpenAI/Anthropic/...)
           ├── Tool Node → FastMCP Client → MCP Server(s)
           └── Code Node → Sandbox RPC → Python Sandbox
        → 流式响应 (SSE / WebSocket)
        → CopilotKit 渲染
```

---

## 4. 核心模块设计

### 4.1 模块全景

```
YoAgent Platform
├── auth-service          # 认证与授权
├── core-api              # 核心业务 API
│   ├── agent-manager     # Agent CRUD & 版本管理
│   ├── tool-registry     # 工具注册与管理
│   ├── workspace-manager # 工作空间管理
│   └── billing-service   # 计费与配额
├── agent-runtime         # Agent 运行时
│   ├── langgraph-engine  # LangGraph 编排引擎
│   ├── mcp-gateway       # FastMCP 工具网关
│   └── sandbox-pool      # 代码沙箱池
├── agui-endpoint         # AG-UI 协议端点（CopilotKit 对接）
├── event-bus             # 事件总线
└── observability         # 可观测性
```

### 4.2 Module: Auth Service

**职责**: 用户认证、授权、API Key 管理

| 功能 | 说明 |
|------|------|
| 注册 / 登录 | Email + Password, OAuth (GitHub, Google) |
| JWT Token 管理 | Access Token (15min) + Refresh Token (7d) |
| API Key | 用于 Agent API 调用的长期令牌，支持 scope 限制 |
| RBAC | Owner / Admin / Member / Viewer 四级角色 |
| SSO (企业版) | SAML 2.0 / OIDC 对接企业 IdP |

**关键接口**:

```
POST   /auth/register
POST   /auth/login
POST   /auth/refresh
POST   /auth/api-keys
DELETE /auth/api-keys/{key_id}
GET    /auth/me
```

### 4.3 Module: Agent Manager

**职责**: Agent 生命周期管理

| 功能 | 说明 |
|------|------|
| Agent CRUD | 创建、读取、更新、删除 Agent 配置 |
| 版本管理 | 每次修改生成新版本，支持回滚 |
| Agent 模板 | 预置模板（问答型、RAG型、代码型、工作流型） |
| Agent 发布 | 将 Agent 发布为 API / Embed / 公开链接 |
| Agent Fork | 基于公开 Agent 创建副本 |

**Agent 配置结构**:

```yaml
agent:
  name: "Data Analyst"
  description: "Analyze CSV data and generate insights"
  model:
    provider: "openai"                # openai | anthropic | custom
    model_id: "gpt-5.4"
    temperature: 0.7
    max_tokens: 4096
  system_prompt: |
    You are a data analyst assistant.
    You can read CSV files, run Python code, and create visualizations.
  tools:
    - mcp://builtin/code-sandbox      # 内置代码沙箱
    - mcp://builtin/file-reader       # 文件读取
    - mcp://user/my-database-tool     # 用户自定义工具
    - mcp://marketplace/slack-tool    # 市场工具
  graph:
    type: "react"                     # react | plan-execute | custom
    max_iterations: 10
    checkpointer: true
  memory:
    type: "conversation"              # conversation | summary | vector
    max_messages: 50
  sandbox:
    enabled: true
    timeout_seconds: 30
    max_memory_mb: 512
    allowed_packages:
      - pandas
      - matplotlib
      - numpy
```

### 4.4 Module: Tool Registry (FastMCP Gateway)

**职责**: 基于 MCP 协议的工具注册、发现与路由

| 功能 | 说明 |
|------|------|
| 内置工具 | 代码执行、文件处理、网页搜索等平台内置工具 |
| 用户自定义工具 | 用户上传 Python 函数或提供 OpenAPI Spec 自动生成 |
| 工具市场 | 社区贡献的 MCP Server，一键安装 |
| 工具编排 | 通过 FastMCP `mount()` 组合多个 MCP Server |
| 工具认证 | 每个工具独立的 credential 管理（OAuth, API Key） |

**架构设计**:

```
MCP Gateway (FastMCP Orchestrator)
├── builtin/               # 内置 MCP Servers
│   ├── code-sandbox       # 代码执行
│   ├── file-ops           # 文件操作
│   ├── web-search         # 网页搜索
│   └── vector-store       # 向量检索
├── user/{user_id}/        # 用户自定义 Servers
│   ├── my-db-tool         # 用户自定义数据库工具
│   └── my-api-tool        # 用户自定义 API 工具
└── marketplace/           # 市场 Servers
    ├── slack              # Slack 集成
    ├── github             # GitHub 集成
    └── notion             # Notion 集成
```

**FastMCP 集成代码示例**:

```python
from fastmcp import FastMCP
from fastmcp.server import create_proxy

# 创建平台级 MCP 编排器
gateway = FastMCP("YoAgent-MCP-Gateway")

# 挂载内置工具
from tools.builtin.code_sandbox import sandbox_server
from tools.builtin.file_ops import file_server
gateway.mount(sandbox_server, namespace="builtin/code-sandbox")
gateway.mount(file_server, namespace="builtin/file-ops")

# 挂载用户自定义工具（动态）
def mount_user_tools(user_id: str, tool_configs: list):
    for config in tool_configs:
        if config.type == "openapi":
            server = FastMCP.from_openapi(
                openapi_spec=config.spec,
                client=httpx.AsyncClient(
                    base_url=config.base_url,
                    headers={"Authorization": f"Bearer {config.token}"}
                ),
                name=config.name,
            )
        elif config.type == "python":
            server = create_proxy(config.script_path)
        gateway.mount(server, namespace=f"user/{user_id}/{config.name}")

# 挂载市场工具
gateway.mount(
    create_proxy("http://marketplace-slack.internal:8080/mcp"),
    namespace="marketplace/slack"
)
```

### 4.5 Module: Sandbox Pool

**职责**: 管理安全隔离的 Python 代码执行环境

| 功能 | 说明 |
|------|------|
| 沙箱创建 | 按需创建隔离的 Python 执行环境 |
| 资源限制 | CPU 时间、内存、磁盘、网络访问限制 |
| 依赖管理 | 通过 uv 快速安装 Python 包 |
| 文件 I/O | 受限的文件读写（仅 workspace 目录） |
| 池化管理 | 预热沙箱池，减少冷启动延迟 |

**沙箱架构**:

```
┌─────────────────────────────────────────────────┐
│              Sandbox Manager                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │ Warm    │  │ Warm    │  │ Warm    │  ...     │
│  │ Sandbox │  │ Sandbox │  │ Sandbox │          │
│  └────┬────┘  └────┬────┘  └────┬────┘          │
│       │            │            │                │
│       ▼            ▼            ▼                │
│  ┌──────────────────────────────────────────┐   │
│  │  gVisor / nsjail 隔离层                   │   │
│  │  - 独立 PID namespace                     │   │
│  │  - 独立 network namespace (可选)          │   │
│  │  - cgroup 资源限制                        │   │
│  │  - seccomp 系统调用过滤                   │   │
│  └──────────────────────────────────────────┘   │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │  uv 虚拟环境                              │   │
│  │  - 按 Agent 配置安装依赖                   │   │
│  │  - 缓存已安装包（跨沙箱共享只读层）        │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**接口设计**:

```python
class SandboxManager:
    async def acquire(self, config: SandboxConfig) -> Sandbox:
        """从池中获取一个预热沙箱，或按需创建"""

    async def execute(self, sandbox: Sandbox, code: str) -> ExecutionResult:
        """在沙箱中执行代码，返回 stdout/stderr/artifacts"""

    async def release(self, sandbox: Sandbox) -> None:
        """归还沙箱到池中（重置状态）或销毁"""

    async def install_packages(self, sandbox: Sandbox, packages: list[str]) -> None:
        """使用 uv 安装 Python 包"""

@dataclass
class SandboxConfig:
    timeout_seconds: int = 30
    max_memory_mb: int = 512
    max_cpu_seconds: int = 10
    network_access: bool = False
    allowed_packages: list[str] = field(default_factory=list)
    workspace_files: dict[str, bytes] = field(default_factory=dict)

@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    artifacts: dict[str, bytes]     # 生成的文件（图表、CSV 等）
    execution_time_ms: int
    memory_peak_mb: float
```

### 4.6 Module: Billing Service

**职责**: 用量计量与计费

| 计量维度 | 说明 |
|----------|------|
| LLM Token | 按 input/output token 分别计量 |
| 工具调用 | 按次数计量 |
| 沙箱执行 | 按 CPU 秒数计量 |
| 存储 | 按 GB/月计量 |

**定价方案**:

| Plan | 价格 | 包含 |
|------|------|------|
| **Free** | $0/月 | 50K tokens, 100 tool calls, 10 min sandbox |
| **Pro** | $29/月 | 2M tokens, 5K tool calls, 2h sandbox, 5 Agents |
| **Team** | $99/月/座 | 10M tokens, 50K tool calls, 10h sandbox, 无限 Agents |
| **Enterprise** | 定制 | 私有部署, SSO, SLA, 审计日志 |

---

## 5. 数据模型设计

### 5.1 ER 关系概览

```
User (1) ──── (N) Workspace
Workspace (1) ──── (N) Agent
Workspace (1) ──── (N) Tool
Agent (1) ──── (N) AgentVersion
Agent (N) ──── (M) Tool              [agent_tools 关联表]
Agent (1) ──── (N) Conversation
Conversation (1) ──── (N) Message
Conversation (1) ──── (N) AgentRun
AgentRun (1) ──── (N) ToolCall
AgentRun (1) ──── (N) SandboxExecution
Workspace (1) ──── (N) WorkspaceMember [多成员]
User (1) ──── (N) ApiKey
```

### 5.2 核心表结构

```sql
-- 用户
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),
    display_name    VARCHAR(100),
    avatar_url      TEXT,
    auth_provider   VARCHAR(50) DEFAULT 'email',  -- email | github | google
    external_id     VARCHAR(255),                  -- OAuth provider user ID
    plan            VARCHAR(20) DEFAULT 'free',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 工作空间
CREATE TABLE workspaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    owner_id        UUID REFERENCES users(id) ON DELETE CASCADE,
    settings        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 工作空间成员
CREATE TABLE workspace_members (
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL DEFAULT 'member',
    -- role: owner | admin | member | viewer
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);

-- Agent
CREATE TABLE agents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) NOT NULL,
    description     TEXT,
    icon            VARCHAR(50),
    status          VARCHAR(20) DEFAULT 'draft',  -- draft | active | archived
    visibility      VARCHAR(20) DEFAULT 'private', -- private | workspace | public
    current_version INT DEFAULT 1,
    config          JSONB NOT NULL,               -- Agent 完整配置（见 4.3）
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (workspace_id, slug)
);

-- Agent 版本
CREATE TABLE agent_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID REFERENCES agents(id) ON DELETE CASCADE,
    version         INT NOT NULL,
    config          JSONB NOT NULL,
    changelog       TEXT,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (agent_id, version)
);

-- 工具注册
CREATE TABLE tools (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) NOT NULL,
    description     TEXT,
    type            VARCHAR(20) NOT NULL,         -- builtin | custom | marketplace
    mcp_uri         TEXT NOT NULL,                -- mcp://builtin/code-sandbox
    config          JSONB DEFAULT '{}',           -- 工具特定配置
    credentials     JSONB DEFAULT '{}',           -- 加密存储的凭据
    schema_json     JSONB,                        -- 工具输入输出 schema
    status          VARCHAR(20) DEFAULT 'active',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (workspace_id, slug)
);

-- Agent-Tool 关联
CREATE TABLE agent_tools (
    agent_id        UUID REFERENCES agents(id) ON DELETE CASCADE,
    tool_id         UUID REFERENCES tools(id) ON DELETE CASCADE,
    config_override JSONB DEFAULT '{}',           -- Agent 级别的工具配置覆盖
    PRIMARY KEY (agent_id, tool_id)
);

-- 对话
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID REFERENCES agents(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id),
    title           VARCHAR(255),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 消息
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,          -- user | assistant | system | tool
    content         TEXT,
    tool_calls      JSONB,                         -- LLM 发起的工具调用
    tool_call_id    VARCHAR(100),                   -- 工具响应关联 ID
    metadata        JSONB DEFAULT '{}',
    tokens_input    INT,
    tokens_output   INT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);

-- Agent 运行记录
CREATE TABLE agent_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    agent_id        UUID REFERENCES agents(id),
    agent_version   INT,
    status          VARCHAR(20) DEFAULT 'running', -- running | completed | failed | cancelled
    trigger_message_id UUID REFERENCES messages(id),
    total_tokens    INT DEFAULT 0,
    total_cost_usd  DECIMAL(10,6) DEFAULT 0,
    duration_ms     INT,
    error           TEXT,
    trace_id        VARCHAR(64),                   -- OpenTelemetry trace ID
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

-- 工具调用记录
CREATE TABLE tool_calls (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id    UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    tool_name       VARCHAR(100) NOT NULL,
    mcp_uri         TEXT,
    input_args      JSONB,
    output          JSONB,
    status          VARCHAR(20) DEFAULT 'pending',
    duration_ms     INT,
    error           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 沙箱执行记录
CREATE TABLE sandbox_executions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id    UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    code            TEXT NOT NULL,
    stdout          TEXT,
    stderr          TEXT,
    exit_code       INT,
    artifacts       JSONB DEFAULT '[]',            -- [{name, url, mime_type}]
    cpu_seconds     FLOAT,
    memory_peak_mb  FLOAT,
    duration_ms     INT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- API Keys
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    name            VARCHAR(100),
    key_hash        VARCHAR(255) NOT NULL,         -- bcrypt hash, 原始 key 仅在创建时返回
    key_prefix      VARCHAR(10) NOT NULL,          -- "ya_" + 前 8 字符，用于识别
    scopes          TEXT[] DEFAULT '{}',            -- 权限范围
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 用量记录（用于计费）
CREATE TABLE usage_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    type            VARCHAR(30) NOT NULL,          -- llm_tokens | tool_calls | sandbox_cpu | storage
    quantity        BIGINT NOT NULL,
    unit            VARCHAR(20),                   -- tokens | calls | seconds | bytes
    metadata        JSONB DEFAULT '{}',
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_usage_workspace_time ON usage_records(workspace_id, recorded_at);
```

---

## 6. API 设计规范

### 6.1 通用约定

| 约定 | 规范 |
|------|------|
| 基础路径 | `/api/v1/` |
| 认证 | `Authorization: Bearer <jwt>` 或 `X-API-Key: ya_xxx` |
| 分页 | `?page=1&page_size=20`，响应包含 `total`, `page`, `page_size` |
| 排序 | `?sort_by=created_at&sort_order=desc` |
| 过滤 | `?status=active&visibility=public` |
| 错误格式 | `{"error": {"code": "AGENT_NOT_FOUND", "message": "...", "details": {...}}}` |
| 速率限制 | Free: 60 req/min, Pro: 300 req/min, Team: 1000 req/min |

### 6.2 Agent API

```
# Agent CRUD
POST   /api/v1/workspaces/{ws_id}/agents              # 创建 Agent
GET    /api/v1/workspaces/{ws_id}/agents              # 列出 Agents
GET    /api/v1/workspaces/{ws_id}/agents/{agent_id}   # 获取 Agent 详情
PATCH  /api/v1/workspaces/{ws_id}/agents/{agent_id}   # 更新 Agent
DELETE /api/v1/workspaces/{ws_id}/agents/{agent_id}   # 删除 Agent

# Agent 版本
GET    /api/v1/agents/{agent_id}/versions              # 列出版本
GET    /api/v1/agents/{agent_id}/versions/{version}    # 获取特定版本
POST   /api/v1/agents/{agent_id}/rollback/{version}    # 回滚到特定版本

# Agent 运行（同步）
POST   /api/v1/agents/{agent_id}/run                   # 运行 Agent（同步）
# Request:
# {
#   "messages": [{"role": "user", "content": "Analyze this CSV"}],
#   "files": ["s3://bucket/data.csv"],
#   "stream": true
# }

# Agent 运行历史
GET    /api/v1/agents/{agent_id}/runs                  # 运行记录列表
GET    /api/v1/agents/{agent_id}/runs/{run_id}         # 运行记录详情
GET    /api/v1/agents/{agent_id}/runs/{run_id}/trace   # 运行追踪链路
```

### 6.3 Conversation API

```
# 对话管理
POST   /api/v1/conversations                           # 创建对话
GET    /api/v1/conversations                           # 列出对话
GET    /api/v1/conversations/{conv_id}                 # 获取对话详情
DELETE /api/v1/conversations/{conv_id}                 # 删除对话

# 消息
POST   /api/v1/conversations/{conv_id}/messages        # 发送消息（触发 Agent 运行）
GET    /api/v1/conversations/{conv_id}/messages        # 获取消息历史

# 流式端点（AG-UI Protocol）
POST   /agui/{agent_name}/runs                         # CopilotKit AG-UI 流式端点
```

### 6.4 Tool API

```
# 工具管理
POST   /api/v1/workspaces/{ws_id}/tools               # 注册工具
GET    /api/v1/workspaces/{ws_id}/tools               # 列出工具
GET    /api/v1/workspaces/{ws_id}/tools/{tool_id}     # 工具详情
PATCH  /api/v1/workspaces/{ws_id}/tools/{tool_id}     # 更新工具
DELETE /api/v1/workspaces/{ws_id}/tools/{tool_id}     # 删除工具

# 工具测试
POST   /api/v1/tools/{tool_id}/test                    # 测试工具调用

# 工具市场
GET    /api/v1/marketplace/tools                       # 浏览市场工具
POST   /api/v1/marketplace/tools/{tool_id}/install     # 安装市场工具
```

---

## 7. Agent 编排引擎（LangGraph）

### 7.1 编排模式

平台支持多种预置编排模式，用户也可通过自定义 StateGraph 实现任意复杂度的 Agent 逻辑。

#### 模式 A: ReAct Agent（默认）

经典 Reasoning + Acting 循环，适用于大部分通用场景。

```python
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import SystemMessage

async def llm_node(state: MessagesState):
    """调用 LLM，可能产生工具调用"""
    model = get_model_for_agent(state["agent_config"])
    model_with_tools = model.bind_tools(state["available_tools"])
    system = SystemMessage(content=state["agent_config"]["system_prompt"])
    response = await model_with_tools.ainvoke([system, *state["messages"]])
    return {"messages": [response]}

async def tool_node(state: MessagesState):
    """通过 MCP Gateway 执行工具调用"""
    results = []
    for tool_call in state["messages"][-1].tool_calls:
        result = await mcp_gateway.call_tool(
            tool_name=tool_call["name"],
            args=tool_call["args"],
            context=state["context"]
        )
        results.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))
    return {"messages": results}

def should_continue(state: MessagesState):
    last = state["messages"][-1]
    if not last.tool_calls:
        return END
    return "tools"

# 构建 ReAct 图
graph = StateGraph(MessagesState)
graph.add_node("llm", llm_node)
graph.add_node("tools", tool_node)
graph.add_edge(START, "llm")
graph.add_conditional_edges("llm", should_continue, ["tools", END])
graph.add_edge("tools", "llm")
react_agent = graph.compile(checkpointer=get_checkpointer())
```

#### 模式 B: Plan-Execute Agent

先规划任务步骤，再依次执行，适合复杂多步骤任务。

```python
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

class PlanExecuteState(TypedDict):
    messages: Annotated[list, add_messages]
    plan: list[str]            # 规划的步骤列表
    current_step: int          # 当前执行步骤索引
    step_results: list[str]    # 每步执行结果
    final_answer: str

async def planner_node(state: PlanExecuteState):
    """LLM 分析用户需求，生成执行计划"""
    plan = await llm.ainvoke(
        f"Break down this task into steps: {state['messages'][-1].content}"
    )
    return {"plan": parse_plan(plan), "current_step": 0}

async def executor_node(state: PlanExecuteState):
    """执行当前步骤"""
    step = state["plan"][state["current_step"]]
    result = await execute_step(step, state)
    return {
        "step_results": [*state["step_results"], result],
        "current_step": state["current_step"] + 1
    }

async def synthesizer_node(state: PlanExecuteState):
    """汇总所有步骤结果，生成最终回答"""
    answer = await llm.ainvoke(
        f"Synthesize results: {state['step_results']}"
    )
    return {"final_answer": answer, "messages": [AIMessage(content=answer)]}

def route_after_execute(state: PlanExecuteState):
    if state["current_step"] >= len(state["plan"]):
        return "synthesize"
    return "execute"

graph = StateGraph(PlanExecuteState)
graph.add_node("plan", planner_node)
graph.add_node("execute", executor_node)
graph.add_node("synthesize", synthesizer_node)
graph.add_edge(START, "plan")
graph.add_edge("plan", "execute")
graph.add_conditional_edges("execute", route_after_execute, ["execute", "synthesize"])
graph.add_edge("synthesize", END)
```

#### 模式 C: Multi-Agent 协作

多个专家 Agent 协作完成任务，由 Supervisor 统一调度。

```python
class SupervisorState(TypedDict):
    messages: Annotated[list, add_messages]
    next_agent: str
    agent_outputs: dict[str, str]

async def supervisor_node(state: SupervisorState):
    """Supervisor 决定下一步交给哪个 Agent"""
    decision = await supervisor_llm.ainvoke(
        f"Available agents: researcher, coder, reviewer. "
        f"Current state: {state}. Which agent should act next?"
    )
    return {"next_agent": decision.agent_name}

async def researcher_node(state: SupervisorState):
    """研究员 Agent：负责信息检索"""
    result = await researcher_agent.ainvoke(state)
    return {"agent_outputs": {**state["agent_outputs"], "researcher": result}}

async def coder_node(state: SupervisorState):
    """程序员 Agent：负责代码生成与执行"""
    result = await coder_agent.ainvoke(state)
    return {"agent_outputs": {**state["agent_outputs"], "coder": result}}

async def reviewer_node(state: SupervisorState):
    """审查员 Agent：负责质量检查"""
    result = await reviewer_agent.ainvoke(state)
    return {"agent_outputs": {**state["agent_outputs"], "reviewer": result}}

graph = StateGraph(SupervisorState)
graph.add_node("supervisor", supervisor_node)
graph.add_node("researcher", researcher_node)
graph.add_node("coder", coder_node)
graph.add_node("reviewer", reviewer_node)

graph.add_edge(START, "supervisor")
graph.add_conditional_edges("supervisor", lambda s: s["next_agent"], {
    "researcher": "researcher",
    "coder": "coder",
    "reviewer": "reviewer",
    "done": END,
})
for agent in ["researcher", "coder", "reviewer"]:
    graph.add_edge(agent, "supervisor")
```

### 7.2 Checkpointer 持久化

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 使用 PostgreSQL 作为 Checkpoint 存储
# 支持对话中断后恢复、历史状态回放
async def get_checkpointer():
    return AsyncPostgresSaver.from_conn_string(
        conn_string=settings.DATABASE_URL
    )
```

### 7.3 Agent 运行时集成

```python
# agent_runtime.py — 核心运行时入口
from copilotkit import LangGraphAGUIAgent
from ag_ui_langgraph import add_langgraph_fastapi_endpoint

class AgentRuntime:
    """管理所有 Agent 实例的运行时"""

    def __init__(self, app: FastAPI, mcp_gateway: FastMCP):
        self.app = app
        self.mcp_gateway = mcp_gateway
        self.agents: dict[str, CompiledGraph] = {}

    async def register_agent(self, agent_config: AgentConfig) -> None:
        """根据配置编译 LangGraph 并注册到 FastAPI"""
        graph = self._build_graph(agent_config)
        compiled = graph.compile(checkpointer=await get_checkpointer())
        self.agents[agent_config.slug] = compiled

        # 注册 AG-UI 端点（CopilotKit 对接）
        add_langgraph_fastapi_endpoint(
            app=self.app,
            agent=LangGraphAGUIAgent(
                name=agent_config.slug,
                description=agent_config.description,
                graph=compiled,
            ),
            path=f"/agui/{agent_config.slug}",
        )

    def _build_graph(self, config: AgentConfig) -> StateGraph:
        """根据 Agent 配置构建对应的 LangGraph"""
        if config.graph_type == "react":
            return self._build_react_graph(config)
        elif config.graph_type == "plan-execute":
            return self._build_plan_execute_graph(config)
        elif config.graph_type == "multi-agent":
            return self._build_multi_agent_graph(config)
        else:
            return self._build_custom_graph(config)
```

---

## 8. 工具协议层（FastMCP）

### 8.1 MCP 架构设计

```
┌────────────────────────────────────────────────────────┐
│                   MCP Gateway (FastMCP)                  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Tool Router                          │  │
│  │  mcp://builtin/*  → Built-in MCP Servers         │  │
│  │  mcp://user/*     → User Custom MCP Servers      │  │
│  │  mcp://market/*   → Marketplace MCP Servers      │  │
│  └──────────┬───────────────────────────────────────┘  │
│             │                                           │
│  ┌──────────▼───────────────────────────────────────┐  │
│  │           Middleware Stack                         │  │
│  │  1. Auth Middleware  (验证 Agent 对工具的访问权限)  │  │
│  │  2. Rate Limiter     (工具调用频率限制)            │  │
│  │  3. Usage Tracker    (计量记录)                    │  │
│  │  4. Audit Logger     (审计日志)                    │  │
│  │  5. Error Handler    (统一错误处理)                │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### 8.2 自定义工具开发 SDK

用户可以通过两种方式注册自定义工具：

**方式 A: Python 函数（平台托管）**

```python
# 用户上传的工具代码
from fastmcp import FastMCP

server = FastMCP("my-database-tool")

@server.tool
def query_database(sql: str, database: str = "main") -> str:
    """Execute a read-only SQL query against the specified database.

    Args:
        sql: The SQL query to execute (SELECT only)
        database: Target database name
    """
    # 平台注入的数据库连接（通过 credential manager）
    conn = get_connection(database)
    result = conn.execute(sql)
    return result.to_json()

@server.resource("schema://tables")
def list_tables() -> list[dict]:
    """List all available tables and their schemas."""
    return get_all_table_schemas()
```

**方式 B: OpenAPI Spec 自动生成**

```python
# 平台自动将用户提供的 OpenAPI Spec 转化为 MCP Server
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType

spec = load_user_openapi_spec(tool_id)
client = httpx.AsyncClient(
    base_url=spec["servers"][0]["url"],
    headers={"Authorization": f"Bearer {get_user_credential(tool_id)}"}
)

mcp_server = FastMCP.from_openapi(
    openapi_spec=spec,
    client=client,
    name=f"user-tool-{tool_id}",
    route_maps=[
        RouteMap(methods={"DELETE"}, mcp_type=MCPType.EXCLUDE),  # 安全：禁止 DELETE
    ]
)
```

### 8.3 工具市场数据模型

```sql
CREATE TABLE marketplace_tools (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publisher_id    UUID REFERENCES users(id),
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    description     TEXT,
    long_description TEXT,
    icon_url        TEXT,
    category        VARCHAR(50),           -- database | communication | dev-tools | ...
    tags            TEXT[],
    mcp_endpoint    TEXT NOT NULL,          -- MCP Server 地址
    auth_type       VARCHAR(20),           -- none | api_key | oauth2
    auth_config     JSONB,                 -- OAuth scopes, key format 等
    schema_json     JSONB,                 -- 工具列表及 schema
    install_count   INT DEFAULT 0,
    rating_avg      DECIMAL(2,1) DEFAULT 0,
    rating_count    INT DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'pending', -- pending | approved | rejected
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 9. 前端交互层（CopilotKit）

### 9.1 前端架构

```
src/
├── app/                          # Next.js App Router
│   ├── layout.tsx                # Root layout with CopilotKit provider
│   ├── (auth)/                   # 认证相关页面
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/              # 主控制台
│   │   ├── layout.tsx            # Dashboard layout
│   │   ├── page.tsx              # 概览页
│   │   ├── agents/               # Agent 管理
│   │   │   ├── page.tsx          # Agent 列表
│   │   │   ├── [id]/page.tsx     # Agent 详情/编辑
│   │   │   └── new/page.tsx      # 创建 Agent
│   │   ├── tools/                # 工具管理
│   │   ├── conversations/        # 对话历史
│   │   ├── marketplace/          # 工具市场
│   │   └── settings/             # 工作空间设置
│   └── (chat)/                   # Agent 对话界面
│       └── [agent_slug]/
│           └── page.tsx          # 全屏 Chat 界面
├── components/
│   ├── copilot/                  # CopilotKit 组件封装
│   │   ├── AgentChat.tsx         # Agent 对话主组件
│   │   ├── AgentSidebar.tsx      # Agent 侧边栏
│   │   └── GenerativeUI.tsx      # 动态 UI 渲染
│   ├── agent-builder/            # Agent 构建器
│   │   ├── ConfigPanel.tsx       # 配置面板
│   │   ├── ToolSelector.tsx      # 工具选择器
│   │   └── GraphVisualizer.tsx   # 执行流可视化
│   └── ui/                       # 通用 UI 组件
├── lib/
│   ├── api.ts                    # API 客户端
│   ├── auth.ts                   # 认证工具
│   └── store/                    # 状态管理
└── hooks/                        # React Hooks
```

### 9.2 CopilotKit 集成

**Root Layout — CopilotKit Provider**:

```tsx
// app/(chat)/[agent_slug]/layout.tsx
import { CopilotKit } from "@copilotkit/react-core";

export default function ChatLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: { agent_slug: string };
}) {
  return (
    <CopilotKit
      runtimeUrl={`${process.env.NEXT_PUBLIC_API_URL}/agui/${params.agent_slug}`}
      agent={params.agent_slug}
    >
      {children}
    </CopilotKit>
  );
}
```

**Agent Chat 组件**:

```tsx
// components/copilot/AgentChat.tsx
"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import { useCopilotAction } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

export function AgentChat() {
  // 注册前端 Action：允许 Agent 在前端渲染动态内容
  useCopilotAction({
    name: "render_chart",
    description: "Render a chart from data",
    parameters: [
      { name: "type", type: "string", enum: ["bar", "line", "pie"] },
      { name: "data", type: "object" },
      { name: "title", type: "string" },
    ],
    render: ({ args }) => <DynamicChart {...args} />,
  });

  useCopilotAction({
    name: "show_code_result",
    description: "Display code execution result with output and artifacts",
    parameters: [
      { name: "code", type: "string" },
      { name: "output", type: "string" },
      { name: "artifacts", type: "object[]" },
    ],
    render: ({ args }) => <CodeResultCard {...args} />,
  });

  return (
    <CopilotChat
      instructions="You are a helpful AI assistant."
      labels={{
        title: "AI Agent",
        initial: "How can I help you today?",
      }}
    />
  );
}
```

### 9.3 关键前端页面

| 页面 | 路由 | 功能 |
|------|------|------|
| Agent 列表 | `/agents` | 展示所有 Agent，支持搜索/筛选/排序 |
| Agent Builder | `/agents/new` | 创建/编辑 Agent，配置模型/工具/提示词/执行图 |
| Agent Chat | `/chat/{agent_slug}` | 全屏对话界面，流式响应，工具调用可视化 |
| 运行追踪 | `/agents/{id}/runs/{run_id}` | 展示 Agent 执行的完整链路（LLM调用→工具调用→结果） |
| 工具市场 | `/marketplace` | 浏览/安装 MCP 工具 |
| 工具配置 | `/tools/{id}` | 配置工具凭据、测试工具 |
| 使用统计 | `/settings/usage` | Token/工具调用/沙箱用量仪表盘 |

---

## 10. 代码执行沙箱

### 10.1 沙箱生命周期

```
                    ┌─────────┐
                    │  Pool   │  预热的空闲沙箱
                    │ (Warm)  │
                    └────┬────┘
                         │ acquire()
                         ▼
┌─────────┐      ┌──────────────┐      ┌──────────────┐
│  Init   │─────▶│   Running    │─────▶│   Cleanup    │
│(安装依赖)│      │ (执行代码)    │      │(收集产物,重置)│
└─────────┘      └──────────────┘      └──────┬───────┘
                                               │ release()
                                               ▼
                                        ┌──────────────┐
                                        │   回归池 或   │
                                        │   销毁        │
                                        └──────────────┘
```

### 10.2 安全约束

| 维度 | 限制 | 说明 |
|------|------|------|
| **CPU** | 10s wall time, 5s CPU time | 防止无限循环 |
| **内存** | 512MB (Free), 2GB (Pro) | OOM 直接终止 |
| **磁盘** | 100MB workspace | 仅 workspace 目录可写 |
| **网络** | 默认禁用；Pro 允许白名单域名 | 防止数据泄露 |
| **系统调用** | seccomp 白名单 | 禁止危险系统调用 |
| **进程** | 最多 10 子进程 | 防止 fork bomb |
| **包安装** | 仅允许白名单包 (Free) / 任意包 (Pro) | uv 安装，有缓存 |

### 10.3 uv 集成

```python
import subprocess

async def install_packages(sandbox_path: str, packages: list[str]) -> None:
    """使用 uv 在沙箱中安装 Python 包"""
    # uv 的优势：比 pip 快 10-100x，确定性解析
    cmd = [
        "uv", "pip", "install",
        "--python", f"{sandbox_path}/bin/python",
        "--cache-dir", "/shared/uv-cache",   # 跨沙箱共享缓存
        "--no-progress",
        *packages
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise PackageInstallError(stderr.decode())
```

---

## 11. 多租户与安全设计

### 11.1 多租户隔离模型

```
Platform
├── Tenant A (Workspace)
│   ├── Data: 行级隔离 (workspace_id WHERE clause)
│   ├── MCP Tools: namespace 隔离 (user/{workspace_id}/*)
│   ├── Sandbox: 进程级隔离 (gVisor/nsjail)
│   ├── API Keys: workspace 绑定
│   └── Billing: 独立计量
├── Tenant B (Workspace)
│   └── ...
└── Platform (Shared)
    ├── Builtin Tools: 共享只读
    ├── Marketplace: 共享目录，per-workspace 安装
    └── LLM Providers: 共享连接池
```

### 11.2 安全分层

| 层级 | 措施 |
|------|------|
| **网络层** | TLS 全覆盖、API Gateway WAF、DDoS 防护 |
| **认证层** | JWT (RS256) + Refresh Token、OAuth 2.0、API Key (bcrypt hash) |
| **授权层** | RBAC (Owner/Admin/Member/Viewer)、资源级权限检查 |
| **数据层** | 行级租户隔离、敏感字段 AES-256 加密、凭据独立加密存储 |
| **执行层** | gVisor/nsjail 沙箱、seccomp 系统调用过滤、cgroup 资源限制 |
| **审计层** | 所有 API 调用记录、Agent 运行链路追踪、数据访问日志 |

### 11.3 Credential Manager

```python
# 工具凭据安全存储
class CredentialManager:
    """管理用户为工具提供的凭据（API Key, OAuth Token 等）"""

    def __init__(self, encryption_key: bytes):
        self.cipher = Fernet(encryption_key)

    async def store(self, workspace_id: str, tool_id: str, credentials: dict) -> None:
        encrypted = self.cipher.encrypt(json.dumps(credentials).encode())
        await db.execute(
            "UPDATE tools SET credentials = $1 WHERE id = $2 AND workspace_id = $3",
            encrypted, tool_id, workspace_id
        )

    async def retrieve(self, workspace_id: str, tool_id: str) -> dict:
        row = await db.fetchrow(
            "SELECT credentials FROM tools WHERE id = $1 AND workspace_id = $2",
            tool_id, workspace_id
        )
        return json.loads(self.cipher.decrypt(row["credentials"]))
```

---

## 12. 部署架构

### 12.1 容器化部署（Docker Compose — 开发/小规模）

```yaml
# docker-compose.yml
services:
  # --- 前端 ---
  web:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      NEXT_PUBLIC_API_URL: http://api:8000
    depends_on: [api]

  # --- 后端 API ---
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://postgres:secret@db:5432/yoagent
      REDIS_URL: redis://redis:6379/0
      MCP_GATEWAY_URL: http://mcp-gateway:8100
      SANDBOX_MANAGER_URL: http://sandbox-manager:8200
    depends_on: [db, redis]

  # --- MCP 工具网关 ---
  mcp-gateway:
    build: ./mcp-gateway
    ports: ["8100:8100"]
    environment:
      DATABASE_URL: postgresql://postgres:secret@db:5432/yoagent

  # --- 沙箱管理器 ---
  sandbox-manager:
    build: ./sandbox
    privileged: true              # gVisor/nsjail 需要
    ports: ["8200:8200"]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - uv-cache:/shared/uv-cache

  # --- 基础设施 ---
  db:
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: yoagent
      POSTGRES_PASSWORD: secret
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data

volumes:
  pgdata:
  uv-cache:
  minio-data:
```

### 12.2 Kubernetes 生产部署（大规模）

```
┌─────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                        │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
│  │  Ingress (Traefik)                                         │ │
│  │  - TLS Termination                                         │ │
│  │  - Rate Limiting                                           │ │
│  └───────────┬─────────────────────────────────────────────── │
│              │                                                  │
│  ┌───────────▼───────┐                                         │
│  │   API Deployment  │  replicas: 3-10 (HPA)                  │
│  │   (FastAPI)       │  resources: 1 CPU, 2Gi RAM              │
│  └───────────────────┘                                         │
│                                                                  │
│  ┌────────────────────┐                                        │
│  │  MCP Gateway       │  replicas: 2-5 (HPA)                  │
│  │  Deployment        │  resources: 1 CPU, 2Gi RAM             │
│  └────────────────────┘                                        │
│                                                                  │
│  ┌────────────────────┐                                        │
│  │  Sandbox Pool      │  replicas: 5-20 (custom autoscaler)   │
│  │  StatefulSet       │  resources: 2 CPU, 4Gi RAM             │
│  │  (gVisor runtime)  │  securityContext: privileged            │
│  └────────────────────┘                                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  StatefulSets / Managed Services                       │    │
│  │  - PostgreSQL (CloudNativePG / RDS)                    │    │
│  │  - Redis (Sentinel / ElastiCache)                      │    │
│  │  - MinIO (or S3)                                       │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Observability Stack                                    │    │
│  │  - OpenTelemetry Collector (DaemonSet)                  │    │
│  │  - Grafana + Loki + Tempo + Prometheus                  │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 12.3 自动扩缩容策略

| 组件 | 指标 | 阈值 | 范围 |
|------|------|------|------|
| API Server | CPU / Request Rate | 70% CPU or 500 req/s | 3-10 pods |
| MCP Gateway | Active Connections | 100 concurrent | 2-5 pods |
| Sandbox Pool | 空闲沙箱数 | 最少保持 5 个空闲 | 5-20 pods |

---

## 13. 分阶段交付路线图

### Phase 1: MVP（8 周）

> **目标**: 最小可用产品，验证核心价值

| 周次 | 交付物 |
|------|--------|
| W1-2 | 项目脚手架、CI/CD、数据库迁移、Auth Service (JWT + GitHub OAuth) |
| W3-4 | Agent CRUD API、ReAct 编排模式、基础 LangGraph 运行时 |
| W5-6 | FastMCP 网关（内置工具：代码沙箱 + 网页搜索）、沙箱 MVP |
| W7-8 | CopilotKit 对话界面、AG-UI 端点、端到端流式对话 |

**MVP 交付范围**:
- [x] 用户注册/登录
- [x] 创建/编辑/删除 Agent
- [x] ReAct 模式运行
- [x] 内置代码沙箱工具
- [x] 流式对话 UI
- [ ] 不含：工具市场、计费、多 Agent、企业功能

### Phase 2: 增长（6 周）

> **目标**: 完善产品功能，支持付费

| 周次 | 交付物 |
|------|--------|
| W9-10 | 用户自定义工具（Python + OpenAPI）、工具凭据管理 |
| W11-12 | Plan-Execute 模式、Agent 版本管理、运行历史与追踪 |
| W13-14 | 计费系统 (Stripe)、使用配额、Free/Pro 区分 |

### Phase 3: 规模化（6 周）

> **目标**: 平台化能力，支持团队与企业

| 周次 | 交付物 |
|------|--------|
| W15-16 | 工具市场 MVP、Workspace 多成员、RBAC |
| W17-18 | Multi-Agent 协作模式、Agent 发布（API / Embed） |
| W19-20 | 企业功能（SSO、审计日志）、K8s 生产部署、SLA 监控 |

### Phase 4: 生态（持续）

- Agent 模板市场
- 社区工具贡献机制
- 私有化部署方案
- Agent-to-Agent 通信协议
- 向量存储与 RAG 深度集成

---

## 14. 非功能性需求

### 14.1 性能

| 指标 | 目标 |
|------|------|
| Agent 首 token 延迟 | < 2s (P99) |
| 工具调用延迟 | < 500ms (平台内置工具) |
| 沙箱冷启动 | < 3s |
| 沙箱热启动 | < 500ms |
| API 响应（非 Agent 调用） | < 200ms (P99) |
| 并发对话数 | 1000+ (单集群) |

### 14.2 可用性

| 指标 | 目标 |
|------|------|
| 平台整体可用性 | 99.9% |
| 计划内维护窗口 | < 4h/月 |
| RTO (恢复时间) | < 15min |
| RPO (数据丢失) | < 1min |

### 14.3 可观测性

```
                    OpenTelemetry Collector
                           │
               ┌───────────┼───────────┐
               ▼           ▼           ▼
         ┌──────────┐ ┌─────────┐ ┌──────────┐
         │  Tempo   │ │  Loki   │ │Prometheus│
         │ (Traces) │ │ (Logs)  │ │(Metrics) │
         └────┬─────┘ └────┬────┘ └────┬─────┘
              │            │           │
              └────────────┼───────────┘
                           ▼
                    ┌──────────────┐
                    │   Grafana    │
                    │  Dashboards  │
                    └──────────────┘
```

**关键仪表盘**:

| 仪表盘 | 指标 |
|--------|------|
| Platform Overview | 活跃用户、Agent 数、对话数、错误率 |
| Agent Performance | 各 Agent 成功率、平均响应时间、token 消耗 |
| Tool Health | 工具调用成功率、延迟分布、错误类型 |
| Sandbox Metrics | 池使用率、执行时间分布、OOM 率 |
| Billing & Usage | 按租户的 token/工具/沙箱用量 |

### 14.4 测试策略

| 层级 | 工具 | 覆盖目标 |
|------|------|----------|
| 单元测试 | pytest | > 80% 行覆盖率 |
| 集成测试 | pytest + testcontainers | API → DB → MCP 全链路 |
| E2E 测试 | Playwright | 核心用户流程 (创建 Agent → 对话 → 查看结果) |
| 负载测试 | Locust | 1000 并发对话 |
| 安全测试 | Trivy + Bandit + OWASP ZAP | CI 集成 |

---

## 15. 风险与缓解策略

| 风险 | 影响 | 概率 | 缓解策略 |
|------|------|------|----------|
| **LLM Provider 宕机** | 高 — 平台完全不可用 | 中 | 多 Provider 故障转移（OpenAI → Anthropic → Self-hosted） |
| **沙箱逃逸** | 极高 — 安全事故 | 低 | gVisor 双层隔离 + seccomp + 定期安全审计 |
| **LLM 成本失控** | 高 — 财务风险 | 中 | 硬性 token 上限 + 实时计量告警 + 按用户配额 |
| **MCP 工具兼容性** | 中 — 工具不可用 | 中 | 工具健康检查 + 自动降级 + 版本锁定 |
| **CopilotKit 升级破坏** | 中 — 前端需重构 | 低 | 封装 CopilotKit 组件、版本锁定、集成测试 |
| **冷启动延迟** | 中 — 用户体验差 | 高 | 沙箱预热池 + uv 包缓存 + LLM 连接池 |
| **数据泄露（跨租户）** | 极高 — 信任危机 | 低 | 行级隔离 + 自动化隔离测试 + 渗透测试 |

---

## 附录 A: 项目目录结构

```
yo-agent/
├── frontend/                     # Next.js + CopilotKit
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── hooks/
│   ├── package.json
│   └── next.config.js
├── backend/                      # FastAPI
│   ├── app/
│   │   ├── main.py               # FastAPI 入口
│   │   ├── api/                   # API 路由
│   │   │   ├── v1/
│   │   │   │   ├── agents.py
│   │   │   │   ├── tools.py
│   │   │   │   ├── conversations.py
│   │   │   │   └── auth.py
│   │   │   └── agui.py           # AG-UI 端点
│   │   ├── core/                  # 核心配置
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── models/                # SQLAlchemy 模型
│   │   ├── schemas/               # Pydantic schemas
│   │   ├── services/              # 业务逻辑
│   │   │   ├── agent_service.py
│   │   │   ├── tool_service.py
│   │   │   └── billing_service.py
│   │   └── runtime/               # Agent 运行时
│   │       ├── engine.py          # LangGraph 编排
│   │       ├── graphs/            # 预置图模式
│   │       │   ├── react.py
│   │       │   ├── plan_execute.py
│   │       │   └── multi_agent.py
│   │       └── checkpointer.py
│   ├── pyproject.toml
│   └── uv.lock
├── mcp-gateway/                   # FastMCP 工具网关
│   ├── gateway/
│   │   ├── main.py
│   │   ├── router.py
│   │   ├── middleware.py
│   │   └── builtin/               # 内置 MCP Servers
│   │       ├── code_sandbox.py
│   │       ├── file_ops.py
│   │       ├── web_search.py
│   │       └── vector_store.py
│   └── pyproject.toml
├── sandbox/                       # 沙箱管理器
│   ├── manager/
│   │   ├── main.py
│   │   ├── pool.py
│   │   ├── executor.py
│   │   └── security.py
│   └── pyproject.toml
├── infra/                         # 基础设施
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   ├── k8s/
│   │   ├── base/
│   │   └── overlays/
│   │       ├── dev/
│   │       └── prod/
│   └── terraform/                 # 云资源（可选）
├── migrations/                    # Alembic 数据库迁移
│   ├── alembic.ini
│   └── versions/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   └── PRD.md                     # 本文档
├── pyproject.toml                 # 根项目（workspace 管理）
└── README.md
```

## 附录 B: 技术决策记录 (ADR)

### ADR-001: 选择 AG-UI Protocol 而非直接 WebSocket

**背景**: CopilotKit 同时支持自定义 WebSocket 和 AG-UI 协议。
**决策**: 采用 AG-UI Protocol（通过 `add_langgraph_fastapi_endpoint`）。
**理由**:
- AG-UI 是 CopilotKit 的标准化 Agent-UI 交互协议，社区维护
- 内置了 LangGraph 状态同步、流式 token、工具调用事件等
- 减少自行维护 WebSocket 协议的成本

### ADR-002: FastMCP Gateway 而非直接工具调用

**背景**: Agent 可以直接调用 Python 函数作为工具。
**决策**: 所有工具调用通过 FastMCP Gateway 统一路由。
**理由**:
- 统一的工具发现、注册、认证机制
- 支持远程 MCP Server（用户自部署、市场工具）
- 中间件栈提供审计、限流、计量能力
- 支持 OpenAPI → MCP 自动转化，大幅降低工具接入成本

### ADR-003: gVisor 而非 Docker-in-Docker 作为沙箱

**背景**: 代码沙箱需要进程级隔离。
**决策**: 使用 gVisor (runsc) 作为沙箱隔离层。
**理由**:
- gVisor 在用户态实现了 Linux 内核接口，攻击面显著小于原生 Linux 内核
- 比完整 VM 轻量，启动更快
- Docker-in-Docker 安全性不足，且增加了复杂性
- 生产环境可降级为 nsjail（轻量替代方案）

---

*文档结束 — YoAgent AI Agent SaaS Platform PRD v1.0*
