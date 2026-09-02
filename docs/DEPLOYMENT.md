# 在线部署

## 1. Neon PostgreSQL

1. 创建 PostgreSQL 项目并在 SQL Editor 执行 `CREATE EXTENSION IF NOT EXISTS vector;`。
2. 保存异步 SQLAlchemy URL 为 `DATABASE_URL`，格式为 `postgresql+asyncpg://...`。
3. 保存 psycopg URL 为 `CHECKPOINT_DATABASE_URL`，格式为 `postgresql://...`。
4. 两个 URL 指向同一数据库，但驱动前缀不同；不要提交到 Git。

## 2. Vercel 后端（无银行卡的默认方案）

从 Git 仓库创建第一个 Vercel Project，把 Root Directory 设置为 `backend`。Vercel 会从
`app/main.py` 自动识别 FastAPI，并按照 `backend/vercel.json` 将函数最长执行时间设置为
60 秒。配置以下 Production 环境变量：

```text
DATABASE_URL=postgresql+asyncpg://...?...&ssl=require
CHECKPOINT_DATABASE_URL=postgresql://...?...&sslmode=require
JWT_SECRET=<随机长字符串>
MODEL_CREDENTIALS_SECRET=<随机长字符串>
CORS_ORIGINS=https://your-frontend.vercel.app
PUBLIC_DEMO_MODE=true
MODEL_ENABLED=false
```

`DATABASE_URL` 使用 SQLAlchemy asyncpg 驱动，Neon URL 中的 `sslmode=require` 需要改为
`ssl=require`，并移除 asyncpg 不支持的 `channel_binding` 参数。
`CHECKPOINT_DATABASE_URL` 由 psycopg 使用，保留 Neon 原始参数。两个地址都不得提交到 Git。

部署完成后验证：

```bash
curl -fsS https://your-api.vercel.app/api/v1/health/ready
```

## 3. Render 后端（备选）

仓库根目录已包含 `render.yaml`。从 Git 仓库创建 Blueprint，填写两个数据库 URL和前端域名 `CORS_ORIGINS`。免费公开 Demo 已设置 `PUBLIC_DEMO_MODE=true` 与 `MODEL_ENABLED=false`：所有账号锁定规则模式，不接收或调用外部模型凭据。部署后验证：

```bash
curl -fsS https://your-api.onrender.com/api/v1/health/ready
```

## 4. Vercel 前端

导入仓库并把 Root Directory 设为 `frontend`，配置：

```text
VITE_API_URL=https://your-api.vercel.app/api/v1
```

部署完成后，把前端正式域名写回后端 Project 的 `CORS_ORIGINS` 并重新部署后端。

## 5. 上线验收

- 打开 Vercel 域名，分别使用客户与客服演示账号登录，并确认客户历史会话可以恢复。
- 完成物流查询，确认浏览器收到 `message_delta` 和 `done`。
- 创建退货申请，在客服工作台批准，刷新会话看到售后编号。
- 检查 Vercel Function 日志无数据库、CORS 或 checkpoint 错误。
- 确认模型选择器显示“规则模式（公开演示）”，且不提供外部模型配置入口。
- Vercel Function 可能发生冷启动，正式演示前先访问后端健康检查完成预热。

本地实现不包含真实线上地址。创建 Neon、Render 和 Vercel 资源需要用户账户授权，完成实际部署并验证前，简历不得写“已上线”。
