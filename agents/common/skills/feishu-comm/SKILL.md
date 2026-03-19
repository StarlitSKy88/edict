# 通用 Skill - 飞书通信

## 功能
让Agent通过飞书应用互相通信，实现异步消息传递。

## 架构

```
┌─────────────────────────────────────────┐
│              飞书平台                    │
├─────────────────────────────────────────┤
│  教皇App  │  红衣主教团App  │  枢机处App    │
└─────┬─────┴──────┬──────┴──────┬──────┘
      │             │             │
      └─────────────┴─────────────┘
                    │ 消息传递
                    ▼
      ┌─────────────────────────┐
      │   本地消息队列 (Redis)   │
      └─────────────────────────┘
```

## 优势
- **异步通信** - 消息不阻塞，存入队列
- **高可靠性** - 消息持久化，不丢失
- **解耦** - Agent之间不直接调用
- **容错** - 支持死信队列、重试机制

## 使用方法

### 1. 配置环境变量

```bash
# 每个Agent的飞书应用配置
export FEISHU_APP_ID="cli_xxxxx"
export FEISHU_APP_SECRET="xxxxx"
export FEISHU_VERIFICATION_TOKEN="xxxxx"

# Redis配置 (消息队列)
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
```

### 2. 初始化通信

```python
from scripts.feishu.agent_comm import FeishuAgentComm

# 初始化 (每个Agent独立实例)
comm = FeishuAgentComm(agent_id="cardinal")

# 注册另一个Agent的飞书ID
comm.register_agent("cardinal_office", "ou_xxxxx")
comm.register_agent("pope", "ou_xxxxx")

# 注册消息处理器
def handle_message(msg):
    print(f"收到消息: {msg.content}")
    # 处理逻辑

comm.register_handler("message", handle_message)
```

### 3. 发送消息

```python
# 发送消息给另一个Agent
comm.send_to_agent(
    to_agent="cardinal_office",
    content="请审核这个任务: ...",
    task_id="TASK-001",
    priority=0  # 0=普通, 1=高, 2=紧急
)
```

### 4. 处理队列

```python
# 在后台持续处理消息
comm.process_queue()
```

### 5. Webhook回调

```python
# 飞书Webhook回调处理
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.json
    result = comm.handle_webhook(payload)
    return jsonify(result)
```

## 配置多个飞书应用

### 为每个Agent创建飞书应用

1. 前往 https://open.feishu.cn/
2. 创建应用 -> 填写基本信息
3. 获取 `App ID` 和 `App Secret`
4. 配置权限:
   - `im:message:send_as` - 发送消息
   - `im:message:receive` - 接收消息
   - `im:chat:create` - 创建群聊
5. 发布应用

### 环境变量命名

```bash
# Agent 1: 教皇
export TAIZI_FEISHU_APP_ID="cli_xxx1"
export TAIZI_FEISHU_APP_SECRET="xxx1"

# Agent 2: 红衣主教团
export ZHONGSHU_FEISHU_APP_ID="cli_xxx2"
export ZHONGSHU_FEISHU_APP_SECRET="xxx2"

# Agent 3: 枢机处
export MENXIA_FEISHU_APP_ID="cli_xxx3"
export MENXIA_FEISHU_APP_SECRET="xxx3"
```

## 消息格式

### AgentMessage

```python
{
    "from_agent": "cardinal",      # 发送方Agent ID
    "to_agent": "cardinal_office",           # 接收方Agent ID
    "content": "请审核任务...",     # 消息内容
    "task_id": "TASK-001",         # 关联任务ID
    "timestamp": 1700000000.0,     # 时间戳
    "priority": 0                   # 优先级
}
```

## 故障处理

| 问题 | 解决方案 |
|-----|---------|
| 消息发送失败 | 自动存入队列，稍后重试 |
| Redis不可用 | 自动降级到内存队列 |
| 飞书API限流 | 指数退避重试 |
| 消息处理异常 | 移入死信队列(DLQ) |

## 监控

```bash
# 查看队列长度
python scripts/feishu/agent_comm.py --agent-id zhonshu --queue

# 查看死信队列
redis-cli > ZRANGE feishu:dlq:zhongshu 0 -1
```
