from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .database import init_db
from .log_handler import install_memory_handler
from .mihomo.manager import get_manager
from .routers import ALL_ROUTERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# 安装内存日志 handler，供 /api/logs 读取
install_memory_handler(level=logging.INFO)
logger = logging.getLogger("proxy_manager")

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # 项目根（backend/ 的上一级）
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("proxy-manager 启动中 (host=%s, port=%s)", settings.host, settings.port)
    init_db()
    mgr = get_manager()
    try:
        mgr.start()
    except Exception as e:
        logger.error("mihomo 启动失败，后端仍可运行（请在系统设置中检查）: %s", e, exc_info=True)
    yield
    try:
        get_manager().stop()
    except Exception as e:
        logger.error("停止 mihomo 异常: %s", e, exc_info=True)
    logger.info("proxy-manager 已停止")


app = FastAPI(
    title="Proxy Manager",
    description="基于 mihomo(Clash.Meta) 的 Docker 代理管理器，提供订阅管理、节点切换、规则路由、流量统计、限速配额等能力",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)

for r in ALL_ROUTERS:
    app.include_router(r)


@app.get("/health", tags=["root"])
def health() -> dict:
    """健康检查。"""
    return {"status": "ok"}


# ---------- 前端静态文件挂载（前后端合并单端口） ----------
if FRONTEND_DIST.is_dir():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback(request: Request, exc: StarletteHTTPException):
        path = request.url.path
        # API 与文档路径返回 JSON，不交给 SPA
        if path.startswith(("/api/", "/docs", "/openapi.json", "/health")):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        if exc.status_code == 404:
            file_path = FRONTEND_DIST / path.lstrip("/")
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(FRONTEND_DIST / "index.html")
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
else:
    @app.get("/", tags=["root"])
    def root() -> dict:
        return {
            "name": "proxy-manager",
            "version": "1.0.0",
            "frontend": "未构建，请进入 frontend 目录执行 npm install && npm run build",
        }
