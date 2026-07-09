from __future__ import annotations

import uvicorn

from proxy_manager.config import settings


def main() -> None:
    uvicorn.run(
        "proxy_manager.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
