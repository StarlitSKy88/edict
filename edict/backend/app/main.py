"""Edict Backend — FastAPI 应用入口。

Lifespan 管理：
- startup: 连接 Redis Event Bus, 初始化数据库
- shutdown: 关闭连接

路由：
- /api/tasks — 任务 CRUD
- /api/agents — Agent 信息
- /api/events — 事件查询
- /api/admin — 管理操作
- /ws — WebSocket 实时推送

增强：
- 全局异常处理器
- 请求日志中间件
"""

import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings
from .services.event_bus import get_event_bus
from .api import tasks, agents, events, admin, websocket
from .api import legacy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("edict")


# ── 全局异常处理器 ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理，记录日志并返回友好错误"""
    log.error(f"全局异常: {request.method} {request.url} - {exc}")
    log.debug(traceback.format_exc())
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "type": "HTTPException"}
        )
    
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误", "type": "InternalError", "message": str(exc)[:100]}
    )


# ── 请求日志中间件 ──
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = __import__("time").time()
        response = await call_next(request)
        elapsed = (time.time() - start_time) * 1000
        
        log.info(f"{request.method} {request.url.path} - {response.status_code} - {elapsed:.1f}ms")
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    settings = get_settings()
    log.info(f"🏛️ Edict Backend starting on port {settings.port}...")

    # 连接 Event Bus
    bus = await get_event_bus()
    log.info("✅ Event Bus connected")

    yield

    # 清理
    await bus.close()
    log.info("Edict Backend shutdown complete")


app = FastAPI(
    title="Edict 三省六部",
    description="事件驱动的 AI Agent 协作平台",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — 开发环境允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

# 注册路由
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(legacy.router, prefix="/api/tasks", tags=["legacy"])


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "engine": "edict"}


@app.get("/api")
async def api_root():
    return {
        "name": "Edict 三省六部 API",
        "version": "2.0.0",
        "endpoints": {
            "tasks": "/api/tasks",
            "agents": "/api/agents",
            "events": "/api/events",
            "admin": "/api/admin",
            "websocket": "/ws",
            "health": "/health",
        },
    }
