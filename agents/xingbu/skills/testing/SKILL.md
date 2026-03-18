# 刑部 Skill - 自动化测试

## 功能
自动化测试能力：
- 单元测试生成
- 集成测试
- 测试执行
- 结果评估

## 使用方法

```python
from scripts.tools.auto_tester import AutoTester

tester = AutoTester()

# 生成单元测试
test_cases = tester.generate_unit_tests("def add(a, b): return a + b")

# 执行测试
results = tester.run_tests("test_file.py")

# 评估结果
evaluation = tester.evaluate(results)
print(evaluation.pass_rate, evaluation.issues)
```

## 核心能力

### 1. 单元测试
- 基于代码分析生成测试用例
- 边界条件覆盖
- 异常情况覆盖

### 2. 集成测试
- API测试
- 工作流测试
- 端到端测试

### 3. 测试执行
- 自动运行测试
- 并行执行
- 失败重试

### 4. 结果评估
- 通过率统计
- 问题分类
- 改进建议

## 适用场景
- 代码开发完成后自动生成测试
- 回归测试
- CI/CD集成
- Prompt质量评估

## 与其他Skills的关系
- **engineering**: 开发代码 → 交给 testing 测试
- **testing**: 生成测试 → 交给 justice 审查
