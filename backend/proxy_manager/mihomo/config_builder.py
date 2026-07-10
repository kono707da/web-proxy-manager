from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx
import yaml
from sqlalchemy.orm import Session

from ..config import BASE_DIR, settings
from ..models import Device, Rule, SpeedLimit, Subscription, TrafficQuota

logger = logging.getLogger("proxy_manager.mihomo")

SUB_CACHE_DIR = BASE_DIR / "data" / "mihomo" / "subscriptions"

# 默认兜底规则（自定义规则之后追加）
DEFAULT_RULES: list[str] = [
    "DOMAIN-SUFFIX,local,DIRECT",
    "IP-CIDR,127.0.0.0/8,DIRECT,no-resolve",
    "IP-CIDR,172.16.0.0/12,DIRECT,no-resolve",
    "IP-CIDR,192.168.0.0/16,DIRECT,no-resolve",
    "IP-CIDR,10.0.0.0/8,DIRECT,no-resolve",
    "GEOIP,CN,DIRECT",
    "MATCH,PROXY",
]


def fetch_subscription(url: str, timeout: float = 30.0, use_proxy: bool = False, custom_proxy: str = "") -> list[dict[str, Any]]:
    """拉取订阅链接，解析为 proxies 列表。

    支持 clash/mihomo 格式的 yaml，也兼容 base64 编码的节点列表（简单处理）。
    - use_proxy=True: 通过 mihomo 的 mixed-port（本地 HTTP 代理）拉取，要求 mihomo 已运行。
    - custom_proxy: 直接指定代理 URL（如 http://1.2.3.4:8080），优先级高于 use_proxy。
    """
    proxy_url = None
    if custom_proxy:
        proxy_url = custom_proxy
        logger.info("通过自定义代理 %s 拉取订阅: %s", proxy_url, url)
    elif use_proxy:
        from .manager import get_manager
        mgr = get_manager()
        if not mgr.is_running():
            raise RuntimeError("mihomo 未运行，无法使用代理更新订阅，请先在系统设置中启动内核")
        proxy_url = f"http://127.0.0.1:{settings.mihomo.mixed_port}"
        logger.info("通过内核代理 %s 拉取订阅: %s", proxy_url, url)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, proxy=proxy_url) as client:
            resp = client.get(url, headers={"User-Agent": "clash-verge/v1.0"})
        resp.raise_for_status()
        text = resp.text
        data = yaml.safe_load(text)
        if isinstance(data, dict) and isinstance(data.get("proxies"), list):
            return [p for p in data["proxies"] if isinstance(p, dict) and p.get("name")]
        if isinstance(data, list):
            return [p for p in data if isinstance(p, dict) and p.get("name")]
        logger.warning("订阅 %s 格式无法识别，未解析到 proxies", url)
        return []
    except Exception as e:
        logger.error("拉取订阅 %s 失败: %s", url, e, exc_info=True)
        raise


def save_subscription_cache(sub_id: int, proxies: list[dict[str, Any]]) -> Path:
    """缓存订阅解析结果。"""
    SUB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = SUB_CACHE_DIR / f"{sub_id}.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"proxies": proxies}, f, allow_unicode=True, sort_keys=False)
    return path


def load_subscription_cache(sub_id: int) -> list[dict[str, Any]]:
    path = SUB_CACHE_DIR / f"{sub_id}.yaml"
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        proxies = data.get("proxies") if isinstance(data, dict) else None
        return [p for p in (proxies or []) if isinstance(p, dict) and p.get("name")]
    except Exception as e:
        logger.error("读取订阅缓存 %s 失败: %s", path, e, exc_info=True)
        return []


def _collect_proxies(db: Session) -> list[dict[str, Any]]:
    """合并所有已启用订阅的节点（按 name 去重）。"""
    subs = db.query(Subscription).filter(Subscription.enabled.is_(True)).all()
    seen: set[str] = set()
    proxies: list[dict[str, Any]] = []
    for sub in subs:
        nodes = load_subscription_cache(sub.id)
        for p in nodes:
            name = p.get("name")
            if name and name not in seen:
                seen.add(name)
                proxies.append(p)
    return proxies


def get_node_source_map(db: Session) -> dict[str, str]:
    """返回节点名 → 订阅名映射（用于前端展示节点来源）。

    节点按订阅顺序首次出现时记录来源，与 _collect_proxies 去重逻辑一致。
    """
    subs = db.query(Subscription).filter(Subscription.enabled.is_(True)).all()
    seen: set[str] = set()
    source: dict[str, str] = {}
    for sub in subs:
        nodes = load_subscription_cache(sub.id)
        for p in nodes:
            name = p.get("name")
            if name and name not in seen:
                seen.add(name)
                source[name] = sub.name
    return source


