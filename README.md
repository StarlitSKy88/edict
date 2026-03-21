# Edict - 神圣帝国 AI Agent 系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen.svg" alt="Status">
</p>

## 📋 项目简介

Edict 是一个基于「神圣罗马帝国」官僚制度设计的多 Agent 协作系统。通过层级化的架构设计，实现 Agent 之间的有序协作、通信和任务流转。

每个 Agent 如同帝国中的各个职能部门，各司其职，协同工作。系统支持自主决策、自我学习、持续进化，是新一代企业级 AI Agent 解决方案。

## 🏛️ 组织架构

```
                              ┌─────────────┐
                              │    教皇     │
                              │   (Pope)    │
                              │ 最高决策者   │
                              └──────┬──────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
     ┌────────▼────────┐   ┌────────▼────────┐
     │   红衣主教团     │   │    主教团        │
     │  (Cardinal)     │   │   (Bishop)      │
     │     规划决策     │   │    执行调度     │
     └────────┬────────┘   └────────┬────────┘
              │                      │
     ┌────────▼────────┐   ┌────────▼─────────────────────┐
     │     枢机处       │   │                              │
     │(Cardinal Office)│   │         六部                 │
     │     审核审批     │   │                              │
     └─────────────────┘   └────────┬────────────────────┘
                                      │
    ┌─────────┬─────────┬─────────┬──────┴──────┬─────────┬─────────┐
    │ 工匠行会 │ 财政部  │ 骑士团  │ 宗教裁判所  │ 典礼部   │ 人事部   │
    │  Guild  │Treasury │ Knights │Inquisition│ Ceremony│ Personnel│
    │ 技术工程 │  财务   │  安全   │   合规    │  文档   │   人事   │
    └─────────┴─────────┴─────────┴───────────┴─────────┴─────────┘
                                            │
                                  ┌─────────▼─────────┐
                                  │    占星术士        │
                                  │  (Astrologer)     │
                                  │   观测监控        │
                                  └───────────────────┘
```

### 职能说明

| 职位 | ID | 职能 |
|-----|-----|------|
| **教皇** | pope | 最高决策者，负责全局规划、任务分发 |
| **红衣主教团** | cardinal | 规划决策，制定战略，任务拆解 |
| **主教团** | bishop | 执行调度，协调各部门，任务派发 |
| **枢机处** | cardinal_office | 审核审批，质量把控，风险评估 |
| **工匠行会** | guild | 技术开发，工程建设，系统架构 |
| **财政部** | treasury | 财务预算，成本控制，投资决策 |
| **骑士团** | knights | 安全防护，风险管理，安全保障 |
| **宗教裁判所** | inquisition | 合规审查，法务支持，规则制定 |
| **典礼部** | ceremony | 文档管理，外交接待，文化建设 |
| **人事部** | personnel | 人力资源，人才培养，绩效评估 |
| **占星术士** | astrologer | 观测监控，数据分析，趋势预测 |

---

## ✨ 核心特性

- 🏛️ **层级架构** - 严格的上下级关系，职责清晰
- 🔄 **异步通信** - 基于飞书/Redis消息队列，告别阻塞
- 🧠 **智能决策** - 自主任务拆解、风险评估
- 💡 **持续进化** - 自我学习、经验复用
- 🛡️ **企业级可靠性** - 熔断器、分布式锁、审计日志
- 📊 **可观测性** - Prometheus监控、成本分析

---

## 📦 核心模块

| 模块 | 文件 | 功能 |
|-----|------|------|
| 层级路由 | `scripts/hierarchical_router.py` | 保障组织架构不变 |
| Agent工厂 | `scripts/agent_factory.py` | 动态创建临时专家 |
| Swarm头脑风暴 | `scripts/swarm_orchestrator.py` | 多Agent协作思考 |
| 报告调度器 | `scripts/report_scheduler.py` | 日报/周报/月报自动 |
| 消息队列 | `scripts/message_queue.py` | 异步通信 |
| 事件总线 | `scripts/event_bus.py` | 发布/订阅 |
| 分布式锁 | `scripts/distributed_lock.py` | 防止竞争 |
| 熔断器 | `scripts/circuit_breaker.py` | 防止级联故障 |
| 审计日志 | `scripts/audit_logger.py` | 操作记录 |
| 权限系统 | `scripts/permission_system.py` | RBAC |
| 成本分析 | `scripts/cost_analyzer.py` | Token统计 |
| 监控指标 | `scripts/metrics.py` | Prometheus指标 |
| 配置中心 | `scripts/config_center.py` | 集中配置 |
| LLM网关 | `scripts/llm_gateway.py` | 统一模型服务层 |

