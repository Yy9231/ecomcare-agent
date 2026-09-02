# EcomCare Agent

面向 3C 电商订单、物流与售后的智能客服 Agent。它使用 LangGraph 编排显式工作流，使用 FastAPI 提供 SSE 与审批 API，使用 PostgreSQL + pgvector 保存业务数据和知识向量，并提供 React 客户端与客服工作台。

> 仓库只包含合成客户、商品和订单。默认离线模式不调用付费模型；启用后可接入 OpenAI、DeepSeek、通义千问、Kimi、智谱、豆包、Claude、Gemini、Ollama 及自定义 OpenAI-compatible 服务。

## 核心演示

1. 客户发送“订单 `EC2026080001` 的物流到哪了”，Agent 校验订单归属后调用物流工具。
2. 客户发送“我要为订单 `EC2026080001` 申请退货”，Agent 先执行确定性的七天退货规则，再暂停工作流。
3. 打开独立的客服工作台，批准或拒绝操作。LangGraph 从 PostgreSQL checkpoint 恢复执行；只有批准后才创建售后单。
4. 客户咨询无法开机或保修政策，系统通过 pgvector 返回 Top 3 知识片段及来源。
5. 客户提出投诉或要求转人工后，客服工作台可使用常用语或自定义内容回复，客户页面自动接收人工消息。
6. 客户发送新消息后，对应会话按最后消息时间自动置顶并显示未读红点；客服打开后服务端持久化已读状态。

## 一键启动

```bash
cp .env.example .env
docker compose up --build
```

- 客户体验系统：<http://localhost:5173/#/customer>
- 客服工作台：<http://localhost:5173/#/agent>
- OpenAPI：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/api/v1/health/ready>

首次启动会创建 pgvector 扩展、LangGraph checkpoint 表、业务表，并写入 30 个商品、100 个订单和 95 篇知识片段。每个商品均包含产品介绍、详细参数以及使用与保修说明。

演示登录账号：

- 客户：`customer1` / `customer123`（也可使用 `customer2`）
- 客服：`agent` / `agent123`

客户与客服登录状态分别保存在浏览器中，两个系统可以同时打开。消息和会话保存在 PostgreSQL；关闭页面后再次登录，会自动恢复该客户最近一次会话。

## 本地开发

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload

cd ../frontend
pnpm install --ignore-workspace
pnpm run dev
```

运行检查：

```bash
make test
make eval
```

## 模型配置

修改未提交的 `.env`：

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=deepseek
MODEL_API_KEY=your-key
MODEL_BASE_URL=
MODEL_NAME=deepseek-chat
```

预设供应商不需要填写 `MODEL_BASE_URL`。配置后可在不打印密钥的情况下验证真实连通性：

```bash
make model-check
```

模型先输出经过 Pydantic 校验的意图、订单号与原因，再根据已经校验的工具结果和知识引用生成自然语言回答。客户身份由 JWT 上下文注入，模型不能指定 `customer_id`；订单归属、售后规则、数据库写入和幂等控制全部位于确定性服务层。模型失败时自动回退到确定性回答模板。

公开免费部署建议设置 `PUBLIC_DEMO_MODE=true` 和 `MODEL_ENABLED=false`。此时客户与客服账号均锁定规则模式，界面不会允许共享演示账号保存外部 API Key；本地开发默认不启用此限制。

## 项目资料

- [架构与数据流](docs/ARCHITECTURE.md)
- [中文学习说明](docs/LEARNING_GUIDE.md)
- [项目深度理解与面试手册](docs/PROJECT_DEEP_DIVE_AND_INTERVIEW.md)
- [大模型接入指南](docs/MODEL_PROVIDERS.md)
- [API 契约](docs/API.md)
- [面试演示脚本](docs/DEMO_SCRIPT.md)
- [在线部署指南](docs/DEPLOYMENT.md)
- [简历项目段落](docs/RESUME.md)
- [评测报告](evaluation/REPORT.md)

## 当前边界

- 这是作品集演示系统，不连接真实电商、支付或物流平台。
- 默认哈希 Embedding 用于无密钥、可重复演示；线上作品可替换为同维度 OpenAI-compatible Embedding 并重新索引。
- 登录使用合成账号和 PBKDF2 密码哈希，适合作品演示；生产环境仍应补充注册、找回密码、限流和多因素认证。
- Render、Neon、Vercel 的部署配置需要在对应平台创建项目后填写真实域名和密钥；本仓库不会代替用户创建付费资源。
