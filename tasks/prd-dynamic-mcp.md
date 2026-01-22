# PRD: Dynamic MCP (动态 MCP 服务执行)

## Introduction

为 Thronglets ServiceBus 添加 Dynamic MCP 功能，让 Agent 能够动态发现并执行 App 提供的 MCP 工具。灵感来源于 [Docker Dynamic MCP](https://docs.docker.com/ai/mcp-catalog-and-toolkit/dynamic-mcp/)。

**核心理念**：Agent 无需预先知道所有 App 的工具，而是通过 `app__list()` 动态发现可用 App，然后通过 `app__execute()` 执行 App 的工具。ServiceBus 作为代理层，为每个 Agent 维护独立的 MCP ClientSession，确保状态隔离和上下文继承。

## Goals

- 支持 Agent 动态发现 App 提供的 MCP 工具列表
- 实现 `app__execute` 工具，通过 ServiceBus 代理调用 App 工具
- 每个 Agent 与 App 之间维护独立的 MCP ClientSession（状态隔离）
- 继承 Agent 当前 session 的所有信息（headers/metadata）到 App 调用
- 前端展示 App 的 tools 列表，方便用户了解 App 能力

## User Stories

### US-001: App 工具发现接口
**Description:** As a developer, I need an API to discover tools provided by an App so that Agents can know what capabilities are available.

**Acceptance Criteria:**
- [x] 添加 `GET /apps/{id}/tools` HTTP API，返回 App 的 MCP 工具列表
- [x] 工具列表包含：name, description, inputSchema
- [x] ServiceBus 连接 App 的 MCP endpoint 获取工具列表（带缓存）
- [x] 处理 App 不可达的错误情况
- [x] Typecheck/lint passes

### US-002: MCP 工具列表查询
**Description:** As an Agent, I want to discover App tools via MCP so that I can decide which tools to use.

**Acceptance Criteria:**
- [x] 添加 `app__list_tools(app_id)` MCP 工具
- [x] 返回 App 的所有可用工具及其 schema
- [x] 当 App 不健康或不可达时返回友好错误
- [x] Typecheck/lint passes

### US-003: Agent-App Session 管理器
**Description:** As a developer, I need a session manager to maintain independent MCP sessions between Agents and Apps.

**Acceptance Criteria:**
- [x] 创建 `dynamic_mcp.py` 模块，实现 `AgentAppSessionManager`
- [x] 为每个 (agent_id, app_id) 对维护独立的 MCP ClientSession
- [x] Session 支持懒加载（首次调用时创建）
- [x] Session 支持自动重连（连接断开时）
- [x] Session 支持过期清理（可配置超时）
- [x] Typecheck/lint passes

### US-004: 实现 app__execute 工具
**Description:** As an Agent, I want to execute App tools through ServiceBus so that I can use App capabilities without direct connection.

**Acceptance Criteria:**
- [x] 添加 `app__execute(app_id, tool_name, arguments)` MCP 工具
- [x] ServiceBus 代理调用 App 的 MCP 工具
- [x] 继承当前 Agent session 的 headers/metadata 到 App 调用
- [x] 返回 App 工具的执行结果（支持 text/image/resource 等类型）
- [x] 处理错误情况：App 不存在、工具不存在、执行失败
- [x] Typecheck/lint passes

### US-005: Session 上下文继承
**Description:** As a developer, I need to pass Agent context to App calls so that Apps can access relevant metadata.

**Acceptance Criteria:**
- [x] 从当前 MCP request 提取 Agent 的 headers/metadata
- [x] 将 Agent context 注入到 App MCP 调用中
- [x] 支持自定义 metadata 透传（如 trace_id, user_id 等）
- [x] Typecheck/lint passes

### US-006: 前端 App 工具展示
**Description:** As a user, I want to see App tools in the frontend so that I can understand App capabilities.

**Acceptance Criteria:**
- [x] 在 App 详情页面展示 tools 列表
- [x] 每个 tool 显示：name, description
- [x] 支持展开查看 tool 的 inputSchema
- [x] 工具加载状态显示（loading/error/success）
- [x] 遵循 frontend/style_guide.md 样式规范
- [x] Verify in browser using dev-browser skill

### US-007: 增强 app__list 返回工具摘要
**Description:** As an Agent, I want app__list to include tool summaries so that I can make informed decisions about which App to use.

**Acceptance Criteria:**
- [x] `app__list` 返回中增加 `tools_count` 字段
- [x] 可选参数 `include_tools: bool` 控制是否返回完整工具列表
- [x] 可选参数 `key_words: list[str]` 用来做搜索功能
- [x] 默认不返回完整工具列表（性能考虑）
- [x] Typecheck/lint passes

## Functional Requirements

- FR-1: 添加 `AgentAppSessionManager` 类，管理 Agent 与 App 之间的 MCP ClientSession
- FR-2: Session key 为 `(agent_id, app_id)` 元组，确保每个 Agent 对每个 App 有独立 session
- FR-3: Session 使用 `mcp` Python SDK 的 `ClientSession` 实现
- FR-4: HTTP API `GET /apps/{id}/tools` 返回 App 的工具列表，格式与 MCP tools/list 一致
- FR-5: MCP 工具 `app__list_tools(app_id)` 返回指定 App 的工具列表
- FR-6: MCP 工具 `app__execute(app_id, tool_name, arguments)` 代理执行 App 工具
- FR-7: `app__execute` 从当前请求上下文提取 `X-Agent-ID` 和其他 headers
- FR-8: `app__execute` 将 Agent context 作为 metadata 传递给 App MCP 调用
- FR-9: Session Manager 支持配置：session_ttl（默认 30 分钟）、max_sessions_per_agent（默认 10）
- FR-10: 前端 App 详情页展示工具列表，支持展开查看 schema

## Non-Goals

- 不实现工具的参数校验（由 App 自己校验）
- 不实现工具调用的权限控制（未来可扩展）
- 不实现工具调用的计费/配额（未来可扩展）
- 不实现工具的自动发现和注册（Agent 需显式查询）
- 不实现 SSE/WebSocket 流式响应（首版只支持同步调用）

## Design Considerations

### Session 管理架构

```
┌─────────────┐     ┌─────────────────────────────────────┐     ┌─────────────┐
│   Agent A   │────▶│         Thronglets ServiceBus       │────▶│   App 1     │
└─────────────┘     │                                     │     └─────────────┘
                    │  ┌─────────────────────────────┐    │
┌─────────────┐     │  │   AgentAppSessionManager    │    │     ┌─────────────┐
│   Agent B   │────▶│  │                             │    │────▶│   App 2     │
└─────────────┘     │  │  Sessions:                  │    │     └─────────────┘
                    │  │  (A, App1) -> ClientSession │    │
                    │  │  (A, App2) -> ClientSession │    │
                    │  │  (B, App1) -> ClientSession │    │
                    │  └─────────────────────────────┘    │
                    └─────────────────────────────────────┘
```

### Context 继承流程

```
Agent Request                    ServiceBus                         App
    │                               │                                │
    │  app__execute(app1, tool, {}) │                                │
    │  Headers: X-Agent-ID=agent-a  │                                │
    │  ──────────────────────────▶  │                                │
    │                               │                                │
    │                               │  1. Extract agent context      │
    │                               │  2. Get/Create session         │
    │                               │  3. Call tool with context     │
    │                               │  ──────────────────────────▶   │
    │                               │                                │
    │                               │  ◀──────────────────────────   │
    │                               │     Tool result                │
    │  ◀──────────────────────────  │                                │
    │     Result                    │                                │
```

### 前端工具展示

- 使用卡片式布局展示每个 tool
- tool name 作为标题，description 作为描述
- 点击展开显示 inputSchema（JSON 格式化展示）
- 参考现有 Agent 列表页面的样式

## Technical Considerations

- 使用 `mcp` Python SDK (`pip install mcp`) 创建 ClientSession
- Session 连接使用 `streamable-http` transport（与 App 的 mcp_endpoint 对接）
- 工具列表可缓存（TTL 5 分钟），减少重复请求
- Session 异常时自动清理并重建
- 考虑并发安全：使用 asyncio.Lock 保护 session 创建

### 依赖

```python
# 需要添加到 pyproject.toml
mcp >= 1.0.0  # MCP Python SDK
```

## Success Metrics

- Agent 可以在 2 次 MCP 调用内执行任意 App 工具（list_tools + execute）
- Session 创建时间 < 500ms
- 工具执行延迟 < 原始 App 延迟 + 100ms（代理开销）
- 前端工具列表加载时间 < 1s

## Open Questions

- Session 断开后是否需要通知 Agent？
- 是否需要支持工具调用的超时配置？
- 是否需要记录工具调用日志用于审计？