---

## 🚀 安装配置

### 1. 环境要求

| 要求 | 版本 | 说明 |
|-----|------|------|
| Python | ≥ 3.11 | 主要运行环境 |
| Node.js | ≥ 22 | 用于OpenClaw |
| Git | 任意 | 代码管理 |
| Redis | ≥ 6.0 | 消息队列(可选) |
| PostgreSQL | ≥ 14 | 数据存储(可选) |

### 2. 克隆项目

```bash
# 克隆项目
git clone https://github.com/StarlitSKy88/edict.git
cd edict
```

### 3. 创建虚拟环境 (推荐)

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 4. 安装依赖

```bash
# 安装核心依赖
pip install -r requirements.txt

# 安装可选依赖
pip install redis prometheus-client psutil aiohttp fastapi uvicorn

# 安装开发依赖 (可选)
pip install pytest pytest-cov ruff mypy black
```

### 5. 环境配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
vim .env
```

#### 完整环境变量配置

```bash
# ═══════════════════════════════════════════════════════════════
# 必填配置
# ═══════════════════════════════════════════════════════════════

# 飞书应用配置 (每个Agent独立应用)
# 获取地址: https://open.feishu.cn/
export FEISHU_APP_ID="cli_xxxxxxxxxxxxxx"
export FEISHU_APP_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export FEISHU_VERIFICATION_TOKEN="xxxxxxxxxxxxxxxxxxxx"

# ═══════════════════════════════════════════════════════════════
# Redis配置 (消息队列)
# ═══════════════════════════════════════════════════════════════
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_DB="0"
export REDIS_PASSWORD=""

# ═══════════════════════════════════════════════════════════════
# LLM模型配置
# ═══════════════════════════════════════════════════════════════

# OpenAI (可选)
export OPENAI_API_KEY="sk-xxxxxxxxxxxx"

# OpenRouter (可选,免费模型)
# 获取地址: https://openrouter.ai/keys
export OPENROUTER_API_KEY="xxxxxxxxxxxx"

# MiniMax (默认)

### LLM Gateway 统一模型服务

项目内置 **LLM Gateway** 模块，提供统一的 LLM 服务：

```bash
# 查看状态
python scripts/llm_gateway.py
```

**功能特性：**
- 🔑 **统一配置** - 一次配置 API Key，所有 Agent 共享
- 🤖 **多模型支持** - 不同 Agent 可用不同模型
- ⚡ **快速切换** - 通过 Dashboard 随时更换 API Key 和模型

**配置文件：** `config/llm_config.yaml`

```yaml
llm:
  # 全局默认
  default_provider: "openrouter"
  default_model: "deepseek/deepseek-chat"
  
  # API Keys (支持环境变量)
  api_keys:
    openrouter: "${OPENROUTER_API_KEY}"
  
  # Agent 专属模型 (可选)
  agent_models:
    taizi: "anthropic/claude-sonnet-4-6"
    gongbu: "deepseek/deepseek-chat"
```

**API 端点：**

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/api/llm/status` | GET | 获取配置状态 |
| `/api/llm/set-global-model` | POST | 设置全局默认模型 |
| `/api/llm/set-agent-model` | POST | 设置 Agent 专属模型 |
| `/api/llm/set-api-key` | POST | 更新 API Key |
| `/api/llm/models` | POST | 获取可用模型列表 |
export MINIMAX_API_KEY="xxxxxxxxxxxx"

# ═══════════════════════════════════════════════════════════════
# AI搜索配置 (可选)
# ═══════════════════════════════════════════════════════════════

# Tavily - 获取地址: https://app.tavily.com/api-keys
export TAVILY_API_KEY="xxxxxxxxxxxx"

# ═══════════════════════════════════════════════════════════════
# 应用配置
# ═══════════════════════════════════════════════════════════════

# 应用环境
export EDICT_ENV="development"  # development | staging | production

# 应用端口
export EDICT_PORT="7891"

# 日志级别
export LOG_LEVEL="INFO"  # DEBUG | INFO | WARNING | ERROR

# 开启的功能
export ENABLE_METRICS="true"
export ENABLE_TRACING="true"
export ENABLE_AUDIT="true"

# ═══════════════════════════════════════════════════════════════
# Agent配置
# ═══════════════════════════════════════════════════════════════

# Agent通信超时 (秒)
export AGENT_TIMEOUT="30"
export AGENT_MAX_RETRIES="3"
export AGENT_HEARTBEAT_INTERVAL="30"

# 告警配置
export AGENT_ENABLE_ALERT="true"
export AGENT_ALERT_WEBHOOK=""

# ═══════════════════════════════════════════════════════════════
# 预算配置 (成本分析)
# ═══════════════════════════════════════════════════════════════
export DAILY_BUDGET="100.0"
export MONTHLY_BUDGET="3000.0"
```

