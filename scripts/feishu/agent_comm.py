#!/usr/bin/env python3
"""
飞书通信模块 - Agent间通过飞书应用沟通
每个Agent作为飞书应用，接收和发送消息
"""
import os
import json
import time
import asyncio
import logging
import hashlib
import hmac
import base64
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

BASE = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Feishu] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('feishu-comm')

# ==================== 配置 ====================
class Config:
    # 飞书配置 (每个Agent独立配置)
    APP_ID = os.getenv('FEISHU_APP_ID', '')
    APP_SECRET = os.getenv('FEISHU_APP_SECRET', '')
    
    # 验证配置
    VERIFICATION_TOKEN = os.getenv('FEISHU_VERIFICATION_TOKEN', '')
    
    # Redis配置 (用于消息队列)
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB = int(os.getenv('REDIS_DB', '0'))
    
    # 消息超时
    MESSAGE_TIMEOUT = int(os.getenv('FEISHU_MSG_TIMEOUT', '60'))
    MAX_RETRIES = int(os.getenv('FEISHU_MAX_RETRIES', '3'))

config = Config()

# ==================== 常量 ====================
class MessageType(Enum):
    TEXT = "text"
    POST = "post"
    INTERACTIVE = "interactive"

class EventType(Enum):
    MESSAGE = "message"
    ADD_USER = "add_user"
    REMOVE_USER = "remove_user"

# ==================== 数据类 ====================
@dataclass
class FeishuMessage:
    """飞书消息"""
    msg_type: str = "text"
    content: str = ""
    user_id: str = ""
    open_id: str = ""
    chat_id: str = ""
    message_id: str = ""
    agent_id: str = ""

@dataclass
class AgentMessage:
    """Agent间消息"""
    from_agent: str
    to_agent: str
    content: str
    task_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    priority: int = 0  # 0=normal, 1=high, 2=urgent

# ==================== 签名验证 ====================
def verify_sign(secret: str, timestamp: str, sign: str) -> bool:
    """验证飞书签名"""
    if not sign or not timestamp:
        return False
    
    string_to_sign = f'{timestamp}\n{secret}'
    try:
        hm = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256)
        return hm.digest() == base64.b64decode(sign.encode("utf-8"))
    except Exception as e:
        log.error(f"签名验证失败: {e}")
        return False

def gen_sign(secret: str, timestamp: str) -> str:
    """生成飞书签名"""
    string_to_sign = f'{timestamp}\n{secret}'
    hm = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256)
    return base64.b64encode(hm.digest()).decode("utf-8")

