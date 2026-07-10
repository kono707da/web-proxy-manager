"""内存日志 handler，缓存最近的应用日志供前端查看。"""

from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime


class MemoryLogHandler(logging.Handler):
    """将日志记录缓存到内存环形缓冲区，供 API 读取。

    线程安全。保留最近 ``capacity`` 条记录。
    """

    _instance: MemoryLogHandler | None = None
    _lock = threading.Lock()

    def __init__(self, capacity: int = 1000) -> None:
        super().__init__()
        self._buffer: deque[dict] = deque(maxlen=capacity)
        self._rw_lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            if record.exc_info:
                entry["message"] += "\n" + self.format(record)
            with self._rw_lock:
                self._buffer.append(entry)
        except Exception:
            # 日志 handler 内部不能抛异常
            pass

    def get_logs(self, tail: int = 200, level: str | None = None, keyword: str | None = None) -> list[dict]:
        """返回最近的日志条目，可按级别和关键词过滤。"""
        with self._rw_lock:
            items = list(self._buffer)
        if level:
            levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
            order = {lvl: i for i, lvl in enumerate(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])}
            if level.upper() in order:
                idx = order[level.upper()]
                allowed = {lvl for lvl, i in order.items() if i >= idx}
                items = [it for it in items if it["level"] in allowed]
        if keyword:
            kw = keyword.lower()
            items = [it for it in items if kw in it["message"].lower() or kw in it["logger"].lower()]
        if tail > 0:
            items = items[-tail:]
        return items

    @classmethod
    def get_instance(cls) -> MemoryLogHandler:
        with cls._lock:
            if cls._instance is None:
                cls._instance = MemoryLogHandler()
            return cls._instance


def install_memory_handler(level: int = logging.INFO) -> MemoryLogHandler:
    """安装内存日志 handler 到 root logger，返回单例。"""
    handler = MemoryLogHandler.get_instance()
    handler.setLevel(level)
    root = logging.getLogger()
    # 避免重复添加
    if not any(isinstance(h, MemoryLogHandler) for h in root.handlers):
        root.addHandler(handler)
    return handler
