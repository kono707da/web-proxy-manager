# Proxy Manager

基于 [mihomo (Clash.Meta)](https://github.com/MetaCubeX/mihomo) 内核的 Linux Docker 代理管理器，通过网页进行流量控制。参考 [clash-verge-rev](https://github.com/clash-verge-rev/clash-verge-rev) 的设计思路，将其能力搬到服务端，以 Docker 形式部署，通过 Web UI 统一管理。

## 功能特性

- **节点 / 订阅管理**：支持订阅链接拉取、缓存、定时更新；节点分组（select / url-test 自动测速）。
- **规则路由**：自定义规则（DOMAIN / IP-CIDR / GEOIP / MATCH 等），支持优先级排序；内置默认规则（国内直连 + 兜底走代理）。
- **流量统计与连接管理**：实时上下行流量、当前活跃连接列表、按连接关闭、内存占用监控。
- **限速 / 配额控制**：
  - 限速：支持 global / group / client 三种粒度，通过 mihomo 的 `download-speed-limit` / `upload-speed-limit` 实现。
  - 配额：按客户端 IP 累计流量，超限自动生成 `IP-CIDR,x.x.x.x/32,REJECT` 阻断规则并热重载配置。
- **Web 管理界面**：黑金主题 SPA，9 个功能页面，登录态持久化，前后端合并到单端口 8000。

## 技术栈

| 层 | 技术 |
|---|---|
| 代理内核 | mihomo (Clash.Meta) |
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| 认证 | bcrypt + JWT (python-jose)，手写 Header Bearer 依赖 |
| 前端 | Vue 3 + Pinia + reka-ui (shadcn-vue) + Tailwind CSS |
| 部署 | Docker 多阶段构建，前后端合并到单端口 |

## 端口说明

| 端口 | 用途 |
|---|---|
| 9000 | Web 管理界面（宿主机映射端口，容器内仍监听 8000） |
| 7890 | 代理混合端口（同时支持 HTTP / SOCKS5，客户端配置此端口即可） |
| 9090 | mihomo external-controller（仅容器内部通信，**不要对外暴露**） |

> 注：容器内部监听 8000 端口，通过 docker 端口映射 `9000:8000` 对外暴露为 9000，避免与同机其他服务冲突。如需改用其他宿主机端口，修改 docker-compose.yml 或 docker run 的 `-p` 参数即可。

## Docker 部署

### 1. 构建镜像

```bash
# 默认构建（amd64）
docker build -t proxy-manager .

# 指定架构（如 arm64）
docker build --build-arg MIHOMO_ARCH=arm64 -t proxy-manager .

# 网络不稳定时通过代理下载 mihomo 内核
docker build --build-arg HTTP_PROXY=http://192.168.188.1:7897 -t proxy-manager .
```

### 2. 启动容器

使用 docker-compose（推荐）：

```bash
# 使用默认镜像标签 latest
docker compose up -d

# 指定镜像标签（配合 Jenkins CI/CD）
IMAGE_TAG=10 docker compose up -d
```

或直接 docker run：

```bash
docker run -d \
  --name proxy-manager \
  --restart unless-stopped \
  -p 9000:8000 \
  -p 7890:7890 \
  -v proxy-manager-data:/app/backend/data \
  -e TZ=Asia/Shanghai \
  proxy-manager
```

### 3. 访问

- Web 界面：`http://<服务器IP>:9000`
- 默认管理员账号：`admin` / `admin123`（**首次登录后请立即在设置页修改密码**）
- 客户端代理配置：HTTP 或 SOCKS5 指向 `<服务器IP>:7890`

## 本地开发

### 前置条件

- Node.js 20+
- Python 3.12+
- mihomo 二进制（放入 PATH，或修改 `backend/config.yaml` 的 `mihomo.binary` 为绝对路径）

### 启动

Windows 下直接运行项目根目录的 `start.bat`：

```bat
start.bat
```

启动脚本会：
1. 检查 8000 端口占用情况：本应用占用则自动杀掉重启；其他程序占用则提示用户。
2. 检查前端是否已构建（`frontend/dist` 存在），不存在则自动 `npm run build`。
3. 检查 mihomo 二进制是否可用。
4. 启动后端（uvicorn），同时服务前端静态文件。

### 前端热更新开发

```bash
cd frontend
npm install
npm run dev    # Vite dev server，自动代理 /api 到 127.0.0.1:8000
```

后端单独启动：

```bash
cd backend
pip install -r requirements.txt
python run.py
```

## 配置说明

配置通过三层加载（优先级从低到高）：

1. `backend/config.yaml` —— 默认配置，提交到版本库
2. 环境变量（前缀 `PROXY_MANAGER_`，如 `PROXY_MANAGER_PORT=8000`）
3. `backend/data/settings.json` —— 敏感配置（如 mihomo secret），首次启动自动生成，不提交到版本库

关键配置项见 `backend/config.yaml`，均有中文注释。

## 数据持久化

所有运行时数据存储在 `backend/data/` 目录（Docker 中挂载到 `proxy-manager-data` volume）：

- `proxy_manager.db` —— SQLite 数据库（用户、订阅、规则、限速、配额、流量统计）
- `mihomo/config.yaml` —— mihomo 运行配置（由后端自动生成）
- `mihomo/subscriptions/{id}.yaml` —— 订阅缓存
- `settings.json` —— 敏感配置（mihomo secret）

> **警告**：绝对不要删除 `proxy_manager.db`，会永久丢失所有配置与历史数据。

## 项目结构

```
proxy-manager/
├── backend/
│   ├── proxy_manager/
│   │   ├── mihomo/            # mihomo 内核管理
│   │   │   ├── client.py      # RESTful API 客户端
│   │   │   ├── config_builder.py  # 配置生成（订阅解析、限速、配额阻断规则）
│   │   │   └── manager.py     # 进程管理 + 流量监控 + 配额检查循环
│   │   ├── routers/           # 9 个 API 路由模块
│   │   ├── config.py          # 三层配置加载
│   │   ├── database.py        # SQLAlchemy 初始化
│   │   ├── models.py          # 6 个数据表
│   │   ├── schemas.py         # Pydantic 模型
│   │   ├── security.py        # 密码哈希 + JWT
│   │   ├── deps.py            # 认证依赖
│   │   └── main.py            # FastAPI 入口
│   ├── config.yaml
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   └── src/
│       ├── api/               # 9 个 API 调用模块
│       ├── views/             # 9 个页面
│       ├── stores/            # Pinia auth store
│       ├── components/ui/     # shadcn-vue 组件库
│       └── router/            # 路由 + 登录守卫
├── Dockerfile                 # 多阶段构建
├── docker-compose.yml
├── start.bat                  # Windows 启动脚本
└── kill_stale_port.ps1        # 端口检查脚本
```

## API 概览

所有 API 前缀 `/api`，除 `/api/auth/login` 外均需 Bearer token。

| 模块 | 路径 | 说明 |
|---|---|---|
| 认证 | `/api/auth` | login / refresh / me |
| 系统 | `/api/system` | 内核启停 / 模式 / 日志级别 / 状态 |
| 订阅 | `/api/subscriptions` | CRUD / 立即更新 / 批量更新 |
| 节点 | `/api/proxies` | 列表 / 分组 / 选择节点 / 测速 |
| 规则 | `/api/rules` | CRUD（写操作触发配置热重载） |
| 连接 | `/api/connections` | 列表 / 关闭单个 / 关闭全部 |
| 流量 | `/api/traffic` | 实时流量 / 内存 / 历史统计（可重置） |
| 限速 | `/api/limits` | CRUD（global / group / client） |
| 配额 | `/api/quotas` | CRUD / 重置使用量 |

## 致谢

- [mihomo (Clash.Meta)](https://github.com/MetaCubeX/mihomo) —— 代理内核
- [clash-verge-rev](https://github.com/clash-verge-rev/clash-verge-rev) —— 设计参考
