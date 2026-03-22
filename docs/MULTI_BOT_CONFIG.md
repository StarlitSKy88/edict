# Edict 多飞书机器人架构配置指南

本文档说明如何为 Edict 三省六部架构配置多飞书机器人，实现专业化分工和记忆隔离。

## 架构说明

### 目标架构

```
用户 → 多个飞书机器人 → 独立Agent → 独立工作空间
```

每个 Agent 成为独立的飞书机器人，拥有：
- 独立的飞书应用
- 独立的工作空间（记忆隔离）
- 独立的配置文件

## 机器人规划

根据三省六部架构，配置以下机器人：

| Agent ID | 职位 | 飞书机器人名称 | 职能 |
|---------|------|--------------|------|
| taizi | 教皇 | 教皇 | 最高决策，全局规划 |
| zhongshu | 红衣主教团 | 中书省 | 规划决策，战略制定 |
| shangshu | 主教团 | 尚书省 | 执行调度，任务派发 |
| menxia | 枢机处 | 门下省 | 审核审批，质量把控 |
| gongbu | 工匠行会 | 工部 | 技术开发，工程建设 |
| hubu | 财政部 | 户部 | 财务预算，成本控制 |
| bingbu | 骑士团 | 兵部 | 安全防护，风险管理 |
| xingbu | 宗教裁判所 | 刑部 | 合规审查，法务支持 |
| libu | 典礼部 | 礼部 | 文档管理，外交接待 |
| libu_hr | 人事部 | 吏部 | 人力资源，人才培养 |
| zaochao | 占星术士 | 钦天监 | 观测监控，数据分析 |

## 配置文件示例

### openclaw.json 配置

