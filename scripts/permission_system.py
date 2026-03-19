#!/usr/bin/env python3
"""
权限控制 - 基于角色的访问控制 (RBAC)
支持细粒度权限管理
"""
import os
import sys
import json
import time
import logging
import threading
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / 'scripts'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [Auth] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('auth')

# ==================== 常量 ====================
class Permission(Enum):
    """权限"""
    # Agent权限
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    AGENT_EXECUTE = "agent:execute"
    
    # 消息权限
    MESSAGE_SEND = "message:send"
    MESSAGE_READ = "message:read"
    MESSAGE_DELETE = "message:delete"
    
    # 任务权限
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_EXECUTE = "task:execute"
    
    # 配置权限
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"
    
    # 系统权限
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_AUDIT = "system:audit"


class Role(Enum):
    """角色"""
    ADMIN = "admin"           # 超级管理员
    MANAGER = "manager"      # 经理
    AGENT = "agent"         # Agent
    OPERATOR = "operator"   # 运维
    AUDITOR = "auditor"    # 审计
    GUEST = "guest"        # 访客


# ==================== 数据类 ====================
@dataclass
class User:
    """用户/Agent"""
    id: str
    name: str
    roles: Set[str] = field(default_factory=set)
    permissions: Set[str] = field(default_factory=set)  # 直接授予的权限
    department: str = ""
    email: str = ""
    active: bool = True
    created_at: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


@dataclass
class PermissionGrant:
    """权限授予记录"""
    permission: str
    granted_to: str  # user_id
    granted_by: str
    granted_at: float = field(default_factory=time.time)
    expires_at: float = None  # 可选过期时间
    reason: str = ""


