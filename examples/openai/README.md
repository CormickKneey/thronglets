# OpenAI Agents SDK + Thronglets Example

这个示例展示了如何使用 OpenAI Agents SDK 与 Thronglets ServiceBus 集成，实现两个 Agent 之间的猜数字游戏。

## 功能特性

- **Alice Agent**: 游戏发起者，负责发现其他 Agent 并发起猜数字游戏
- **Bob Agent**: 游戏参与者，负责接收消息并响应游戏请求
- **MCP 集成**: 使用 Model Context Protocol (MCP) 进行 Agent 间通信
- **自动发现**: Agent 可以自动发现总线上的其他 Agent
- **消息传递**: 通过 Thronglets ServiceBus 进行异步消息传递

## 前置要求

1. 启动 Thronglets ServiceBus:
```bash
cd /Users/ryanpu/ant/thronglets
uv run python main.py --port 8000
```

2. 设置 OpenAI API Key:
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

## 运行示例

```bash
cd /Users/ryanpu/ant/thronglets/examples/openai
uv run python agent.py
```

## 游戏流程

1. **注册阶段**: Alice 和 Bob 向 ServiceBus 注册自己
2. **发现阶段**: Alice 使用 `agent__list` 工具发现 Bob
3. **邀请阶段**: Alice 向 Bob 发送游戏邀请
4. **游戏阶段**: 
   - Alice 选择一个 0-50 之间的数字
   - Bob 进行猜测
   - Alice 提供"更高"/"更低"的提示
   - 游戏继续直到 Bob 猜中数字
5. **结束阶段**: Alice 宣布游戏结束

## 技术架构

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────┐
│   Alice     │    │ Thronglets      │    │    Bob      │
│   Agent     │◄──►│ ServiceBus      │◄──►│   Agent     │
│             │    │                 │    │             │
│ OpenAI      │    │ HTTP API        │    │ OpenAI      │
│ Agents SDK  │    │ MCP Server      │    │ Agents SDK  │
└─────────────┘    └─────────────────┘    └─────────────┘
```

### MCP 工具

每个 Agent 通过 MCP 连接获得以下工具：

- `agent__list`: 列出所有注册的 Agent
- `agent__whoami`: 获取当前 Agent 信息
- `message__send`: 发送消息给其他 Agent
- `message__receive`: 接收发送给自己的消息
- `task__*`: 任务管理相关工具

## 代码结构

- `agent.py`: 主要的示例代码
- `alice_card`: Alice Agent 的 ServiceBus 注册信息
- `bob_card`: Bob Agent 的 ServiceBus 注册信息
- `main()`: 主函数，设置连接并运行 Agent

## 自定义扩展

你可以基于这个示例扩展：

1. **更多 Agent**: 添加更多参与者
2. **复杂游戏**: 实现更复杂的游戏逻辑
3. **任务协作**: 实现工作流协作
4. **持久化**: 使用 Redis 存储游戏状态

## 故障排除

1. **连接失败**: 确保 Thronglets ServiceBus 正在运行
2. **API 错误**: 检查 OpenAI API Key 是否正确设置
3. **MCP 错误**: 确保 MCP Server 地址正确（默认: http://localhost:8000/bus/mcp）

## 依赖项

- `openai-agents[litellm]>=0.6.6`
- `fastapi>=0.115.0`
- `fastmcp>=2.0.0`
- `httpx>=0.27.0`

所有依赖已在项目根目录的 `pyproject.toml` 中配置。
