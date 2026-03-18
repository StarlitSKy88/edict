# 通用 Skill - 反思学习

## 功能
让Agent具备从经验中反思学习的能力：
- 任务复盘
- 失败分析
- 经验总结
- 改进建议

## 使用方法

```python
from scripts.tools.reflection import Reflector

reflector = Reflector()

# 反思任务
reflection = reflector.reflect(
    task_id="JJC-xxx",
    task_goal="完成代码开发",
    actual_result="延迟2天完成",
    errors=["低估工作量", "未考虑测试时间"],
    successes=["代码质量好", "按时提测"]
)

print(reflection.lessons)      # 经验教训
print(reflection.improvements) # 改进建议
print(reflection.patterns)     # 发现的模式
```

## 核心能力

### 1. 任务复盘
- 对比目标与实际结果
- 识别偏差原因
- 提取关键因素

### 2. 模式识别
- 从多个任务中发现规律
- 识别重复问题
- 总结成功模式

### 3. 改进建议
- 基于历史给出具体建议
- 量化改进预期
- 优先级排序

## 适用场景
- 任务完成后自动复盘
- 失败任务根因分析
- 团队经验传承
- 个人能力提升

## 与self-evolution的区别
- **reflection**: 侧重于"反思"和"分析"
- **self-evolution**: 侧重于"执行"和"优化"

两者配合使用效果最佳。
