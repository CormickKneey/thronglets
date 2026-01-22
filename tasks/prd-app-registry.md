# PRD: App Registry (场景化 MCP 服务注册)

## Introduction

为 Thronglets ServiceBus 添加 App 注册功能。App 是面向特定场景（如炒股、游戏开发、数据分析等）的 MCP 服务，Agent 可以发现这些 App 并通过 MCP 协议与它们交互。这将 Thronglets 从单纯的 Agent 通信总线扩展为一个能力丰富的 Agent 生态平台。

**架构特点**：采用健康检查机制而非持久化存储，App 必须提供健康检查端点，系统通过探活来管理 App 生命周期，简化了持久化和 failover 的复杂度。

## Goals

- 允许 App（场景化 MCP 服务）主动注册到 ServiceBus
- 提供 App 列表查询功能，让 Agent 发现可用的场景服务
- 展示 App 的 MCP 接入地址，让 Agent 知道如何连接
- 通过健康检查自动发现和移除不健康的 App
- 无需持久化存储，降低运维复杂度

## User Stories

### US-001: 定义 App 数据模型
**Description:** As a developer, I need App data models so that Apps can be properly stored and retrieved.

**Acceptance Criteria:**
- [x] 在 `models.py` 中添加 `AppCard` 模型，包含：name, description, scenario (场景), mcp_endpoint, health_check_url (必填), icon_url (optional), tags (optional)
- [x] 添加 `RegisteredApp` 模型，包含：app_id, card, registered_at, last_seen_at, healthy (健康状态)
- [x] Typecheck/lint passes

### US-002: 实现 App 注册中心（内存）
**Description:** As a developer, I need an in-memory App registry with health check lifecycle management.

**Acceptance Criteria:**
- [x] 创建 `app_registry.py` 模块，实现内存注册表
- [x] 实现 `register`, `get`, `list`, `delete`, `find_by_name` 方法
- [x] 实现后台健康检查任务
- [x] 不健康的 App 自动从注册表移除
- [x] Typecheck/lint passes

### US-003: 添加 App 注册 HTTP API
**Description:** As an App provider, I want to register my App to ServiceBus so that Agents can discover it.

**Acceptance Criteria:**
- [x] `POST /apps` - 注册新 App 或续期，返回 app_id，必须提供 health_check_url
- [x] `GET /apps/{id}` - 获取单个 App 详情
- [x] `DELETE /apps/{id}` - 注销 App
- [x] 注册时自动生成 app_id (UUID)
- [x] 支持心跳续期（重复 POST 更新 last_seen_at）
- [x] Typecheck/lint passes

### US-004: 添加 App 列表 HTTP API
**Description:** As a client, I want to list all available Apps so that I can see the ecosystem.

**Acceptance Criteria:**
- [x] `GET /apps` - 返回所有已注册 App 列表
- [x] 支持 `healthy_only` 参数筛选健康的 App
- [x] 返回数据包含 app_id, name, description, scenario, mcp_endpoint, health_check_url, healthy
- [x] Typecheck/lint passes

### US-005: 添加 App MCP 工具
**Description:** As an Agent, I want MCP tools to discover Apps so that I can find and connect to scenario services.

**Acceptance Criteria:**
- [x] `app__list(healthy_only)` - 列出所有可用 App，返回名称、场景、描述、MCP 地址、健康状态
- [x] `app__get(app_id)` - 获取指定 App 的详细信息和接入方式
- [x] Typecheck/lint passes

## Functional Requirements

- FR-1: 添加 `AppCard` 模型，字段包括 name (str), description (str), scenario (str), mcp_endpoint (str), health_check_url (str, 必填), icon_url (str, optional), tags (list[str], optional)
- FR-2: 添加 `RegisteredApp` 模型，字段包括 app_id (str), card (AppCard), registered_at (datetime), last_seen_at (datetime), healthy (bool)
- FR-3: 内存注册表 `AppRegistry` 实现 App 的 CRUD 操作和健康检查生命周期管理
- FR-4: HTTP API `POST /apps` 接收 AppCard（含 health_check_url），返回 RegisteredApp
- FR-5: HTTP API `GET /apps` 返回所有 RegisteredApp 列表，支持 healthy_only 筛选
- FR-6: HTTP API `GET /apps/{id}` 返回单个 RegisteredApp
- FR-7: HTTP API `DELETE /apps/{id}` 删除指定 App
- FR-8: MCP 工具 `app__list` 返回 App 列表（面向 Agent 的简洁格式），支持 healthy_only 参数
- FR-9: MCP 工具 `app__get` 返回单个 App 详情，包含 MCP 接入地址和健康状态
- FR-10: 后台健康检查任务定期探活 App，连续失败超过阈值则自动移除

## Non-Goals

- 不包含 App 分类/搜索/过滤功能
- 不包含 App 推荐或排序算法
- 不包含 App 认证/授权机制
- 不包含 App 调用次数统计
- 不实现 Agent 自动连接 App 的逻辑（Agent 自行处理 MCP 连接）
- 不包含持久化存储（通过健康检查机制管理生命周期）

## Technical Considerations

- 使用 `app_registry.py` 模块独立管理 App 注册，不依赖 Storage 层
- 健康检查使用 httpx 异步客户端
- 健康检查参数可配置：检查间隔、超时时间、失败阈值
- MCP 工具命名遵循现有 `namespace__action` 模式
- App 与 Agent 是平行概念，共享 ServiceBus 但独立管理

## Success Metrics

- App 可以在 1 次 API 调用内完成注册
- Agent 可以通过 1 次 MCP 调用获取所有可用 App 列表
- 获取 App 接入方式（MCP endpoint）清晰明确
- 不健康的 App 自动从列表中移除

## Open Questions

- ~~App 是否需要类似 Agent 的过期清理机制？~~ **已实现**：通过健康检查自动清理
- 是否需要区分 App 的传输协议类型（streamable-http / stdio）？
