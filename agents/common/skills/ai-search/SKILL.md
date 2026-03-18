# 通用 Skill - AI搜索

## 功能
基于Perplexity的AI增强搜索：
- 自然语言提问
- 实时网络信息
- 引用来源标注
- 中文友好

## 使用方法

```python
from scripts.tools.ai_search import AISearch

searcher = AISearch(provider="perplexity")

# 搜索
results = searcher.search("2026年AI Agent最新趋势")
for r in results:
    print(f"标题: {r.title}")
    print(f"来源: {r.url}")
    print(f"摘要: {r.content[:200]}")
```

## 支持的Provider

| Provider | 特点 |
|----------|------|
| perplexity | AI原生搜索，答案质量最高 |
| tavily | 专为Agent设计，结构化结果 |

## 适用场景
- 深度研究
- 事实核查
- 趋势分析
- 技术调研
