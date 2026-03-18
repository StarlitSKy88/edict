# 通用 Skill - 网页搜索

## 功能
让Agent具备全网搜索能力：
- 关键词搜索
- 获取搜索结果
- 内容摘要
- 批量搜索

## 使用方法

```python
from scripts.tools.web_search import WebSearch

searcher = WebSearch()

# 单次搜索
results = searcher.search("AI agent 2026 trends", num=10)

# 批量搜索
results = searcher.batch_search([
    "Python async best practices",
    "LLM agent framework comparison"
])

# 获取结果
for r in results:
    print(r.title, r.url, r.snippet)
```

## 适用场景
- 调研任务
- 信息收集
- 趋势分析
- 竞品分析

## 注意事项
1. 遵守搜索平台规则
2. 合理控制请求频率
3. 结果需要人工验证
