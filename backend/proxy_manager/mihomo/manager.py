from __future__ import annotations

import json
import logging
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy.orm import Session

from ..config import BASE_DIR, settings
from ..database import SessionLocal
from ..models import TrafficQuota, TrafficStat
from .client import MihomoAPIError, MihomoClient
from . import config_builder

logger = logging.getLogger("proxy_manager.mihomo")


class MihomoManager:
    """mihomo 内核生命周期管理（单例）。

    职责：
    1. 生成配置 + 启动/停止/重启 mihomo 子进程
    2. 后台线程读取实时流量缓存到内存
    3. 后台线程累计按客户端 IP 的流量、检查配额
    """

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self.client = MihomoClient(
            host="127.0.0.1",
            port=settings.mihomo.api_port,
            secret=settings.mihomo.secret,
        )
        self._work_dir = (BASE_DIR / settings.mihomo.work_dir).resolve()
        self._config_path = self._work_dir / "config.yaml"
        self._log_path = self._work_dir / "mihomo.log"
        self._stop_event = threading.Event()
        self._threads: list[threading.Thread] = []
        self._traffic_cache: dict[str, int] = {"up": 0, "down": 0, "ts": 0}
        self._memory_cache: dict[str, int] = {"inuse": 0, "oslimit": 0}
        self._start_time: float = 0.0
        self._last_error: str | None = None
        # 连接字节缓存，用于计算增量累计流量: {conn_id: {up, down, ip}}
        self._conn_cache: dict[str, dict[str, Any]] = {}

    # ---------- 进程管理 ----------
    @property
    def work_dir(self) -> Path:
        return self._work_dir

    @property
    def config_path(self) -> Path:
        return self._config_path

    def is_running(self) -> bool:
        if self._proc is None:
            return False
        return self._proc.poll() is None

    def start(self, db: Session | None = None) -> None:
        """生成配置并启动 mihomo。"""
        if self.is_running():
            logger.warning("mihomo 已在运行，忽略重复启动")
            return
        self._last_error = None
        self._work_dir.mkdir(parents=True, exist_ok=True)
        # 写入配置
        if db is None:
            db = SessionLocal()
            try:
                config_builder.write_config(db, self._config_path)
            finally:
                db.close()
        else:
            config_builder.write_config(db, self._config_path)

        binary = settings.mihomo.binary
        cmd = [binary, "-d", str(self._work_dir), "-f", str(self._config_path)]
        logger.info("启动 mihomo: %s", " ".join(cmd))
        try:
            log_fp = self._log_path.open("w", encoding="utf-8")
            self._proc = subprocess.Popen(
                cmd,
                stdout=log_fp,
                stderr=subprocess.STDOUT,
                cwd=str(self._work_dir),
                start_new_session=True,
            )
        except FileNotFoundError:
            self._last_error = f"未找到 mihomo 二进制: {binary}。请确认已安装或在容器内运行。"
            logger.error(self._last_error)
            return
        except Exception as e:
            self._last_error = f"启动 mihomo 失败: {e}"
            logger.error(self._last_error, exc_info=True)
            return

        self._start_time = time.time()
        self._stop_event.clear()
        self._start_monitors()
        logger.info("mihomo 已启动, PID=%s", self._proc.pid)

    def stop(self) -> None:
        """停止 mihomo 及所有监控线程。"""
        self._stop_event.set()
        self._threads.clear()
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait(timeout=3)
                logger.info("mihomo 进程已停止")
            except Exception as e:
                logger.error("停止 mihomo 异常: %s", e, exc_info=True)
        self._proc = None
        self._traffic_cache = {"up": 0, "down": 0, "ts": 0}

    def restart(self, db: Session | None = None) -> None:
        self.stop()
        time.sleep(0.5)
        self.start(db)

    def reload(self, db: Session | None = None) -> None:
        """重新生成配置并通知 mihomo 热重载。"""
        if db is None:
            db = SessionLocal()
            try:
                config_builder.write_config(db, self._config_path)
            finally:
                db.close()
        else:
            config_builder.write_config(db, self._config_path)
        if not self.is_running():
            logger.warning("mihomo 未运行，reload 跳过（下次启动生效）")
            return
        try:
            self.client.reload_config(str(self._config_path), force=True)
            self.client.close_all_connections()
            logger.info("mihomo 配置已热重载")
        except MihomoAPIError as e:
            logger.error("mihomo 热重载失败，尝试重启: %s", e, exc_info=True)
            self.restart()

    # ---------- 监控线程 ----------
    def _start_monitors(self) -> None:
        t1 = threading.Thread(target=self._traffic_loop, name="mihomo-traffic", daemon=True)
        t2 = threading.Thread(target=self._quota_loop, name="mihomo-quota", daemon=True)
        t1.start()
        t2.start()
        self._threads = [t1, t2]

    def _traffic_loop(self) -> None:
        """读取 mihomo /traffic 流式响应，缓存实时上下行。"""
        url = f"{self.client.base_url}/traffic"
        while not self._stop_event.is_set():
            try:
                with httpx.stream("GET", url, headers=self.client.headers, timeout=None) as resp:
                    for line in resp.iter_lines():
                        if self._stop_event.is_set() or not line:
                            break
                        try:
                            data = json.loads(line)
                            self._traffic_cache = {
                                "up": int(data.get("up", 0)),
                                "down": int(data.get("down", 0)),
                                "ts": int(time.time()),
                            }
                        except (json.JSONDecodeError, ValueError, TypeError):
                            continue
            except Exception:
                if self._stop_event.is_set():
                    break
                time.sleep(1)

    def _quota_loop(self) -> None:
        """定期累计按客户端 IP 流量、检查配额、必要时触发重载。"""
        interval = max(1, settings.traffic.quota_check_interval)
        need_reload = False
        while not self._stop_event.is_set():
            time.sleep(interval)
            if not self.is_running():
                continue
            try:
                need_reload = self._accumulate_traffic() or need_reload
                if self._check_quotas():
                    need_reload = True
                if need_reload:
                    logger.info("配额状态变更，触发配置重载")
                    db = SessionLocal()
                    try:
                        config_builder.write_config(db, self._config_path)
                        self.client.reload_config(str(self._config_path), force=True)
                    finally:
                        db.close()
                    need_reload = False
            except Exception as e:
                logger.error("流量/配额监控异常: %s", e, exc_info=True)

    def _accumulate_traffic(self) -> bool:
        """从 /connections 累计按客户端 IP 的流量增量。返回是否有新 IP 首次出现。"""
        try:
            data = self.client.get_connections()
        except MihomoAPIError as e:
            logger.warning("获取连接失败: %s", e)
            return False
        conns = data.get("connections", []) or []
        new_ip_seen = False
        current_ids: set[str] = set()
        db = SessionLocal()
        try:
            for c in conns:
                cid = c.get("id")
                if not cid:
                    continue
                current_ids.add(cid)
                meta = c.get("metadata", {}) or {}
                ip = meta.get("sourceIP") or meta.get("destinationIP") or "unknown"
                up = int(c.get("upload", 0))
                down = int(c.get("download", 0))
                last = self._conn_cache.get(cid)
                if last is None:
                    delta_up, delta_down = up, down
                    new_ip_seen = True
                else:
                    delta_up = max(0, up - int(last.get("up", 0)))
                    delta_down = max(0, down - int(last.get("down", 0)))
                self._conn_cache[cid] = {"up": up, "down": down, "ip": ip}
                if delta_up > 0 or delta_down > 0:
                    self._bump_stat(db, ip, delta_up, delta_down)
            db.commit()
        except Exception as e:
            logger.error("累计流量失败: %s", e, exc_info=True)
            db.rollback()
        finally:
            db.close()
        # 清理已断开连接
        gone = set(self._conn_cache.keys()) - current_ids
        for gid in gone:
            self._conn_cache.pop(gid, None)
        return new_ip_seen

    @staticmethod
    def _bump_stat(db: Session, ip: str, up: int, down: int) -> None:
        stat = db.query(TrafficStat).filter(TrafficStat.client_ip == ip).first()
        now = datetime.now(timezone.utc)
        if stat is None:
            stat = TrafficStat(
                client_ip=ip,
                upload_total=up,
                download_total=down,
                total_bytes=up + down,
                last_seen=now,
            )
            db.add(stat)
        else:
            stat.upload_total += up
            stat.download_total += down
            stat.total_bytes += up + down
            stat.last_seen = now

    def _check_quotas(self) -> bool:
        """检查配额是否超限，返回是否有 blocked 状态变更。"""
        db = SessionLocal()
        changed = False
        try:
            quotas = db.query(TrafficQuota).filter(TrafficQuota.enabled.is_(True)).all()
            for q in quotas:
                # 周期重置
                if self._maybe_reset_quota(db, q):
                    changed = True
                stat = db.query(TrafficStat).filter(TrafficStat.client_ip == q.target).first()
                used = stat.total_bytes if stat else 0
                q.used_bytes = used
                should_block = q.quota_bytes > 0 and used >= q.quota_bytes
                if should_block and not q.blocked:
                    q.blocked = True
                    changed = True
                    logger.warning("配额超限: %s(%s) 已用 %d/%d，已阻断", q.name, q.target, used, q.quota_bytes)
                elif not should_block and q.blocked and used < q.quota_bytes:
                    q.blocked = False
                    changed = True
                    logger.info("配额恢复: %s(%s) 已用 %d/%d，解除阻断", q.name, q.target, used, q.quota_bytes)
            db.commit()
            return changed
        except Exception as e:
            logger.error("配额检查失败: %s", e, exc_info=True)
            db.rollback()
            return False
        finally:
            db.close()

    @staticmethod
    def _maybe_reset_quota(db: Session, q: TrafficQuota) -> bool:
        """按周期重置配额计数（daily/monthly）。返回是否重置。"""
        now = datetime.now(timezone.utc)
        if q.period == "total":
            return False
        reset = False
        if q.last_reset is None:
            reset = True
        elif q.period == "daily" and (now - q.last_reset).total_seconds() >= 86400:
            reset = True
        elif q.period == "monthly":
            # 到达 reset_day 且跨月
            if now.day == q.reset_day and (q.last_reset is None or now.month != q.last_reset.month or now.year != q.last_reset.year):
                reset = True
        if reset:
            stat = db.query(TrafficStat).filter(TrafficStat.client_ip == q.target).first()
            if stat:
                stat.upload_total = 0
                stat.download_total = 0
                stat.total_bytes = 0
            q.used_bytes = 0
            q.blocked = False
            q.last_reset = now
        return reset

    # ---------- 状态查询 ----------
    def get_realtime_traffic(self) -> dict[str, int]:
        return dict(self._traffic_cache)

    def get_memory(self) -> dict[str, int]:
        try:
            data = self.client.get_connections()
            self._memory_cache = {"inuse": int(data.get("memory", 0)), "oslimit": 0}
        except MihomoAPIError:
            pass
        return dict(self._memory_cache)

    def get_status(self) -> dict[str, Any]:
        version = None
        mode = None
        if self.is_running():
            try:
                v = self.client.get_version()
                version = v.get("version")
                cfg = self.client.get_configs()
                mode = cfg.get("mode")
            except MihomoAPIError:
                pass
        return {
            "running": self.is_running(),
            "pid": self._proc.pid if self._proc else None,
            "version": version,
            "api_port": settings.mihomo.api_port,
            "mixed_port": settings.mihomo.mixed_port,
            "mode": mode,
            "log_level": settings.mihomo.log_level,
            "uptime": int(time.time() - self._start_time) if self._start_time and self.is_running() else None,
            "last_error": self._last_error,
        }


_manager: MihomoManager | None = None


def get_manager() -> MihomoManager:
    global _manager
    if _manager is None:
        _manager = MihomoManager()
    return _manager