```json
{
  "agents": {
    "list": [
      {
        "id": "taizi",
        "name": "教皇",
        "default": true,
        "workspace": "~/.openclaw/workspace-taizi",
        "model": {
          "primary": "minimax/MiniMax-M2.1"
        }
      },
      {
        "id": "zhongshu",
        "name": "中书省",
        "workspace": "~/.openclaw/workspace-zhongshu",
        "model": {
          "primary": "minimax/MiniMax-M2.1"
        }
      },
      {
        "id": "shangshu",
        "name": "尚书省",
        "workspace": "~/.openclaw/workspace-shangshu",
        "model": {
          "primary": "minimax/MiniMax-M2.1"
        }
      },
      {
        "id": "menxia",
        "name": "门下省",
        "workspace": "~/.openclaw/workspace-menxia",
        "model": {
          "primary": "minimax/MiniMax-M2.1"
        }
      },
      {
        "id": "gongbu",
        "name": "工部",
        "workspace": "~/.openclaw/workspace-gongbu",
        "model": {
          "primary": "minimax/MiniMax-M2.1"
        }
      },
      {
        "id": "hubu",
        "name": "户部",
        "workspace": "~/.openclaw/workspace-hubu",
        "model": {
          "primary": "minimax/MiniMax-M2.1"
        }
      },
      {
        "id": "bingbu",
        "name": "兵部",
        "workspace": "~/.openclaw/workspace-bingbu",
        "model": {
          "primary": "minimax/MiniMax-M2.1"
        }
      },
      {
        "id": "xingbu",
        "name": "刑部",
        "workspace": "~/.openclaw/workspace-xingbu",
        "model": {
          "primary": "minimax/MiniMax-M2.1"
        }
      },
      {
        "id": "libu",
        "name": "礼部",
        "workspace": "~/.openclaw/workspace-libu",
        "model": {
          "primary": "minimax/MiniMax-M2.1"
        }
      },
      {
        "id": "libu_hr",
        "name": "吏部",
        "workspace": "~/.openclaw/workspace-libu_hr",
        "model": {
          "primary": "minimax/MiniMax-M2.1"
        }
      },
      {
        "id": "zaochao",
        "name": "钦天监",
        "workspace": "~/.openclaw/workspace-zaochao",
        "model": {
          "primary": "minimax/MiniMax-M2.1"
        }
      }
    ]
  },
  
  "session": {
    "dmScope": "per-account-channel-peer"
  },
  
  "channels": {
    "feishu": {
      "enabled": true,
      "threadSession": true,
      "replyMode": "auto",
      "appId": "cli_taizi_xxx",
      "appSecret": "taizi_secret_xxx",
      
      "accounts": {
        "default": {},
        
        "zhongshu": {
          "appId": "cli_zhongshu_xxx",
          "appSecret": "zhongshu_secret_xxx",
          "botName": "中书省",
          "dmPolicy": "allowlist",
          "allowFrom": ["*"]
        },
        
        "shangshu": {
          "appId": "cli_shangshu_xxx",
          "appSecret": "shangshu_secret_xxx",
          "botName": "尚书省",
          "dmPolicy": "allowlist",
          "allowFrom": ["*"]
        },
        
        "menxia": {
          "appId": "cli_menxia_xxx",
          "appSecret": "menxia_secret_xxx",
          "botName": "门下省",
          "dmPolicy": "allowlist",
          "allowFrom": ["*"]
        },
        
        "gongbu": {
          "appId": "cli_gongbu_xxx",
          "appSecret": "gongbu_secret_xxx",
          "botName": "工部",
          "dmPolicy": "allowlist",
          "allowFrom": ["*"]
        },
        
        "hubu": {
          "appId": "cli_hubu_xxx",
          "appSecret": "hubu_secret_xxx",
          "botName": "户部",
          "dmPolicy": "allowlist",
          "allowFrom": ["*"]
        },
        
        "bingbu": {
          "appId": "cli_bingbu_xxx",
          "appSecret": "bingbu_secret_xxx",
          "botName": "兵部",
          "dmPolicy": "allowlist",
          "allowFrom": ["*"]
        },
        
        "xingbu": {
          "appId": "cli_xingbu_xxx",
          "appSecret": "xingbu_secret_xxx",
          "botName": "刑部",
          "dmPolicy": "allowlist",
          "allowFrom": ["*"]
        },
        
        "libu": {
          "appId": "cli_libu_xxx",
          "appSecret": "libu_secret_xxx",
          "botName": "礼部",
          "dmPolicy": "allowlist",
          "allowFrom": ["*"]
        },
        
        "libu_hr": {
          "appId": "cli_libu_hr_xxx",
          "appSecret": "libu_hr_secret_xxx",
          "botName": "吏部",
          "dmPolicy": "allowlist",
          "allowFrom": ["*"]
        },
        
        "zaochao": {
          "appId": "cli_zaochao_xxx",
          "appSecret": "zaochao_secret_xxx",
          "botName": "钦天监",
          "dmPolicy": "allowlist",
          "allowFrom": ["*"]
        }
      },
      
      "groups": {
        "*": { "requireMention": true }
      },
      
      "groupPolicy": "allowlist",
      "groupAllowFrom": ["oc_group_xxx"]
    }
  },
  
  "bindings": [
    { "agentId": "taizi", "match": { "channel": "feishu", "accountId": "default" } },
    { "agentId": "zhongshu", "match": { "channel": "feishu", "accountId": "zhongshu" } },
    { "agentId": "shangshu", "match": { "channel": "feishu", "accountId": "shangshu" } },
    { "agentId": "menxia", "match": { "channel": "feishu", "accountId": "menxia" } },
    { "agentId": "gongbu", "match": { "channel": "feishu", "accountId": "gongbu" } },
    { "agentId": "hubu", "match": { "channel": "feishu", "accountId": "hubu" } },
    { "agentId": "bingbu", "match": { "channel": "feishu", "accountId": "bingbu" } },
    { "agentId": "xingbu", "match": { "channel": "feishu", "accountId": "xingbu" } },
    { "agentId": "libu", "match": { "channel": "feishu", "accountId": "libu" } },
    { "agentId": "libu_hr", "match": { "channel": "feishu", "accountId": "libu_hr" } },
    { "agentId": "zaochao", "match": { "channel": "feishu", "accountId": "zaochao" } }
  ]
}
```

## 飞书应用创建清单

需要创建 **11 个飞书机器人应用**：