### 6. 飞书应用配置 (详细步骤)

#### 6.1 创建应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 点击「创建应用」
3. 填写应用名称和描述
4. 创建后进入应用详情

#### 6.2 配置权限

在「应用权限」中添加以下权限：

| 权限名称 | 权限码 | 说明 |
|---------|--------|------|
| 发送消息 | `im:message:send_as` | 以应用身份发送消息 |
| 接收消息 | `im:message:receive` | 接收用户消息 |
| 创建群聊 | `im:chat:create` | 创建群聊 |
| 成员管理 | `im:chat:members` | 管理群成员 |
| 用户信息 | `contact:user.base:readonly` | 读取用户基本信息 |
| 用户邮箱 | `contact:user.email:readonly` | 读取用户邮箱 |

#### 6.3 发布应用

1. 在「版本管理与发布」中创建版本
2. 填写版本号和发布说明
3. 提交审核
4. 审核通过后发布

#### 6.4 获取配置

发布后获取以下信息：
- `App ID` - 应用ID
- `App Secret` - 应用密钥
- `Verification Token` - 回调验证令牌

### 7. Redis安装 (可选)

```bash
# Ubuntu/Debian
sudo apt install redis-server

# CentOS/RHEL
sudo yum install redis

# macOS
brew install redis

# 启动Redis
redis-server

# 或使用Docker
docker run -d -p 6379:6379 redis:alpine
```

### 8. 初始化数据

```bash
# 初始化目录结构
python3 scripts/init_directories.py

# 初始化配置
python3 scripts/init_config.py

# 验证安装
python3 scripts/health_check.py
```

---

## 🚀 启动

### 方式一: 一键启动 (推荐)

```bash
cd /path/to/edict
bash start.sh
```

### 方式二: 手动启动

```bash
# 1. 启动看板服务器
cd dashboard
python3 server.py --port 7891

# 2. 启动数据刷新 (新终端)
cd ..
bash scripts/run_loop.sh

# 3. 启动Agent (可选, 第三个终端)
python3 scripts/pope/main.py
```

### 方式三: Docker启动

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 📖 使用指南

### 1. 任务管理

```bash
# 创建任务
python3 scripts/kanban_update.py create \
    JJC-20260319-001 \
    "开发用户登录功能" \
    教皇 \
    教皇 \
    "任务描述内容"

# 更新状态
python3 scripts/kanban_update.py state \
    JJC-20260319-001 \
    Doing \
    "开始开发"

# 完成任务
python3 scripts/kanban_update.py done \
    JJC-20260319-001 \
    "产出: login.py" \
    "完成摘要"

# 查看统计
python3 scripts/kanban_update.py stats
```

### 2. 层级管理

```bash
# 查看层级
python3 scripts/hierarchical_router.py --list

# 查看层级树
python3 scripts/hierarchical_router.py --tree

# 检查路由权限
python3 scripts/hierarchical_router.py --check 工匠行会 财政部

# 添加新部门
python3 scripts/hierarchical_router.py --add \
    波斯国 \
    波斯国 \
    地方 \
    教皇

# 获取团队成员
python3 scripts/hierarchical_router.py --team 主教团
```

### 3. Agent工厂

```bash
# 创建临时专家 (24小时)
python3 scripts/agent_factory.py --create "金融专家" finance

# 创建临时专家 (自定义时间)
python3 scripts/agent_factory.py --create "安全专家" security --expires 48

# 创建项目组 (7天)
python3 scripts/agent_factory.py --project \
    "金融系统" \
    "finance,devops,security" \
    --days 7

# 列出临时Agent
python3 scripts/agent_factory.py --list

# 销毁Agent
python3 scripts/agent_factory.py --destroy temp_finance_xxxxx

# 清理过期Agent
python3 scripts/agent_factory.py --cleanup
```

### 4. Swarm头脑风暴

```bash
# 创建头脑风暴
python3 scripts/swarm_orchestrator.py --create \
    "AI发展方向" \
    红衣主教团 \
    主教团 \
    工匠行会 \
    --mode hybrid \
    --rounds 5

# 启动
python3 scripts/swarm_orchestrator.py --start swarm_xxxxx

# 查看列表
python3 scripts/swarm_orchestrator.py --list

# 导出结果
python3 scripts/swarm_orchestrator.py --export swarm_xxxxx markdown
```

