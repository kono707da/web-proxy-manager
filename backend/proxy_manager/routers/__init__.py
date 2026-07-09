"""API 路由聚合。"""

from . import auth, connections, limits, proxies, quotas, rules, subscriptions, system, traffic

ALL_ROUTERS = [
    auth.router,
    system.router,
    subscriptions.router,
    proxies.router,
    rules.router,
    connections.router,
    traffic.router,
    limits.router,
    quotas.router,
]
