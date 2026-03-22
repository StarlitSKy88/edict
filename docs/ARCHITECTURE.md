# Edict 系统架构文档

**版本**: 3.0  
**更新日期**: 2026-03-22

---

## 一、系统概述

Edict（三省六部）是一个基于 OpenClaw 构建的多 Agent 协作系统，采用中国古代官僚制度设计，实现 Agent 之间的有序协作和任务流转。

### 核心特性
- 🏛️ 层级架构 - 严格的上下级关系
- 🔄 异步通信 - 基于消息队列
- 🧠 智能决策 - 自主任务拆解
- 📊 可观测性 - 实时看板监控

---

## 二、架构设计

### 2.1 整体架构

```
用户 → 飞书/Telegram → OpenClaw Gateway
                                ↓
                    ┌───────────┴───────────┐
                    ↓                       ↓
               教皇 (taizi)          外部API服务
                    ↓                       
              红衣主教团 (zhongshu)      
                    ↓                       
                   枢机处 (menxia)         
                    ↓                       
                  主教团 (shangshu)        
                    ↓                       
         ┌─────────┼─────────┬───────────┐
         ↓         ↓         ↓           ↓
       户部     礼部       兵部        工部...
```

### 2.2 Agent 层级

| 层级 | Agent | 职责 |
|------|-------|------|
| L0 | 教皇 | 最高决策者，消息分拣 |
| L1 | 红衣主教团 | 规划决策 |
| L2 | 主教团 | 执行调度 |
| L3 | 枢机处 | 审核审批 |
| L4 | 六部 | 专项执行 |

---

## 三、核心模块

### 3.1 任务流转

```
Pending → Taizi → Zhongshu → Menxia → Assigned → Doing → Review → Done
```

### 3.2 数据流

1. **任务创建**: 用户发送消息 → 教皇分拣
2. **任务规划**: 红衣主教团拆解任务
3. **任务审核**: 枢机处质量把控
4. **任务执行**: 主教团派发 → 六部执行
5. **任务完成**: 礼部汇总 → 回奏用户

### 3.3 消息队列

- **Redis 模式**: 生产环境推荐
- **内存模式**: 开发/测试环境

---

## 四、部署架构

### 4.1 单机部署

```
┌─────────────────────────────┐
│      OpenClaw Gateway       │
│         (Port 7891)        │
├─────────────────────────────┤
│  Dashboard (React)         │
│  API Server (Python)        │
│  Scripts (Task Runner)      │
└─────────────────────────────┘
```

### 4.2 生产部署

```
                    ┌──────────────────┐
                    │   Load Balancer  │
                    └────────┬─────────┘
                             │
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Gateway 1  │    │  Gateway 2  │    │  Gateway 3  │
│   (Node1)   │    │   (Node2)   │    │   (Node3)   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            ↓
              ┌─────────────────────────┐
              │   Redis (消息队列)      │
              │   PostgreSQL (数据)    │
              └─────────────────────────┘
```

---

## 五、API 接口

### 5.1 任务管理

| 接口 | 方法 | 说明 |
|-----|------|------|
| `/api/tasks` | GET | 获取任务列表 |
| `/api/tasks` | POST | 创建任务 |
| `/api/tasks/:id` | PUT | 更新任务 |
| `/api/tasks/:id` | DELETE | 删除任务 |

### 5.2 模型管理

| 接口 | 方法 | 说明 |
|-----|------|------|
| `/api/llm/status` | GET | 获取LLM配置 |
| `/api/llm/set-global-model` | POST | 设置全局模型 |
| `/api/llm/set-agent-model` | POST | 设置Agent模型 |

---

## 六、扩展开发

### 6.1 新增 Agent

1. 在 `data/agent_config.json` 添加配置
2. 创建 `agents/{agent_id}/SOUL.md`
3. 配置权限和路由规则
4. 重启 Gateway

### 6.2 新增 Skill

1. 在 `agents/common/skills/` 创建目录
2. 编写 `SKILL.md` 文档
3. 实现 Python 模块
4. 在 Agent SOUL.md 中注册

---

## 七、监控运维

### 7.1 健康检查

```bash
python3 scripts/health_check.py
```

### 7.2 日志查看

```bash
# 实时日志
python3 scripts/monitor.py

# 错误日志
grep ERROR logs/*.log
```

### 7.3 性能监控

- Prometheus 指标: `/api/metrics`
- Dashboard: 看板实时状态

---

## 八、常见问题

### Q1: 如何切换模型?

在 `config/llm_config.yaml` 中修改 `default_model`，或使用 Dashboard 面板切换。

### Q2: 如何添加新渠道?

在 `channels` 配置中添加新渠道配置（飞书/Telegram/Signal等）。

### Q3: 数据如何持久化?

生产环境建议使用 PostgreSQL + Redis，运行迁移脚本：
```bash
python3 edict/migration/migrate_json_to_pg.py
```

---

*文档版本: 3.0*
