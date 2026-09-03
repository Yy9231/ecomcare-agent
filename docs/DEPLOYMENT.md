# 在线部署

当前已验证的公开 Demo：

- 客户：<https://ecomcare-agent.vercel.app/#/customer>
- 客服：<https://ecomcare-agent.vercel.app/#/agent>
- API：<https://ecomcare-agent.vercel.app/api/docs>

## 1. 国内访问：魔搭 Docker 创空间（免费方案）

仓库根目录的 `Dockerfile` 会先构建 React，再把静态文件复制进 FastAPI 镜像。
FastAPI 在创空间规定的 `0.0.0.0:7860` 上同时提供页面、API 与 SSE，因此浏览器与
后端使用同一个域名，不需要额外配置跨域。`ms_deploy.json` 声明了 Docker SDK、
免费 CPU 资源和 7860 端口。

创建公开的 Docker 创空间后，将仓库代码推送到创空间的 `master` 分支，并在创空间
的 Secrets 中配置以下敏感变量：

```text
DATABASE_URL=<Neon 标准 PostgreSQL 连接串>
CHECKPOINT_DATABASE_URL=<同一条 Neon 连接串>
JWT_SECRET=<随机长字符串>
MODEL_CREDENTIALS_SECRET=<另一个随机长字符串>
```

在 Variables 中配置非敏感开关：

```text
PUBLIC_DEMO_MODE=false
MODEL_ENABLED=false
CORS_ORIGINS=https://<你的创空间域名>
```

`PUBLIC_DEMO_MODE=false` 允许客户和客服分别在界面保存自己的模型、
Base URL 和 API Key；API Key 使用 `MODEL_CREDENTIALS_SECRET` 加密后才写入
Neon，不会明文返回前端。`MODEL_ENABLED=false` 只表示不提供全局共享
模型，不影响账号自行配置。

验证地址：

```bash
curl -fsS https://<owner>-<studio>.ms.show/api/v1/health/ready
```

魔搭 Docker 创空间需先完成阿里云账号绑定与实名认证。免费实例可能
休眠，但用于简历公开 Demo 时可保留 Vercel 地址作为备用。

## 2. Neon PostgreSQL

1. 创建 PostgreSQL 项目并在 SQL Editor 执行 `CREATE EXTENSION IF NOT EXISTS vector;`。
2. 保存异步 SQLAlchemy URL 为 `DATABASE_URL`，格式为 `postgresql+asyncpg://...`。
3. 保存 psycopg URL 为 `CHECKPOINT_DATABASE_URL`，格式为 `postgresql://...`。
4. 两个 URL 指向同一数据库，但驱动前缀不同；不要提交到 Git。

## 3. Vercel 前后端（备用方案）

仓库根目录的 `vercel.json` 把前端和后端定义为同一个 Project 的两个 Service：静态页面
交给 `frontend`，`/api/*` 请求转发到 `backend`。Vercel 会从 `app/main.py` 自动识别
FastAPI，并按照 `backend/vercel.json` 将函数最长执行时间设置为 60 秒。配置以下
Production 环境变量：

```text
DATABASE_URL=postgresql://...?...&sslmode=require
CHECKPOINT_DATABASE_URL=postgresql://...?...&sslmode=require
JWT_SECRET=<随机长字符串>
MODEL_CREDENTIALS_SECRET=<随机长字符串>
PUBLIC_DEMO_MODE=true
MODEL_ENABLED=false
```

两个数据库变量可以粘贴同一条 Neon 标准连接串：应用会在内存中把 `DATABASE_URL`
安全转换成 asyncpg 格式，`CHECKPOINT_DATABASE_URL` 则保留给 psycopg 使用。连接串不得
提交到 Git。

部署完成后验证：

```bash
curl -fsS https://your-project.vercel.app/api/v1/health/ready
```

## 4. Render 后端（备选）

仓库根目录已包含 `render.yaml`。从 Git 仓库创建 Blueprint，填写两个数据库 URL和前端域名 `CORS_ORIGINS`。免费公开 Demo 已设置 `PUBLIC_DEMO_MODE=true` 与 `MODEL_ENABLED=false`：所有账号锁定规则模式，不接收或调用外部模型凭据。部署后验证：

```bash
curl -fsS https://your-api.onrender.com/api/v1/health/ready
```

## 5. 上线验收

- 打开 Vercel 域名，分别使用客户与客服演示账号登录，并确认客户历史会话可以恢复。
- 线上独立入口分别为 `/#/customer` 与 `/#/agent`；Hash 路由确保刷新时仍由 CDN 返回前端入口。
- 完成物流查询，确认浏览器收到 `message_delta` 和 `done`。
- 创建退货申请，在客服工作台批准，刷新会话看到售后编号。
- 检查 Vercel Function 日志无数据库、CORS 或 checkpoint 错误。
- 确认模型选择器显示“规则模式（公开演示）”，且不提供外部模型配置入口。
- Vercel Function 可能发生冷启动，正式演示前先访问后端健康检查完成预热。

当前 Vercel + Neon 环境已经完成健康检查、双角色登录、物流查询及“退货申请 → 人工审批 → 恢复执行”验收。