# ==================== 权限系统 ====================
class PermissionSystem:
    """权限控制系统"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初始化"""
        self._users: Dict[str, User] = {}
        self._roles: Dict[str, Set[str]] = {}  # role -> permissions
        self._grants: List[PermissionGrant] = []
        self._lock = threading.RLock()
        
        # 初始化默认角色
        self._init_default_roles()
        
        # 初始化默认用户
        self._init_default_users()
        
        log.info("权限系统初始化完成")
    
    def _init_default_roles(self):
        """初始化默认角色"""
        
        role_permissions = {
            Role.ADMIN.value: {
                # 所有权限
                "system:admin",
                "system:audit",
                "agent:create", "agent:read", "agent:update", "agent:delete", "agent:execute",
                "message:send", "message:read", "message:delete",
                "task:create", "task:read", "task:update", "task:delete", "task:execute",
                "config:read", "config:write",
            },
            Role.MANAGER.value: {
                "agent:read", "agent:execute",
                "message:send", "message:read",
                "task:create", "task:read", "task:update", "task:execute",
                "config:read",
                "system:audit",
            },
            Role.AGENT.value: {
                "agent:read",
                "message:send", "message:read",
                "task:read", "task:execute",
            },
            Role.OPERATOR.value: {
                "agent:read",
                "message:read",
                "task:read", "task:update",
                "config:read", "config:write",
            },
            Role.AUDITOR.value: {
                "agent:read",
                "message:read",
                "task:read",
                "config:read",
                "system:audit",
            },
            Role.GUEST.value: {
                "agent:read",
                "task:read",
            }
        }
        
        self._roles = role_permissions
    
    def _init_default_users(self):
        """初始化默认用户"""
        
        # 教皇 (管理员)
        self.create_user(
            id="教皇",
            name="教皇",
            roles={Role.ADMIN.value}
        )
        
        # 红衣主教团 (经理)
        self.create_user(
            id="红衣主教团",
            name="红衣主教团",
            roles={Role.MANAGER.value}
        )
        
        # 其他Agent
        for agent in ["主教团", "枢机处", "工匠行会", "财政部", "骑士团", "宗教裁判所"]:
            self.create_user(
                id=agent,
                name=agent,
                roles={Role.AGENT.value}
            )
    
    # ---- 用户管理 ----
    def create_user(
        self,
        id: str,
        name: str,
        roles: Set[str] = None,
        permissions: Set[str] = None,
        **kwargs
    ) -> User:
        """创建用户"""
        
        user = User(
            id=id,
            name=name,
            roles=roles or set(),
            permissions=permissions or set(),
            **kwargs
        )
        
        with self._lock:
            self._users[id] = user
        
        log.info(f"创建用户: {id} ({name})")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        return self._users.get(user_id)
    
    def update_user(self, user_id: str, **kwargs) -> bool:
        """更新用户"""
        with self._lock:
            if user_id not in self._users:
                return False
            
            user = self._users[user_id]
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            return True
    
    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        with self._lock:
            if user_id in self._users:
                del self._users[user_id]
                log.info(f"删除用户: {user_id}")
                return True
            return False
    
    def list_users(self, role: str = None, active: bool = None) -> List[User]:
        """列出用户"""
        with self._lock:
            users = list(self._users.values())
        
        if role:
            users = [u for u in users if role in u.roles]
        if active is not None:
            users = [u for u in users if u.active == active]
        
        return users
    
    # ---- 权限检查 ----
    def has_permission(self, user_id: str, permission: str) -> bool:
        """检查权限"""
        
        user = self._users.get(user_id)
        if not user:
            return False
        
        if not user.active:
            return False
        
        # 检查直接权限
        if permission in user.permissions:
            return True
        
        # 检查角色权限
        for role in user.roles:
            role_perms = self._roles.get(role, set())
            if permission in role_perms:
                return True
        
        return False
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """检查权限 (不存在用户则拒绝)"""
        result = self.has_permission(user_id, permission)
        
        if not result:
            log.warning(f"权限拒绝: {user_id} 请求 {permission}")
        
        return result
    
    def can(self, user_id: str, *permissions: str) -> bool:
        """检查多个权限 (AND)"""
        return all(self.has_permission(user_id, p) for p in permissions)
    
    def can_any(self, user_id: str, *permissions: str) -> bool:
        """检查多个权限 (OR)"""
        return any(self.has_permission(user_id, p) for p in permissions)
    
    # ---- 权限授予 ----
    def grant_permission(
        self,
        permission: str,
        user_id: str,
        granted_by: str,
        expires_at: float = None,
        reason: str = ""
    ) -> bool:
        """授予权限"""
        
        user = self._users.get(user_id)
        if not user:
            return False
        
        with self._lock:
            user.permissions.add(permission)
            
            grant = PermissionGrant(
                permission=permission,
                granted_to=user_id,
                granted_by=granted_by,
                expires_at=expires_at,
                reason=reason
            )
            self._grants.append(grant)
        
        log.info(f"授权: {granted_by} -> {user_id} ({permission})")
        return True
    
    def revoke_permission(self, user_id: str, permission: str) -> bool:
        """撤销权限"""
        
        user = self._users.get(user_id)
        if not user:
            return False
        
        with self._lock:
            if permission in user.permissions:
                user.permissions.remove(permission)
                log.info(f"撤销权限: {user_id} ({permission})")
                return True
        
        return False
    
    def get_permissions(self, user_id: str) -> Set[str]:
        """获取用户所有权限"""
        
        user = self._users.get(user_id)
        if not user:
            return set()
        
        permissions = user.permissions.copy()
        
        for role in user.roles:
            role_perms = self._roles.get(role, set())
            permissions.update(role_perms)
        
        return permissions
    
    # ---- 角色管理 ----
    def assign_role(self, user_id: str, role: str) -> bool:
        """分配角色"""
        
        user = self._users.get(user_id)
        if not user:
            return False
        
        if role not in self._roles:
            log.warning(f"未知角色: {role}")
            return False
        
        with self._lock:
            user.roles.add(role)
        
        log.info(f"分配角色: {user_id} -> {role}")
        return True
    
    def remove_role(self, user_id: str, role: str) -> bool:
        """移除角色"""
        
        user = self._users.get(user_id)
        if not user:
            return False
        
        with self._lock:
            if role in user.roles:
                user.roles.remove(role)
                log.info(f"移除角色: {user_id} <- {role}")
                return True
        
        return False
    
    # ---- 查询 ----
    def list_roles(self) -> List[str]:
        """列出所有角色"""
        return list(self._roles.keys())
    
    def get_role_permissions(self, role: str) -> Set[str]:
        """获取角色权限"""
        return self._roles.get(role, set())
    
    def who_has_permission(self, permission: str) -> List[str]:
        """谁有某权限"""
        users = []
        
        for user_id, user in self._users.items():
            if self.has_permission(user_id, permission):
                users.append(user_id)
        
        return users
    
    # ---- 持久化 ----
    def save(self, path: str = "config/permissions.json"):
        """保存配置"""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        
        data = {
            "users": {
                uid: {
                    "name": u.name,
                    "roles": list(u.roles),
                    "permissions": list(u.permissions),
                    "active": u.active
                }
                for uid, u in self._users.items()
            }
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        log.info(f"权限配置已保存: {path}")
    
    def load(self, path: str = "config/permissions.json"):
        """加载配置"""
        if not os.path.exists(path):
            return False
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            with self._lock:
                self._users.clear()
                
                for uid, info in data.get("users", {}).items():
                    self._users[uid] = User(
                        id=uid,
                        name=info["name"],
                        roles=set(info.get("roles", [])),
                        permissions=set(info.get("permissions", [])),
                        active=info.get("active", True)
                    )
            
            log.info(f"权限配置已加载: {path}")
            return True
            
        except Exception as e:
            log.error(f"加载权限配置失败: {e}")
            return False


# ==================== 装饰器 ====================
def require_permission(*permissions: str):
    """权限检查装饰器"""
    
    def decorator(func):
        
        def wrapper(*args, **kwargs):
            # 获取user_id (从kwargs或第一个参数)
            user_id = kwargs.get('user_id') or (args[0] if args else None)
            
            if not user_id:
                raise PermissionError("未指定用户")
            
            auth = PermissionSystem()
            
            if not auth.can(user_id, *permissions):
                raise PermissionError(
                    f"权限不足: 需要 {permissions}, 当前用户 {user_id}"
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def require_role(*roles: str):
    """角色检查装饰器"""
    
    def decorator(func):
        
        def wrapper(*args, **kwargs):
            user_id = kwargs.get('user_id') or (args[0] if args else None)
            
            if not user_id:
                raise PermissionError("未指定用户")
            
            auth = PermissionSystem()
            user = auth.get_user(user_id)
            
            if not user:
                raise PermissionError(f"用户不存在: {user_id}")
            
            if not any(role in user.roles for role in roles):
                raise PermissionError(
                    f"角色不足: 需要 {roles}, 当前用户 {user_id} 角色 {user.roles}"
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# ==================== CLI ====================
def main():
    import argparse
    parser = argparse.ArgumentParser(description='权限控制')
    parser.add_argument('--check', nargs=2, metavar=("USER", "PERM"), help='检查权限')
    parser.add_argument('--list-users', action='store_true', help='列出用户')
    parser.add_argument('--create-user', nargs=2, metavar=("ID", "NAME"), help='创建用户')
    parser.add_argument('--grant', nargs=3, metavar=("USER", "PERM", "BY"), help='授予权限')
    parser.add_argument('--assign-role', nargs=3, metavar=("USER", "ROLE", "BY"), help='分配角色')
    parser.add_argument('--perms', help='查看用户权限')
    parser.add_argument('--save', action='store_true', help='保存配置')
    parser.add_argument('--load', action='store_true', help='加载配置')
    
    args = parser.parse_args()
    
    auth = PermissionSystem()
    
    if args.check:
        result = auth.check_permission(args.check[0], args.check[1])
        print(f"{args.check[0]} 有 {args.check[1]} 权限: {result}")
    
    elif args.list_users:
        for u in auth.list_users():
            print(f"{u.id:15} | {u.name:10} | {list(u.roles)} | {'活跃' if u.active else '禁用'}")
    
    elif args.create_user:
        auth.create_user(args.create_user[0], args.create_user[1])
        print(f"用户已创建: {args.create_user[0]}")
    
    elif args.grant:
        auth.grant_permission(args.grant[1], args.grant[0], args.grant[2])
        print(f"权限已授予: {args.grant[0]} -> {args.grant[1]}")
    
    elif args.assign_role:
        auth.assign_role(args.assign_role[0], args.assign_role[1])
        print(f"角色已分配: {args.assign_role[0]} -> {args.assign_role[1]}")
    
    elif args.perms:
        perms = auth.get_permissions(args.perms)
        print(f"{args.perms} 的权限:")
        for p in sorted(perms):
            print(f"  - {p}")
    
    elif args.save:
        auth.save()
        print("配置已保存")
    
    elif args.load:
        auth.load()
        print("配置已加载")


if __name__ == '__main__':
    main()
