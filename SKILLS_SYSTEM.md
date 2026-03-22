# Nick 智能体技能系统 - 自主决策/学习/进化

## 一、Agent 与 Skills 映射

### 1.1 太子 (消息分拣)
| Skill | 功能 | 状态 |
|-------|------|------|
| classifier | 消息分类、意图识别 | ✅ |
| task-extractor | 任务提取 | ✅ |
| priority-judge | 紧急度判断 | ✅ |

### 1.2 中书省 (规划)
| Skill | 功能 | 状态 |
|-------|------|------|
| planner | 任务拆解、方案制定 | ✅ |
| risk-evaluator | 风险评估 | ✅ |
| resource-planner | 资源规划 | ✅ |

### 1.3 门下省 (审核)
| Skill | 功能 | 状态 |
|-------|------|------|
| reviewer | 方案审核 | ✅ |
| compliance-checker | 合规检查 | ✅ |
| feedback-generator | 反馈建议 | ✅ |

### 1.4 尚书省 (派发)
| Skill | 功能 | 状态 |
|-------|------|------|
| dispatcher | 任务派发 | ✅ |
| load-balancer | 负载均衡 | ✅ |
| progress-tracker | 进度跟踪 | ✅ |

### 1.5 六部 (执行)
| Agent | Skill | 功能 |
|-------|-------|------|
| 户部 | finance | 预算、成本 | ✅ |
| 吏部 | hr | 人员调配 | ✅ |
| 兵部 | military | 安全保障 | ✅ |
| 刑部 | justice | 审查裁决 | ✅ |
| 工部 | engineering | 技术实施 | ✅ |
| 钦天监 | observer | 观察分析 | ✅ |

---

## 二、通用 Skills

### 2.1 error-handler (错误处理)
- 错误分类与自动恢复
- 备用方案尝试
- 失败告警

### 2.2 memory-recall (记忆检索)
- 经验检索
- Context 注入
- 学习记录

### 2.3 health-check (健康检查)
- Agent 状态
- 任务进度
- 资源使用

### 2.4 self-evolution (自主进化)
- 自我决策
- 自我学习
- 自我优化

---

## 三、自主进化系统

### 3.1 自我决策
```python
# 决策流程
1. 分析任务需求
2. 评估可用资源
3. 选择最优方案
4. 评估风险
5. 制定执行计划
```

### 3.2 自我学习
```python
# 学习流程
1. 记录任务执行结果
2. 提取成功模式
3. 提取失败教训
4. 更新经验库
```

### 3.3 自我进化
```python
# 进化流程
1. 分析失败率
2. 识别问题模式
3. 生成优化建议
4. 更新提示词
5. 优化技能库
```

---

## 四、使用方法

### 4.1 调用 Skill
```bash
# 太子分类
python3 agents/pope/skills/classifier/main.py --message "帮我想营销方案"

# 中书省规划
python3 agents/cardinal/skills/planner/main.py --task "研发聊天机器人"

# 门下省审核
python3 agents/cardinal_office/skills/reviewer/main.py --plan "方案内容"
```

### 4.2 记忆系统
```bash
# 检索经验
python3 scripts/memory_system.py --retrieve --agent cardinal

# 记录学习
python3 scripts/memory_system.py --store pattern zhongshu "规划大项目要..."

# 生成 Context
python3 scripts/memory_system.py --compress --agent cardinal
```

### 4.3 自主进化
```bash
# 记录任务
python3 scripts/self_evolution.py --record task_id agent true 50000 0

# 查看统计
python3 scripts/self_evolution.py --stats zhongshu

# 获取建议
python3 scripts/self_evolution.py --recommend zhongshu
```

---

## 五、架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Nick 智能体系统                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐ │
│   │ 太子   │ → │ 中书省 │ → │ 门下省 │ → │ 尚书省 │ │
│   │classifier│   │ planner │   │ reviewer│   │dispatcher│ │
│   └─────────┘   └─────────┘   └─────────┘   └─────────┘ │
│        ↓            ↓            ↓            ↓          │
│   ┌─────────────────────────────────────────────────┐   │
│   │           通用 Skills 层                          │   │
│   │  error-handler │ memory-recall │ self-evolution │   │
│   └─────────────────────────────────────────────────┘   │
│                         ↓                               │
│   ┌─────────────────────────────────────────────────┐   │
│   │           自主进化引擎                            │   │
│   │  决策 → 学习 → 进化 → 优化 → 决策               │   │
│   └─────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、进化机制

### 6.1 触发条件
- 任务失败率 > 30%
- 执行时间过长
- 资源使用异常

### 6.2 进化动作
1. 分析失败模式
2. 生成优化建议
3. 更新 Agent 提示词
4. 优化 Skill 库
5. 记录进化历史

---

## 七、效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 任务完成率 | ~70% | ~90% |
| 平均执行时间 | 无优化 | 优化30% |
| 错误恢复 | 手动 | 自动 |
| 经验复用 | 无 | 智能推荐 |