def _apply_speed_limits(proxies: list[dict[str, Any]], db: Session) -> None:
    """将限速规则应用到 proxies。

    mihomo Meta 分支支持 proxy 级别 ``download-speed-limit`` / ``upload-speed-limit``（单位 B/s）。
    - global: 所有节点
    - group: 名称匹配 target 的节点（简化实现）
    - client: mihomo 不支持按客户端限速，跳过（由配额阻断兜底）
    """
    limits = db.query(SpeedLimit).filter(SpeedLimit.enabled.is_(True)).all()
    if not limits:
        return
    global_dl = global_ul = 0
    group_map: dict[str, tuple[int, int]] = {}
    for lim in limits:
        if lim.scope == "global":
            if lim.download_limit and lim.download_limit > global_dl:
                global_dl = lim.download_limit
            if lim.upload_limit and lim.upload_limit > global_ul:
                global_ul = lim.upload_limit
        elif lim.scope == "group":
            cur = group_map.get(lim.target, (0, 0))
            group_map[lim.target] = (
                max(cur[0], lim.download_limit),
                max(cur[1], lim.upload_limit),
            )
    for p in proxies:
        name = p.get("name", "")
        dl = global_dl
        ul = global_ul
        for gname, (gdl, gul) in group_map.items():
            if gname and gname in name:
                dl = max(dl, gdl)
                ul = max(ul, gul)
        if dl > 0:
            p["download-speed-limit"] = dl
        if ul > 0:
            p["upload-speed-limit"] = ul


def _build_proxy_groups(proxy_names: list[str]) -> list[dict[str, Any]]:
    """构建代理组：PROXY(select) + AUTO(url-test)。"""
    groups: list[dict[str, Any]] = []
    candidates = ["DIRECT", *proxy_names] if proxy_names else ["DIRECT"]
    groups.append({
        "name": "PROXY",
        "type": "select",
        "proxies": candidates,
        "icon": "https://fastly.jsdelivr.net/gh/clash-verge-rev/clash-verge-rev@main/docs/logo.png",
    })
    if proxy_names:
        groups.append({
            "name": "AUTO",
            "type": "url-test",
            "url": "https://www.gstatic.com/generate_204",
            "interval": 300,
            "tolerance": 50,
            "proxies": proxy_names,
        })
        # PROXY 组也加入 AUTO 选项
        groups[0]["proxies"].insert(0, "AUTO")
    return groups


def _build_rules(db: Session) -> list[str]:
    """配额阻断规则 + 自定义规则(按 priority 降序) + 默认兜底规则 + 设备路由规则。"""
    rules: list[str] = []
    # 配额超限的客户端 IP 阻断（最高优先级）
    blocked = (
        db.query(TrafficQuota)
        .filter(TrafficQuota.enabled.is_(True), TrafficQuota.blocked.is_(True))
        .all()
    )
    seen_ips: set[str] = set()
    for q in blocked:
        if q.scope == "client" and q.target and q.target not in seen_ips:
            seen_ips.add(q.target)
            rules.append(f"IP-CIDR,{q.target}/32,REJECT,no-resolve")
    # 自定义规则
    custom = (
        db.query(Rule)
        .filter(Rule.enabled.is_(True))
        .order_by(Rule.priority.desc(), Rule.id.asc())
        .all()
    )
    for r in custom:
        rules.append(f"{r.rule_type},{r.value},{r.target}")
    # 默认兜底规则（除 MATCH 外）
    rules.extend(DEFAULT_RULES[:-1])
    # 设备路由规则：按来源 IP 分配固定节点（在 MATCH 之前，国内直连之后）
    devices = (
        db.query(Device)
        .filter(Device.enabled.is_(True))
        .order_by(Device.id.asc())
        .all()
    )
    for d in devices:
        rules.append(f"SRC-IP-CIDR,{d.source_ip}/32,{d.proxy_name}")
    # 最终兜底
    rules.append(DEFAULT_RULES[-1])  # MATCH,PROXY
    return rules


def build_config(db: Session) -> dict[str, Any]:
    """生成完整的 mihomo 配置字典。"""
    proxies = _collect_proxies(db)
    _apply_speed_limits(proxies, db)
    proxy_names = [p["name"] for p in proxies]
    groups = _build_proxy_groups(proxy_names)
    rules = _build_rules(db)

    cfg: dict[str, Any] = {
        "mixed-port": settings.mihomo.mixed_port,
        "allow-lan": settings.mihomo.allow_lan,
        "mode": "rule",
        "log-level": settings.mihomo.log_level,
        "external-controller": f"0.0.0.0:{settings.mihomo.api_port}",
        "secret": settings.mihomo.secret,
        "dns": {
            "enable": True,
            "ipv6": False,
            "enhanced-mode": "fake-ip",
            "fake-ip-range": "198.18.0.1/16",
            "nameserver": ["https://dns.alidns.com/dns-query", "https://doh.pub/dns-query"],
            "fallback": ["https://1.1.1.1/dns-query", "https://dns.google/dns-query"],
        },
        "proxies": proxies,
        "proxy-groups": groups,
        "rules": rules,
    }
    if settings.mihomo.enable_tun:
        cfg["tun"] = {
            "enable": True,
            "stack": "gvisor",
            "dns-hijack": ["any:53"],
            "auto-route": True,
            "auto-detect-interface": True,
        }
    return cfg


def write_config(db: Session, path: Path | None = None) -> Path:
    """生成并写入 mihomo config.yaml，返回路径。"""
    if path is None:
        path = BASE_DIR / settings.mihomo.work_dir / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg = build_config(db)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    logger.info("mihomo 配置已写入 %s（proxies=%d）", path, len(cfg.get("proxies", [])))
    return path
