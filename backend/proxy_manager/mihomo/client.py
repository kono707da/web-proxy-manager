from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("proxy_manager.mihomo")


class MihomoAPIError(Exception):
    """mihomo API 调用异常。"""


class MihomoClient:
    """mihomo external-controller RESTful API 客户端。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 9090, secret: str = "", timeout: float = 20.0) -> None:
        self.base_url = f"http://{host}:{port}"
        self.secret = secret
        self.timeout = timeout

    @property
    def headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.secret:
            h["Authorization"] = f"Bearer {self.secret}"
        return h

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.request(method, url, headers=self.headers, **kwargs)
            if resp.status_code >= 400:
                raise MihomoAPIError(f"mihomo API {method} {path} 返回 {resp.status_code}: {resp.text}")
            if resp.status_code == 204 or not resp.content:
                return None
            return resp.json()
        except httpx.RequestError as e:
            raise MihomoAPIError(f"无法连接 mihomo API {path}: {e}") from e

    # ---------- 系统 ----------
    def get_version(self) -> dict[str, Any]:
        return self._request("GET", "/version")

    def get_configs(self) -> dict[str, Any]:
        return self._request("GET", "/configs")

    def patch_configs(self, payload: dict[str, Any]) -> None:
        self._request("PATCH", "/configs", json=payload)

    def reload_config(self, config_path: str, force: bool = True) -> None:
        """通知 mihomo 重载配置文件。config_path 必须是 mihomo 可访问的路径。"""
        self._request("PUT", "/configs", params={"force": "true" if force else "false"}, json={"path": config_path})

    # ---------- 流量 / 内存 ----------
    def get_connections(self) -> dict[str, Any]:
        """返回 {downloadTotal, uploadTotal, connections, memory}。"""
        return self._request("GET", "/connections")

    def close_connection(self, conn_id: str) -> None:
        self._request("DELETE", f"/connections/{conn_id}")

    def close_all_connections(self) -> None:
        self._request("DELETE", "/connections")

    # ---------- 代理 ----------
    def get_proxies(self) -> dict[str, Any]:
        """返回 {proxies: {name: {...}}}。"""
        return self._request("GET", "/proxies")

    def get_proxy(self, name: str) -> dict[str, Any]:
        return self._request("GET", f"/proxies/{name}")

    def select_proxy(self, group: str, name: str) -> None:
        """在 Selector 类型的代理组中选择节点。"""
        self._request("PUT", f"/proxies/{group}", json={"name": name})

    def test_delay(self, name: str, url: str = "https://www.gstatic.com/generate_204", timeout: int = 15000) -> int:
        """测速，返回延迟毫秒，0 表示失败。

        timeout 为传给 mihomo 的测速超时（毫秒），需大于客户端 HTTP 超秒以等待排队。
        503/504（排队超时/测速超时）静默返回 0，不刷错误日志。
        """
        try:
            data = self._request("GET", f"/proxies/{name}/delay", params={"url": url, "timeout": timeout})
            return int(data.get("delay", 0))
        except MihomoAPIError as e:
            # 503 = mihomo 内部测速异常，504 = 节点超时，都属正常失败，降级为 debug
            if "返回 503" in str(e) or "返回 504" in str(e):
                logger.debug("节点测速超时 %s: %s", name, e)
            else:
                logger.warning("测速失败 %s: %s", name, e)
            return 0

    # ---------- 规则 ----------
    def get_rules(self) -> dict[str, Any]:
        return self._request("GET", "/rules")

    # ---------- 健康检查 ----------
    def health(self) -> bool:
        try:
            self.get_version()
            return True
        except MihomoAPIError:
            return False