| 职位 | App ID | App Secret | 权限需求 |
|-----|--------|-----------|---------|
| 教皇 | cli_taizi_xxx | xxx | 发送消息、接收消息、创建群聊、用户信息 |
| 中书省 | cli_zhongshu_xxx | xxx | 发送消息、接收消息 |
| 尚书省 | cli_shangshu_xxx | xxx | 发送消息、接收消息 |
| 门下省 | cli_menxia_xxx | xxx | 发送消息、接收消息 |
| 工部 | cli_gongbu_xxx | xxx | 发送消息、接收消息 |
| 户部 | cli_hubu_xxx | xxx | 发送消息、接收消息 |
| 兵部 | cli_bingbu_xxx | xxx | 发送消息、接收消息 |
| 刑部 | cli_xingbu_xxx | xxx | 发送消息、接收消息 |
| 礼部 | cli_libu_xxx | xxx | 发送消息、接收消息 |
| 吏部 | cli_libu_hr_xxx | xxx | 发送消息、接收消息 |
| 钦天监 | cli_zaochao_xxx | xxx | 发送消息、接收消息 |

## 工作空间创建

为每个 Agent 创建独立的工作空间：

```bash
# 创建工作空间目录
mkdir -p ~/.openclaw/workspace-taizi
mkdir -p ~/.openclaw/workspace-zhongshu
mkdir -p ~/.openclaw/workspace-shangshu
mkdir -p ~/.openclaw/workspace-menxia
mkdir -p ~/.openclaw/workspace-gongbu
mkdir -p ~/.openclaw/workspace-hubu
mkdir -p ~/.openclaw/workspace-bingbu
mkdir -p ~/.openclaw/workspace-xingbu
mkdir -p ~/.openclaw/workspace-libu
mkdir -p ~/.openclaw/workspace-libu_hr
mkdir -p ~/.openclaw/workspace-zaochao

# 复制配置文件到每个工作空间
cp config.json ~/.openclaw/workspace-taizi/
cp config.json ~/.openclaw/workspace-zhongshu/
# ... 以此类推
```

## 用户使用方式

### 场景一：直接咨询某个部门
```
用户：@工部 帮我开发一个用户登录功能
工部 Agent：开始处理...
```

### 场景二：任务派发
```
用户：@尚书省 有一个新项目需要开发
尚书省 Agent：收到，让我安排任务...
        → 派发给工部
        → 派发给户部预算审核
```

### 场景三：多部门协作
```
用户：@教皇 需要开发一个新系统
教皇 Agent：好的，召集各部门...
        [中书省] 制定规划
        [尚书省] 调度资源
        [工部] 技术开发
        [户部] 预算审批
        [刑部] 合规审查
```

## 路由规则说明

| 触发方式 | 路由目标 |
|---------|---------|
| @教皇 | taizi Agent |
| @中书省 | zhongshu Agent |
| @尚书省 | shangshu Agent |
| @门下省 | menxia Agent |
| @工部 | gongbu Agent |
| @户部 | hubu Agent |
| @兵部 | bingbu Agent |
| @刑部 | xingbu Agent |
| @礼部 | libu Agent |
| @吏部 | libu_hr Agent |
| @钦天监 | zaochao Agent |
| 私聊默认 | taizi Agent（教皇） |

## 部署步骤

1. **创建飞书应用**：在飞书开放平台创建 11 个机器人应用
2. **获取 Credentials**：记录每个应用的 App ID 和 App Secret
3. **配置回调地址**：为每个应用配置回调 URL
4. **创建工作空间**：在 ~/.openclaw/ 下创建 11 个工作空间目录
5. **修改 openclaw.json**：填入所有配置（使用 gateway config.patch）
6. **重启 Gateway**：使配置生效
7. **测试**：验证各机器人是否正常工作

## 注意事项

1. **会话隔离**：每个用户与每个部门的对话完全独立记忆
2. **权限控制**：建议使用 allowlist 模式
3. **成本考虑**：11 个机器人会增加 API 调用成本，可根据实际需要选择部分上线
4. **配置更新**：修改配置后需要重启 Gateway

## 简化方案（推荐先测试）

如果 11 个机器人过多，可以先配置核心的 3-5 个：

| 方案 | 机器人数量 | 适用场景 |
|-----|----------|---------|
| 最小 | 2个 | taizi + zhongshu |
| 基础 | 5个 | taizi + zhongshu + shangshu + gongbu + menxia |
| 完整 | 11个 | 全部三省六部 |
