# ---------- 阶段1: 构建前端 ----------
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---------- 阶段2: 运行时 ----------
FROM python:3.12-slim

WORKDIR /app

# 下载 mihomo 内核（可通过 build-arg 指定版本/架构/代理）
ARG MIHOMO_VERSION=1.19.20
ARG MIHOMO_ARCH=amd64
ARG HTTP_PROXY=""
ARG HTTPS_PROXY=""
ENV http_proxy=${HTTP_PROXY} https_proxy=${HTTPS_PROXY}

RUN apt-get update && apt-get install -y --no-install-recommends wget gzip ca-certificates && \
    wget -q --tries=3 --timeout=30 \
      "https://github.com/MetaCubeX/mihomo/releases/download/v${MIHOMO_VERSION}/mihomo-linux-${MIHOMO_ARCH}-v${MIHOMO_VERSION}.gz" \
      -O /tmp/mihomo.gz && \
    gzip -d /tmp/mihomo.gz && \
    chmod +x /tmp/mihomo && \
    mv /tmp/mihomo /usr/local/bin/mihomo && \
    apt-get purge -y wget gzip && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

ENV http_proxy="" https_proxy=""

# 安装 Python 依赖
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 复制后端代码
COPY backend/ /app/backend/

# 复制前端构建产物（前后端合并到单端口 8000）
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# 创建数据目录
RUN mkdir -p /app/backend/data/mihomo

# 8000 = Web 管理界面；7890 = 代理混合端口(HTTP/SOCKS5)
EXPOSE 8000 7890

VOLUME ["/app/backend/data"]

ENV TZ=Asia/Shanghai
ENV PROXY_MANAGER_HOST=0.0.0.0
ENV PROXY_MANAGER_PORT=8000

WORKDIR /app/backend

CMD ["python", "run.py"]
