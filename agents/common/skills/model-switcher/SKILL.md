# 通用 Skill - 模型切换器

## 功能
让用户可以自行配置 OpenRouter API Key 并自由选择模型：
- 设置用户的 OpenRouter API Key
- 查看可用模型列表
- 切换当前使用的模型
- 切换单个 Agent 的模型

## 使用方法

### 1. 设置 API Key
```python
from scripts.llm_gateway import LLMGateway

llm = LLMGateway()
llm.set_api_key("openrouter", "your-openrouter-api-key")
```

### 2. 查看可用模型
```python
models = llm.list_models()
for m in models:
    print(f"{m.id} - {m.name} ({m.price})")
```

### 3. 切换全局默认模型
```python
llm.set_default_model("deepseek/deepseek-chat")
# 或其他模型如:
# llm.set_default_model("qwen/qwen-2.5-7b-instruct")
# llm.set_default_model("anthropic/claude-sonnet-4-6")
# llm.set_default_model("google/gemini-2.0-flash-exp")
```

### 4. 切换单个 Agent 的模型
```python
llm.set_agent_model("gongbu", "deepseek/deepseek-chat")
llm.set_agent_model("zhongshu", "anthropic/claude-sonnet-4-6")
```

### 5. 获取当前配置
```python
config = llm.get_config()
print(f"默认模型: {config.default_model}")
print(f"当前 Agent 模型:")
for agent_id, model in config.agent_models.items():
    print(f"  {agent_id}: {model}")
```

## 适用场景
- 用户想使用自己的 API Key
- 需要为不同 Agent 分配不同模型
- 想切换到特定模型进行测试
- 想使用免费模型降低成本

## 常用免费模型 (OpenRouter)
| 模型 ID | 名称 | 价格 |
|---------|------|------|
| deepseek/deepseek-chat | DeepSeek Chat | 免费 |
| qwen/qwen-2.5-7b-instruct | Qwen 2.5 | 免费 |
| google/gemini-2.0-flash-exp | Gemini 2.0 | 免费 |
| mistralai/mistral-7b-instruct | Mistral 7B | 免费 |

## 注意事项
1. API Key 需要从 https://openrouter.ai/keys 获取
2. 免费模型有调用限制，建议用于测试
3. 生产环境建议使用付费模型
4. 模型切换后需要重启 Gateway 生效
