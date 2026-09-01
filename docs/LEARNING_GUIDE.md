# 从一次客服请求理解 Agent 项目

## 1. RAG、Embedding 和向量检索

RAG 的目标不是“让模型记住文档”，而是在回答前取回相关事实。知识文档先被切成独立片段；Embedding 把文本转换为向量；pgvector 根据查询向量和文档向量的余弦距离返回最相近的三个片段。回答同时返回 `title`、`source` 和 `version`，便于核查依据。

默认 `HashingEmbedder` 不需要密钥，适合离线演示和测试，但语义能力有限。真实部署应替换成同维度的中文 Embedding 模型、重新索引，并用 `Recall@3` 比较效果。

## 2. Tool Calling 与普通聊天

普通聊天只生成文本，无法可靠查询实时订单。Tool Calling 让模型输出受约束的结构化决策，例如：

```json
{"intent":"logistics_query","order_no":"EC2026080001","confidence":0.96}
```

服务端根据这个决策调用固定函数。模型没有数据库连接，也不能生成 SQL。即使模型写错订单号，`get_owned_order` 仍会同时匹配服务端注入的 `customer_id`，从而阻止越权读取。

## 3. LangChain 与 LangGraph 的职责

LangChain 负责模型适配与 Pydantic 结构化输出；LangGraph 负责节点、条件分支、checkpoint、暂停和恢复。这个项目没有把所有逻辑塞进一段 Prompt，而是把路由、工具、审批和回复拆成可测试节点。

## 4. 为什么规则不能交给模型

七天退货期限、订单归属和幂等写入属于确定性业务规则。同一个输入必须得到同一个结果，而且结果需要审计。大模型可能幻觉或受提示词注入影响，因此只能提出意图，不能决定权限或直接写数据库。

## 5. SSE 如何工作

浏览器发送消息后保持 HTTP 连接，FastAPI 按顺序发送：

```text
event: tool_started
data: {"name":"get_logistics"}

event: message_delta
data: {"content":"订单正在运输中"}
```

客户端按空行切分事件，并合并多行 `data:`。SSE 适合服务器单向流式输出，比 WebSocket 更容易接入普通 HTTP 基础设施。

## 6. Checkpoint 与人工审批

`thread_id` 对应一条会话。售后节点调用 `interrupt` 后，LangGraph 将当前状态保存到 PostgreSQL并停止。客服提交 `approve` 或 `reject` 后，API 使用 `Command(resume=...)` 恢复同一线程。批准分支才调用 `create_after_sales`，并通过 `idempotency_key` 防止重复写入。

## 7. 如何评价 Agent

- 工具选择准确率：意图是否路由到正确工具。
- 任务完成率：工具、订单号和结果是否共同满足用户目标。
- `Recall@3`：正确知识来源是否出现在前三个检索结果。
- 不安全操作拦截率：越权或绕过审批的请求是否都被阻止。
- 延迟和 Token：上线后还要衡量体验与成本。

面试时不要只展示成功对话。主动演示错误订单号、其他客户订单、过期退货和拒绝审批，能更好体现工程能力。
