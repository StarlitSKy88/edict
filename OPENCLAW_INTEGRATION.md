# Edict 与 OpenClaw 搭配使用指南

## 📐 一、关系架构

```
┌─────────────────────────────────────────────────────────────┐
│                     用户 (飞书/Telegram/微信)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    OpenClaw Gateway                          │
│         (消息路由、插件管理、Agent调度)                         │
│  • 消息接收与分发                                           │
│  • 插件加载 (飞书/钉钉/Telegram)                            │
│  • Agent 会话管理                                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Edict 三省六部系统                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  太子 (消息分拣)  ←→  OpenClaw Agent           │    │
│  │  中书省 (规划)    ←→  OpenClaw Agent           │    │
│  │  门下省 (审核)    ←→  OpenClaw Agent           │    │
│  │  尚书省 (派发)    ←→  OpenClaw Agent           │    │
│  │  六部 (执行)      ←→  OpenClaw Agent           │    │
│  └─────────────────────────────────────────────────────┘    │
│                    │                                        │
│                    ▼                                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Edict 看板 (dashboard/server.py)                 │    │
│  │  • 实时任务状态展示                                  │    │
│  │  • 流转历史追溯                                     │    │
│  │  • 绩效统计                                        │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 二、工作流程

### 2.1 消息接收流程

```
用户发送消息
    │
    ▼
OpenClaw Gateway (接收消息)
    │
    ▼
太子 Agent (分拣消息)
    │
    ▼
判断: 是否是需要处理的任务?
    │
    ├── 是 → 创建任务 → 写入 tasks_source.json
    │
    └── 否 → 直接回复用户
```

### 2.2 任务处理流程

```
任务创建
    │
    ▼
中书省 (起草方案)
    │
    ▼
门下省 (审核封驳)
    │
    ▼
    ├── 通过 → 尚书省派发
    │
    └── 驳回 → 返回中书省重做
    │
    ▼
尚书省 (派发六部)
    │
    ▼
六部 (并行执行)
    │
    ▼
    ├── 完成 → 尚书省汇总
    │
    └── 阻塞 → 太子处理
    │
    ▼
任务完成 → 更新看板
```

---

## 🛠️ 三、配置步骤

### 3.1 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| OpenClaw | 最新版 | 必须安装 |
| Python | 3.9+ | 运行脚本 |
| Redis | 6.0+ | 事件总线(可选) |
| PostgreSQL | 14+ | 数据存储(可选) |

### 3.2 安装步骤

```bash
# 1. 安装 OpenClaw
curl -fsSL https://openclaw.ai/install.sh | bash

# 2. 克隆 Edict 项目
git clone https://github.com/cft0808/edict.git
cd edict

# 3. 运行安装脚本
bash install.sh

# 4. 启动看板
cd dashboard
python3 server.py --port 7891
```

### 3.3 OpenClaw 配置

在 `openclaw.json` 中配置 Agent:

```json
{
  "agents": {
    "pope": {
      "model": "anthropic/claude-sonnet-4-6",
      "skills": ["edict-basic"]
    },
    "cardinal": {
      "model": "anthropic/claude-sonnet-4-6", 
      "skills": ["edict-planning"]
    }
  }
}
```

---

## 🔌 四、集成方式

### 4.1 飞书集成 (推荐)

```
飞书群 → OpenClaw 插件 → Gateway → Edict Agent
                    │
                    └── 太子 Agent 接收消息
```

配置:
```bash
openclaw config set channels.feishu.app_id "你的AppID"
openclaw config set channels.feishu.app_secret "你的Secret"
```

### 4.2 Telegram 集成

```
Telegram Bot → OpenClaw → Gateway → Edict Agent
```

配置:
```bash
openclaw config set channels.telegram.bot_token "你的Token"
```

---

## 📊 五、数据流

### 5.1 任务数据流

```
用户消息
    │
    ▼
kanban_update.py create
    │
    ▼
tasks_source.json (JSON 存储)
    │
    ├──▶ 太子分拣
    ├──▶ 中书省规划
    ├──▶ 门下省审核
    ├──▶ 尚书省派发
    └──▶ 六部执行
    
    │
    ▼
refresh_live_data.py
    │
    ▼
live_status.json
    │
    ▼
dashboard/server.py (API)
    │
    ▼
前端看板展示
```

### 5.2 关键数据文件

| 文件 | 用途 |
|------|------|
| `tasks_source.json` | 任务源数据 |
| `live_status.json` | 实时状态 |
| `agent_config.json` | Agent配置 |
| `officials_stats.json` | 官员统计 |

---

## ⚡ 六、快速命令

### 6.1 日常运维

```bash
# 健康检查
python3 scripts/health_check.py

# 启动看板
cd dashboard && python3 server.py

# 启动数据刷新
bash scripts/run_loop.sh

# 备份数据
python3 scripts/backup.py
```

### 6.2 Agent 调用

```bash
# 通过 OpenClaw 调用
openclaw agent --agent pope -m "请分析这个需求..."

# 直接调用脚本
python3 scripts/kanban_update.py create JJC-20260318-001 "新任务" Taizi 太子 太子 "任务描述"
```

---

## 🎯 七、注意事项

### 7.1 必须配置

1. **OpenClaw Gateway** 正常运行
2. **飞书/Telegram 插件** 已安装
3. **数据目录** 有写权限
4. **网络** 可访问 AI 服务

### 7.2 常见问题

| 问题 | 解决 |
|------|------|
| 消息不响应 | 检查 OpenClaw 状态 |
| 任务不更新 | 检查 JSON 文件权限 |
| 看板空白 | 运行 refresh_live_data.py |
| Agent 无响应 | 检查模型配置 |

---

## 🔗 八、相关文档

- [OpenClaw 官方文档](https://docs.openclaw.ai)
- [Edict 架构文档](docs/task-dispatch-architecture.md)
- [飞书插件安装](https://github.com/cft0808/edict#飞书机器人部署)

---

**总结**: Edict 依赖 OpenClaw 作为消息网关和 Agent 调度底座,Edict 在此基础上构建了三省六部的任务流转和可视化看板。两者是上层应用与底层平台的关系。