# ==================== API客户端 ====================
class FeishuClient:
    """飞书API客户端"""
    
    def __init__(self, app_id: str = None, app_secret: str = None):
        self.app_id = app_id or config.APP_ID
        self.app_secret = app_secret or config.APP_SECRET
        self.access_token: Optional[str] = None
        self.token_expires_at: float = 0
        
        # API基础URL
        self.base_url = "https://open.feishu.cn/open-apis"
    
    def _get_access_token(self) -> Optional[str]:
        """获取tenant_access_token"""
        now = time.time()
        if self.access_token and now < self.token_expires_at - 60:
            return self.access_token
        
        if not requests:
            log.warning("requests库未安装")
            return None
        
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            result = resp.json()
            
            if result.get("code") == 0:
                self.access_token = result["tenant_access_token"]
                self.token_expires_at = now + result.get("expire", 7200)
                log.info(f"获取token成功，过期时间: {self.token_expires_at}")
                return self.access_token
            else:
                log.error(f"获取token失败: {result}")
                return None
        except Exception as e:
            log.error(f"获取token异常: {e}")
            return None
    
    def send_message(
        self,
        receive_id: str,
        msg_type: str = "text",
        content: str = "",
        receive_id_type: str = "open_id"
    ) -> Optional[dict]:
        """发送消息"""
        token = self._get_access_token()
        if not token:
            return None
        
        url = f"{self.base_url}/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        params = {
            "receive_id_type": receive_id_type
        }
        
        data = {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": json.dumps({"text": content}) if msg_type == "text" else content
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, params=params, timeout=10)
            result = resp.json()
            
            if result.get("code") == 0:
                log.info(f"消息发送成功: {receive_id}")
                return result
            else:
                log.error(f"消息发送失败: {result}")
                return result
        except Exception as e:
            log.error(f"消息发送异常: {e}")
            return None
    
    def send_rich_text_message(self, receive_id: str, receive_id_type: str = "chat_id",
                                content: str = "", mentions: List[dict] = None) -> Optional[dict]:
        """
        发送富文本消息（支持@提及）
        
        Args:
            receive_id: 接收者ID (chat_id 或 user_id)
            receive_id_type: 接收者类型 ("chat_id" / "user_id" / "open_id")
            content: 消息内容
            mentions: @提及的用户列表 [{"id": "ou_xxx", "name": "张三"}]
        
        Returns:
            发送结果
        """
        token = self._get_access_token()
        if not token:
            return None
        
        # 构建富文本内容
        rich_text_content = self._build_rich_text(content, mentions)
        
        url = f"{self.base_url}/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        params = {"receive_id_type": receive_id_type}
        
        data = {
            "receive_id": receive_id,
            "msg_type": "rich_text",
            "content": json.dumps(rich_text_content)
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, params=params, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                log.info(f"富文本消息发送成功: {receive_id}")
                return result
            else:
                log.error(f"富文本消息发送失败: {result}")
                return result
        except Exception as e:
            log.error(f"富文本消息发送异常: {e}")
            return None
    
    def _build_rich_text(self, content: str, mentions: List[dict] = None) -> dict:
        """
        构建富文本消息内容（支持@）
        
        飞书rich_text格式:
        {
            "type": "markdown",
            "content": "内容 **加粗** @张三"
        }
        或使用原生rich_text:
        {
            "type": "native",
            "elements": [...]
        }
        """
        # 简单方案：使用markdown类型，支持@语法
        # @用户格式: <at id=all></at> @所有人
        # @指定人: <at id=ou_xxx></at>
        
        at_mentions = ""
        if mentions:
            for m in mentions:
                user_id = m.get('id', '')
                user_name = m.get('name', '用户')
                if user_id:
                    # 飞书at特定人格式
                    at_mentions += f'<at id="{user_id}" name="{user_name}"></at> '
        
        # 组合消息：@ + 内容
        full_content = at_mentions + content if at_mentions else content
        
        return {
            "type": "markdown",
            "content": full_content
        }
    
    def send_group_message_with_mentions(self, chat_id: str, content: str,
                                          mention_user_ids: List[str] = None,
                                          mention_all: bool = False) -> Optional[dict]:
        """
        在群聊中发送消息，支持@提及
        
        Args:
            chat_id: 群聊ID
            content: 消息内容
            mention_user_ids: 需要@的用户ID列表
            mention_all: 是否@所有人
        
        Returns:
            发送结果
        """
        # 构建提及列表
        mentions = []
        if mention_all:
            # @所有人
            mentions = [{"id": "all", "name": "所有人"}]
        elif mention_user_ids:
            for uid in mention_user_ids:
                mentions.append({"id": uid, "name": "用户"})
        
        return self.send_rich_text_message(
            receive_id=chat_id,
            receive_id_type="chat_id",
            content=content,
            mentions=mentions
        )
    
    def create_agent_group_chat(self, agent_ids: List[str], 
                                 agent_names: Dict[str, str] = None,
                                 name: str = "Agent 群聊") -> Optional[str]:
        """
        创建Agent群聊并拉入多个Agent
        
        Args:
            agent_ids: Agent ID列表
            agent_names: Agent名称映射 {"agent_id": "名称"}
            name: 群聊名称
        
        Returns:
            chat_id 或 None
        """
        token = self._get_access_token()
        if not token:
            return None
        
        # 获取用户ID列表（需要先将Agent注册为用户或有对应的user_id）
        # 这里假设agent_ids就是user_id
        user_ids = agent_ids
        
        url = f"{self.base_url}/im/v1/chats"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        data = {
            "name": name,
            "user_id_list": user_ids,
            "chat_type": "group"
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                chat_id = result["data"]["chat_id"]
                log.info(f"创建Agent群聊成功: {chat_id}, 成员: {user_ids}")
                return chat_id
            else:
                log.error(f"创建群聊失败: {result}")
                return None
        except Exception as e:
            log.error(f"创建群聊异常: {e}")
            return None
    
    def add_members_to_chat(self, chat_id: str, user_ids: List[str]) -> bool:
        """
        添加成员到群聊
        
        Args:
            chat_id: 群聊ID
            user_ids: 要添加的用户ID列表
        
        Returns:
            是否成功
        """
        token = self._get_access_token()
        if not token:
            return False
        
        url = f"{self.base_url}/im/v1/chats/{chat_id}/members"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        data = {
            "member_id_list": user_ids,
            "member_id_type": "user_id"
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                log.info(f"添加成员成功: {chat_id}, 新成员: {user_ids}")
                return True
            else:
                log.error(f"添加成员失败: {result}")
                return False
        except Exception as e:
            log.error(f"添加成员异常: {e}")
            return False
    
    def remove_members_from_chat(self, chat_id: str, user_ids: List[str]) -> bool:
        """
        从群聊移除成员
        
        Args:
            chat_id: 群聊ID
            user_ids: 要移除的用户ID列表
        
        Returns:
            是否成功
        """
        token = self._get_access_token()
        if not token:
            return False
        
        url = f"{self.base_url}/im/v1/chats/{chat_id}/members"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        params = {
            "member_id_list": ",".join(user_ids),
            "member_id_type": "user_id"
        }
        
        try:
            resp = requests.delete(url, headers=headers, params=params, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                log.info(f"移除成员成功: {chat_id}, 移除成员: {user_ids}")
                return True
            else:
                log.error(f"移除成员失败: {result}")
                return False
        except Exception as e:
            log.error(f"移除成员异常: {e}")
            return False
    
    def get_chat_members(self, chat_id: str) -> List[dict]:
        """
        获取群聊成员列表
        
        Args:
            chat_id: 群聊ID
        
        Returns:
            成员列表
        """
        token = self._get_access_token()
        if not token:
            return []
        
        url = f"{self.base_url}/im/v1/chats/{chat_id}/members"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        params = {
            "member_id_type": "user_id"
        }
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return result.get("data", {}).get("items", [])
            return []
        except Exception as e:
            log.error(f"获取群成员异常: {e}")
            return []
    
    def reply_message(self, message_id: str, content: str, msg_type: str = "text") -> Optional[dict]:
        """回复消息"""
        token = self._get_access_token()
        if not token:
            return None
        
        url = f"{self.base_url}/im/v1/messages/{message_id}/reply"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        data = {
            "msg_type": msg_type,
            "content": json.dumps({"text": content}) if msg_type == "text" else content
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            return resp.json()
        except Exception as e:
            log.error(f"回复消息异常: {e}")
            return None
    
    def get_user_info(self, user_id: str) -> Optional[dict]:
        """获取用户信息"""
        token = self._get_access_token()
        if not token:
            return None
        
        url = f"{self.base_url}/contact/v3/users/{user_id}"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            return resp.json()
        except Exception as e:
            log.error(f"获取用户信息异常: {e}")
            return None
    
    def create_app_chat(self, user_ids: List[str], name: str = "Agent Chat") -> Optional[str]:
        """创建群聊"""
        token = self._get_access_token()
        if not token:
            return None
        
        url = f"{self.base_url}/im/v1/chats"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        data = {
            "name": name,
            "user_id_list": user_ids,
            "chat_type": "group"
        }
        
        try:
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return result["data"]["chat_id"]
            return None
        except Exception as e:
            log.error(f"创建群聊异常: {e}")
            return None


# ==================== 消息队列 ====================
class MessageQueue:
    """基于Redis的消息队列"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.queue_key = f"feishu:queue:{agent_id}"
        self.dlq_key = f"feishu:dlq:{agent_id}"  # 死信队列
        
        try:
            import redis
            self.redis = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                decode_responses=True
            )
        except Exception as e:
            log.warning(f"Redis连接失败: {e}，使用内存队列")
            self.redis = None
            self._memory_queue: List[AgentMessage] = []
    
    def push(self, message: AgentMessage) -> bool:
        """推送消息到队列"""
        msg_data = json.dumps({
            "from": message.from_agent,
            "to": message.to_agent,
            "content": message.content,
            "task_id": message.task_id,
            "timestamp": message.timestamp,
            "priority": message.priority
        })
        
        if self.redis:
            try:
                # 优先级队列 (score = timestamp - priority*1000 保证高优先级先出)
                score = message.timestamp - message.priority * 1000
                self.redis.zadd(self.queue_key, {msg_data: score})
                return True
            except Exception as e:
                log.error(f"Redis推送失败: {e}")
                return False
        else:
            self._memory_queue.append(message)
            return True
    
    def pop(self, timeout: int = 0) -> Optional[AgentMessage]:
        """从队列取出消息"""
        if self.redis:
            try:
                result = self.redis.zpopmin(self.queue_key, 1)
                if result:
                    _, data = result[0]
                    msg = json.loads(data)
                    return AgentMessage(
                        from_agent=msg["from"],
                        to_agent=msg["to"],
                        content=msg["content"],
                        task_id=msg.get("task_id"),
                        timestamp=msg.get("timestamp", time.time()),
                        priority=msg.get("priority", 0)
                    )
            except Exception as e:
                log.error(f"Redis取出失败: {e}")
        else:
            if self._memory_queue:
                return self._memory_queue.pop(0)
        return None
    
    def size(self) -> int:
        """队列长度"""
        if self.redis:
            return self.redis.zcard(self.queue_key)
        return len(self._memory_queue)
    
    def move_to_dlq(self, message: AgentMessage, reason: str):
        """消息移到死信队列"""
        log.warning(f"消息移至DLQ: {message.from_agent}->{message.to_agent}, 原因: {reason}")
        # 可以在这里添加重试逻辑


# ==================== Agent通信 ====================
class FeishuAgentComm:
    """基于飞书的Agent通信"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.client = FeishuClient()
        self.queue = MessageQueue(agent_id)
        self.handlers: Dict[str, Callable] = {}
        
        # Agent注册表 (agent_id -> open_id)
        self._registry: Dict[str, str] = {}
        
        # 群聊缓存 (agent_group_id -> chat_id)
        self._group_chats: Dict[str, str] = {}
    
    # ==================== 群聊通信 ====================
    
    def create_or_get_group_chat(self, agent_ids: List[str], 
                                   group_name: str = None) -> Optional[str]:
        """
        创建或获取Agent群聊
        
        Args:
            agent_ids: 参与群聊的Agent ID列表
            group_name: 群聊名称（可选）
        
        Returns:
            chat_id 或 None
        """
        # 生成群聊唯一ID（排序保证一致性）
        sorted_ids = sorted(agent_ids)
        group_key = "_".join(sorted_ids)
        
        # 检查缓存
        if group_key in self._group_chats:
            return self._group_chats[group_key]
        
        # 创建新群聊
        if group_name is None:
            agent_count = len(agent_ids)
            group_name = f"Agent 群聊 ({agent_count}人)"
        
        # 转换agent_id为user_id（这里假设agent_id就是user_id）
        user_ids = agent_ids
        
        chat_id = self.client.create_agent_group_chat(
            agent_ids=user_ids,
            agent_names=None,
            name=group_name
        )
        
        if chat_id:
            self._group_chats[group_key] = chat_id
        
        return chat_id
    
    def send_to_group(self, chat_id: str, content: str,
                       mention_agent_ids: List[str] = None,
                       mention_all: bool = False) -> bool:
        """
        发送消息到群聊，支持@提及
        
        Args:
            chat_id: 群聊ID
            content: 消息内容
            mention_agent_ids: 需要@的Agent ID列表
            mention_all: 是否@所有人
        
        Returns:
            是否成功
        """
        # 转换agent_id为open_id
        mention_user_ids = None
        if mention_agent_ids:
            mention_user_ids = [
                self._registry.get(aid) for aid in mention_agent_ids
                if self._registry.get(aid)
            ]
        
        result = self.client.send_group_message_with_mentions(
            chat_id=chat_id,
            content=content,
            mention_user_ids=mention_user_ids,
            mention_all=mention_all
        )
        
        return result and result.get("code") == 0
    
    def broadcast_to_agents(self, agent_ids: List[str], content: str,
                             mention_senders: bool = True) -> Dict[str, bool]:
        """
        广播消息给多个Agent（在群聊中发送）
        
        Args:
            agent_ids: 目标Agent ID列表
            content: 消息内容
            mention_senders: 是否在消息中@发送者
        
        Returns:
            发送结果 {"agent_id": success, ...}
        """
        results = {}
        
        # 创建群聊
        chat_id = self.create_or_get_group_chat(agent_ids)
        if not chat_id:
            for aid in agent_ids:
                results[aid] = False
            return results
        
        # 在群聊中发送消息，@所有人
        success = self.send_to_group(
            chat_id=chat_id,
            content=content,
            mention_all=True
        )
        
        for aid in agent_ids:
            results[aid] = success
        
        return results
    
    def group_discuss(self, agent_ids: List[str], topic: str,
                       initiator: str = None) -> Optional[str]:
        """
        发起Agent群组讨论
        
        Args:
            agent_ids: 参与讨论的Agent列表
            topic: 讨论主题
            initiator: 发起人Agent ID（默认自己）
        
        Returns:
            chat_id 或 None
        """
        if initiator is None:
            initiator = self.agent_id
        
        # 创建群聊
        chat_id = self.create_or_get_group_chat(
            agent_ids=agent_ids,
            group_name=f"讨论: {topic}"
        )
        
        if not chat_id:
            return None
        
        # 发送讨论主题
        content = f"📢 **讨论主题**: {topic}\n\n发起人: {initiator}\n请各Agent发表意见。"
        
        self.send_to_group(
            chat_id=chat_id,
            content=content,
            mention_all=True
        )
        
        return chat_id
    
    def add_agent_to_group(self, chat_id: str, agent_id: str) -> bool:
        """将Agent添加到现有群聊"""
        open_id = self._registry.get(agent_id)
        if not open_id:
            log.error(f"未找到Agent: {agent_id}")
            return False
        return self.client.add_members_to_chat(chat_id, [open_id])
    
    def remove_agent_from_group(self, chat_id: str, agent_id: str) -> bool:
        """从群聊移除Agent"""
        open_id = self._registry.get(agent_id)
        if not open_id:
            log.error(f"未找到Agent: {agent_id}")
            return False
        return self.client.remove_members_from_chat(chat_id, [open_id])
    
    def get_group_members(self, chat_id: str) -> List[dict]:
        """获取群聊成员列表"""
        return self.client.get_chat_members(chat_id)
    
    def register_handler(self, event_type: str, handler: Callable):
        """注册消息处理器"""
        self.handlers[event_type] = handler
    
    def register_agent(self, agent_id: str, open_id: str):
        """注册Agent的飞书ID"""
        self._registry[agent_id] = open_id
        log.info(f"注册Agent: {agent_id} -> {open_id}")
    
    def send_to_agent(
        self,
        to_agent: str,
        content: str,
        task_id: Optional[str] = None,
        priority: int = 0
    ) -> bool:
        """发送消息给另一个Agent"""
        # 获取目标Agent的open_id
        to_open_id = self._registry.get(to_agent)
        
        if not to_open_id:
            log.error(f"未找到Agent: {to_agent}")
            # 存入队列，稍后重试
            msg = AgentMessage(
                from_agent=self.agent_id,
                to_agent=to_agent,
                content=content,
                task_id=task_id,
                priority=priority
            )
            self.queue.push(msg)
            return False
        
        # 发送飞书消息
        result = self.client.send_message(
            receive_id=to_open_id,
            content=content
        )
        
        if result and result.get("code") == 0:
            return True
        
        # 发送失败，存入队列
        msg = AgentMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            content=content,
            task_id=task_id,
            priority=priority
        )
        self.queue.push(msg)
        return False
    
    def broadcast_to_group(self, chat_id: str, content: str) -> bool:
        """在群聊中广播消息"""
        result = self.client.send_message(
            receive_id=chat_id,
            content=content
        )
        return result and result.get("code") == 0
    
    def handle_webhook(self, payload: dict) -> dict:
        """处理飞书Webhook事件"""
        # 验证签名
        timestamp = payload.get("timestamp", "")
        sign = payload.get("sign", "")
        
        if not verify_sign(config.APP_SECRET, timestamp, sign):
            return {"code": 9999, "msg": "签名验证失败"}
        
        event = payload.get("event", {})
        event_type = event.get("type")
        
        # 处理消息事件
        if event_type == "message":
            msg = FeishuMessage(
                msg_type=event.get("msg_type", "text"),
                content=event.get("message", {}).get("content", {}),
                user_id=event.get("sender", {}).get("user_id", ""),
                open_id=event.get("open_id", ""),
                chat_id=event.get("chat_id", ""),
                message_id=event.get("message_id", "")
            )
            
            # 解析消息内容
            try:
                content = json.loads(msg.content)
                msg.content = content.get("text", "")
            except:
                pass
            
            # 存入队列
            agent_msg = AgentMessage(
                from_agent=msg.user_id,
                to_agent=self.agent_id,
                content=msg.content
            )
            self.queue.push(agent_msg)
            
            # 调用处理器
            handler = self.handlers.get("message")
            if handler:
                try:
                    handler(msg)
                except Exception as e:
                    log.error(f"消息处理异常: {e}")
        
        return {"code": 0, "msg": "success"}
    
    def process_queue(self):
        """处理消息队列"""
        while True:
            msg = self.queue.pop()
            if not msg:
                break
            
            # 查找处理器
            handler = self.handlers.get("queue")
            if handler:
                try:
                    handler(msg)
                except Exception as e:
                    log.error(f"队列消息处理异常: {e}")
                    self.queue.move_to_dlq(msg, str(e))


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='飞书Agent通信')
    parser.add_argument('--agent-id', required=True, help='Agent ID')
    parser.add_argument('--send', help='发送消息')
    parser.add_argument('--to', help='目标Agent ID')
    parser.add_argument('--queue', action='store_true', help='查看队列')
    parser.add_argument('--webhook', help='处理Webhook')
    
    args = parser.parse_args()
    
    comm = FeishuAgentComm(args.agent_id)
    
    if args.send and args.to:
        success = comm.send_to_agent(args.to, args.send)
        print(f"发送{'成功' if success else '失败'}")
    elif args.queue:
        print(f"队列长度: {comm.queue.size()}")
    elif args.webhook:
        payload = json.loads(args.webhook)
        result = comm.handle_webhook(payload)
        print(json.dumps(result))

if __name__ == '__main__':
    main()
