# 通用 Skill - 错误处理与自动恢复

## 触发条件
当 Agent 执行出错时自动调用

## 功能

### 1. 错误分类
- 网络错误 → 重试
- 权限错误 → 降级处理
- 超时错误 → 延长超时重试
- 未知错误 → 记录并告警

### 2. 自动恢复
- 尝试备用方案
- 回退到上一步
- 标记任务阻塞

### 3. 告警通知
- 失败告警到飞书
- 记录错误日志
- 触发人工介入

## 使用方法

```python
from skills.error_handler import ErrorHandler

handler = ErrorHandler()
result = handler.handle(error, context)
# result: {action: "retry|fallback|escalate|block", message: "..."}
```

## 错误代码

| 代码 | 含义 | 处理 |
|------|------|------|
| E001 | 网络超时 | 重试3次 |
| E002 | 权限不足 | 降级处理 |
| E003 | 资源不存在 | 创建或跳过 |
| E004 | 任务阻塞 | 标记并告警 |
| E005 | 未知错误 | 记录并升级 |

## 集成

在每个 Agent 的 SOUL 中添加：
```
当遇到错误时，使用 error-handler skill 处理。
如果无法恢复，标记任务为 Blocked 并通知教皇。
```
