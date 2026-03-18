# 通用 Skill - 知识图谱

## 功能
构建和维护Agent间的知识图谱：
- 实体管理（Agent、任务、技能）
- 关系建模（上下级、协作、依赖）
- 图谱查询（路径、邻居、中心性）
- 推理能力（推荐、预测）

## 使用方法

```python
from scripts.tools.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()

# 添加实体
kg.add_entity("taizi", "agent", {"role": "太子", "capabilities": ["classifier"]})
kg.add_entity("zhongshu", "agent", {"role": "中书省"})

# 添加关系
kg.add_relation("taizi", "delegates_to", "zhongshu")
kg.add_relation("zhongshu", "reviews", "menxia")

# 查询图谱
agents = kg.query_entities("agent")
delegates = kg.get_relations("taizi", "delegates_to")

# 推理推荐
recommended = kg.recommend("zhongshu", "can_delegate_to")
```

## 核心能力

### 1. 实体管理
- Agent实体
- 任务实体
- 技能实体
- 关系实体

### 2. 关系建模
| 关系类型 | 说明 |
|----------|------|
| delegates_to | 任务委派 |
| reviews | 审核关系 |
| depends_on | 依赖关系 |
| collaborates_with | 协作关系 |
| manages | 管理关系 |

### 3. 图谱查询
- 查找直接关系
- 查找路径
- 计算中心性
- 识别社区

### 4. 推理能力
- 推荐相关Agent
- 预测任务流向
- 发现协作模式

## 与RAG的区别
- **RAG**: 语义相似检索
- **Knowledge Graph**: 关系推理检索

两者结合效果最佳！
