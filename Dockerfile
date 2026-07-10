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

# mihomo 内核由后端运行时自动下载到 /app/backend/data/mihomo/（挂载卷内，持久化）
# 构建阶段无需访问 GitHub，加快构建速度

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
