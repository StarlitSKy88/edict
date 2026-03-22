# 🚀 Nick 优化版快速使用指南

## 📦 项目位置
`/workspace/nick-main/`

---

## ⚡ 快速启动

### 方式一: 一键启动 (推荐)
```bash
cd /workspace/nick-main
bash start.sh
```

### 方式二: 手动启动

```bash
# 1. 启动看板服务器
cd /workspace/nick-main/dashboard
python3 server.py --port 7891

# 2. 启动数据刷新 (新终端)
cd /workspace/nick-main
bash scripts/run_loop.sh
```

---

## 🛠️ 日常运维命令

### 健康检查
```bash
python3 scripts/health_check.py
```

### 一键优化 (测试+分析)
```bash
python3 scripts/optimize_all.py
```

### 边缘场景测试
```bash
python3 scripts/test_edge_cases.py
```

### 并发安全测试
```bash
python3 scripts/test_concurrency.py
```

### 数据备份
```bash
python3 scripts/backup.py
```

### 实时监控
```bash
python3 scripts/monitor.py
```

### 性能分析
```bash
python3 scripts/performance.py
```

### 边界保护 (自动修复)
```bash
python3 scripts/edge_guard.py
```

---

## 📊 访问地址

| 服务 | 地址 |
|------|------|
| 看板前端 | http://localhost:7891 |
| API接口 | http://localhost:7891/api/* |
| 健康检查 | http://localhost:7891/health |

---

## 📁 关键文件

| 文件 | 用途 |
|------|------|
| `data/tasks_source.json` | 任务源数据 |
| `data/live_status.json` | 实时状态 |
| `data/agent_config.json` | Agent配置 |

---

## 🔧 任务命令

### 创建任务
```bash
python3 scripts/kanban_update.py create JJC-20260318-001 "任务标题" Taizi 太子 太子 "任务描述"
```

### 更新状态
```bash
python3 scripts/kanban_update.py state JJC-20260318-001 Doing "开始执行"
```

### 查看统计
```bash
python3 scripts/kanban_update.py stats
```

---

## ✅ 优化版新增功能

| 功能 | 命令 |
|------|------|
| 健康检查 | `python3 scripts/health_check.py` |
| 边界保护 | `python3 scripts/edge_guard.py` |
| 边缘测试 | `python3 scripts/test_edge_cases.py` |
| 并发测试 | `python3 scripts/test_concurrency.py` |
| 性能分析 | `python3 scripts/performance.py` |
| 实时监控 | `python3 scripts/monitor.py` |
| 数据备份 | `python3 scripts/backup.py` |
| 一键优化 | `python3 scripts/optimize_all.py` |

---

## 📖 相关文档

- [与 OpenClaw 搭配指南](./OPENCLAW_INTEGRATION.md)
- [优化对比报告](./COMPARISON_DETAIL.md)
- [竞品分析](./COMPETITIVE_ANALYSIS.md)

---

**项目位置**: `/workspace/nick-main/`
