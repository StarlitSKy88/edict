# Edict 三省六部 AI Agent 系统

## 环境要求

- Python >= 3.11
- Node.js >= 22 (用于OpenClaw)
- Git

## 快速安装

```bash
# 1. 克隆项目
git clone https://github.com/StarlitSKy88/edict.git
cd edict

# 2. 安装Python依赖
pip install -r requirements.txt

# 3. 安装Playwright (可选)
playwright install chromium

# 4. 配置OpenClaw
# 参考 OpenClaw 官方文档配置飞书/Telegram等
```

## 项目结构

```
edict/
├── agents/              # 11个Agent (三省六部)
│   ├── taizi/          # 太子 - 消息分拣
│   ├── zhongshu/       # 中书省 - 规划
│   ├── menxia/         # 门下省 - 审核
│   ├── shangshu/       # 尚书省 - 调度
│   ├── gongbu/         # 工部 - 技术
│   ├── hubu/          # 户部 - 财务
│   ├── bingbu/         # 兵部 - 安全
│   ├── xingbu/         # 刑部 - 合规
│   ├── libu/           # 礼部 - 文档
│   ├── libu_hr/        # 吏部 - 人事
│   ├── zaochao/       # 钦天监 - 观测
│   └── common/          # 通用Skills
├── scripts/             # 核心脚本
├── config/              # 配置文件
├── tests/               # 测试
└── data/               # 数据目录
```

## 使用方法

### 看板操作

```bash
# 创建任务
python3 scripts/kanban_update.py create JJC-001 "任务标题" Zhongshu 中书省 中书令

# 任务流转
python3 scripts/kanban_update.py flow JJC-001 "太子" "中书省" "转交"

# 完成任务
python3 scripts/kanban_update.py done JJC-001 "产出" "摘要"
```

### Agent Skills

```python
from scripts.agent_communicator import AgentCommunicator
from scripts.knowledge_graph import KnowledgeGraph
from scripts.ai_search import AISearch
```

## 通用Skills

| Skill | 功能 |
|-------|------|
| error-handler | 错误处理 |
| memory-recall | 记忆检索 |
| health-check | 健康检查 |
| self-evolution | 自主进化 |
| knowledge-graph | 知识图谱 |
| ai-search | AI搜索 |
| web-browsing | 网页浏览 |
| reflection | 反思学习 |

## 配置

### 环境变量

```bash
# 可选配置
export EDICT_ENV=production
export PERPLEXITY_API_KEY=your-key
export TAVILY_API_KEY=your-key
```

## 测试

```bash
# 运行测试
pytest tests/

# 运行特定测试
pytest tests/test_kanban.py -v
```

## 许可证

MIT License - see LICENSE file
