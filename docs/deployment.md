# 部署与在线 Demo

> 状态：仓库提供单机生产编排、HTTPS 反向代理和部署步骤。**尚未部署到公网**，因为没有可用的域名、服务器和证书邮箱。开发编排已在本地 Docker 主机的 Windows 环境启动并通过 API 健康检查；生产编排仍需在真实服务器验证。本文档不把“可部署”表述为“已上线”。

## 目标拓扑

```text
Internet
  │  HTTPS (Caddy, 自动证书)
  ▼
Caddy ──/api/*、/media/*、/docs──▶ FastAPI (uvicorn)
  │                                  │
  └──其余路径────────────────▶ Next.js  │
                                     ▼
                              PostgreSQL 16 + pgvector
                                     │
                          uploads_data 卷（书籍图片）
```

Redis、Celery、MinIO 和真实支付网关尚未接入首版代码，生产编排中不包含它们，避免出现“编排存在但业务未使用”的假象。开发 Compose 中的 Redis 与 MinIO 放在 `extras` profile，默认不启动。

## 前置条件

- 一台可运行 Docker 24+ 与 Docker Compose v2 的 Linux 服务器（建议 2 核 4 GB 起）；
- 一个已解析到服务器公网 IP 的域名；
- 服务器放行 80/443 端口；
- 能获取 Let's Encrypt 证书的邮箱。

## 首次部署

```bash
git clone <repo-url> campus-book-loop
cd campus-book-loop
cp .env.prod.example .env.prod
# 编辑 .env.prod：至少替换 PUBLIC_BASE_URL、DOMAIN、ACME_EMAIL、
# POSTGRES_PASSWORD、TOKEN_SECRET
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

启动顺序由编排保证：PostgreSQL 健康检查通过 → API 执行 `alembic upgrade head` 并启动 → Web 启动 → Caddy 申请证书。

`APP_ENV=production` 时 API 会拒绝默认值或少于 32 字符的 `TOKEN_SECRET`；如果容器反复重启，先检查该变量。

验证：

```bash
curl -fsS https://books.example.com/api/v1/textbooks | head
curl -fsS https://books.example.com/health
curl -fsSI https://books.example.com/media/  # 应返回 404/403，而不是内部路径
```

演示账号见 README。首次启动会写入种子数据；`SEED_ON_STARTUP=false` 可关闭。

## 发布更新

```bash
git pull
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

API 容器每次启动都会执行 `alembic upgrade head`，迁移必须是向前兼容的。Web 的 `NEXT_PUBLIC_API_BASE_URL` 是构建期变量，修改域名后必须重新构建 Web 镜像。

## 数据备份与恢复

```bash
# 备份
docker compose --env-file .env.prod -f docker-compose.prod.yml \
  exec -T postgres pg_dump -U campus_book_app campus_book_loop > backup.sql

# 恢复
docker compose --env-file .env.prod -f docker-compose.prod.yml \
  exec -T postgres psql -U campus_book_app campus_book_loop < backup.sql
```

`uploads_data` 卷需要单独备份（例如 `docker run --rm -v uploads_data:/data ... tar`）。数据库里的 `image_url` 只保存相对路径，恢复时必须同时恢复图片卷。

## 重置演示数据

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml down
docker volume rm campus-book-loop_postgres_data campus-book-loop_uploads_data
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

卷名以 Compose 项目名为前缀，执行前用 `docker volume ls` 确认。

## 当前约束

- 单机部署，没有高可用、自动扩缩容和多地域；
- 图片存储在本地卷，不适用于多副本 API；需要横向扩展时应接入 S3/MinIO；
- 支付、退款仍是沙箱状态，不产生真实资金流，不具备资金托管资质；
- 没有接入 Redis、Celery、向量检索和真实教务数据；
- 估价模型使用合成数据，不能作为真实市场准确率；
- 仓库内没有自动化备份、监控告警和日志聚合，需在真实上线前补齐；
- 生产编排未在真实服务器验证；开发编排已在本地 Docker 主机启动并通过 API 健康检查，首次部署生产环境时仍需按上面的验证命令逐项确认。
