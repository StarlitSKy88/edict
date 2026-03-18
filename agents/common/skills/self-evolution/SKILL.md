# 自主进化 Skill - 自我优化

## 核心能力

### 1. 自我决策
- 分析任务需求
- 选择最优方案
- 评估风险

### 2. 自我学习
- 从成功中提取模式
- 从失败中学习教训
- 积累经验

### 3. 自我进化
- 优化执行策略
- 改进提示词
- 更新技能库

## 使用

```python
from skills.self_evolution import SelfEvolution

evo = SelfEvolution()

# 决策
decision = evo.decide(task, options)

# 学习
evo.learn(task_id, success, lessons)

# 进化
evo.evolve(agent_id)
```

## 进化规则

1. 每次任务后评估效果
2. 提取成功模式到 Pattern
3. 更新 Agent 提示词
4. 优化 Skills 库
