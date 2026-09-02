# 简历项目经历

> 只有 `evaluation/REPORT.md` 生成真实结果后，才把其中数字填入简历。

**EcomCare Agent｜3C 电商智能客服系统**
技术栈：Python、FastAPI、LangChain、LangGraph、PostgreSQL、pgvector、React、Docker

- 设计并实现面向订单、物流和售后场景的智能客服 Agent，通过 LangGraph 编排知识检索、业务工具调用、异常降级与多轮会话状态。
- 将订单查询、售后资格判断和数据库写入封装为类型安全工具，加入订单归属校验、幂等控制及人工审批机制，确保高风险操作不可由模型直接执行。
- 基于 pgvector 构建带来源引用的商品与售后政策 RAG，并建立 50 条合成离线评测集；确定性基线的工具选择准确率、任务完成率、`Recall@3` 和安全路由率均为 100%（真实模型效果另行评测）。
- 使用 FastAPI SSE 与 React 实现客户聊天端和客服工作台，通过 Docker Compose 完成本地一键运行，并使用 Vercel Services + Neon 部署公开演示环境。

在线 Demo：<https://ecomcare-agent.vercel.app/#/customer>