### 5. 报告调度

```bash
# 手动生成日报
python3 scripts/report_scheduler.py --daily

# 手动生成周报
python3 scripts/report_scheduler.py --weekly

# 手动生成月报
python3 scripts/report_scheduler.py --monthly

# 列出报告
python3 scripts/report_scheduler.py --list

# 启动自动调度
python3 scripts/report_scheduler.py --start

# 停止调度
python3 scripts/report_scheduler.py --stop
```

### 6. 权限管理

```bash
# 检查权限
python3 scripts/permission_system.py --check 教皇 "agent:create"

# 授予权限
python3 scripts/permission_system.py --grant \
    工匠行会 \
    "task:execute" \
    教皇

# 分配角色
python3 scripts/permission_system.py --assign-role \
    占星术士 \
    manager \
    教皇

# 查看用户权限
python3 scripts/permission_system.py --perms 工匠行会

# 列出所有用户
python3 scripts/permission_system.py --list-users
```

### 7. 成本分析

```bash
# 查看成本统计
python3 scripts/cost_analyzer.py --stats

# 查看预算状态
python3 scripts/cost_analyzer.py --budget

# 查看模型使用
python3 scripts/cost_analyzer.py --models

# 导出报告
python3 scripts/cost_analyzer.py --export month

# 设置预算
python3 scripts/cost_analyzer.py --set-budget 200 5000
```

### 8. 监控指标

```bash
# 启动指标服务器
python3 scripts/metrics.py --server --port 9090

# 查看指标 (文本)
python3 scripts/metrics.py

# 查看系统指标
python3 scripts/metrics.py --system

# 查看Agent指标
python3 scripts/metrics.py --agent 工匠行会

# Prometheus格式
python3 scripts/metrics.py --prometheus

# JSON格式
python3 scripts/metrics.py --json
```

### 9. 运维命令

```bash
# 健康检查
python3 scripts/health_check.py

# 性能分析
python3 scripts/performance.py

# 实时监控
python3 scripts/monitor.py

# 数据备份
python3 scripts/backup.py

# 一键优化
python3 scripts/optimize_all.py
```

---

## 📁 项目结构

```
edict/
├── agents/                    # Agent定义
│   ├── pope/                # 教皇
│   ├── cardinal/            # 红衣主教团
│   ├── bishop/             # 主教团
│   ├── cardinal_office/    # 枢机处
│   ├── guild/              # 工匠行会
│   ├── treasury/           # 财政部
│   ├── knights/            # 骑士团
│   ├── inquisition/        # 宗教裁判所
│   ├── ceremony/           # 典礼部
│   ├── personnel/          # 人事部
│   ├── astrologer/         # 占星术士
│   └── common/            # 通用Skills
├── scripts/                # 核心脚本
│   ├── hierarchical_router.py
│   ├── agent_factory.py
│   ├── swarm_orchestrator.py
│   ├── report_scheduler.py
│   ├── message_queue.py
│   ├── event_bus.py
│   ├── distributed_lock.py
│   ├── circuit_breaker.py
│   ├── audit_logger.py
│   ├── permission_system.py
│   ├── cost_analyzer.py
│   ├── metrics.py
│   ├── config_center.py
│   └── ...
├── dashboard/              # 看板前端
├── data/                  # 数据目录
├── config/                # 配置文件
├── docker/                 # Docker配置
├── tests/                  # 测试
├── start.sh               # 启动脚本
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🔧 常见问题

### Q1: 启动失败，提示缺少依赖

```bash
# 重新安装依赖
pip install -r requirements.txt --upgrade
```

### Q2: Redis连接失败

```bash
# 检查Redis是否启动
redis-cli ping

# 启动Redis
redis-server

# 或使用Docker
docker run -d -p 6379:6379 redis:alpine
```

### Q3: 飞书消息收不到

1. 检查应用是否已发布
2. 检查回调URL是否配置正确
3. 检查App ID和Secret是否正确

### Q4: 权限不足

```bash
# 重置权限
python3 scripts/permission_system.py --load
```

---

## 📜 API Keys 获取

| 服务 | 用途 | 获取地址 |
|-----|------|---------|
| 飞书 | Agent通信 | open.feishu.cn |
| Tavily | AI搜索 | app.tavily.com |
| OpenRouter | 免费模型 | openrouter.ai |
| OpenAI | LLM | platform.openai.com |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

<p align="center">
  Made with ❤️ by Edict Team
</p>
