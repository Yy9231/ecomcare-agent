# API 契约

所有受保护接口使用 `Authorization: Bearer <token>`。

| 方法 | 路径 | 用途 |
|---|---|---|
| `POST` | `/api/v1/auth/login` | 使用账号密码登录并获取角色 Token |
| `GET` | `/api/v1/auth/me` | 校验并续期当前登录状态 |
| `POST` | `/api/v1/conversations` | 创建客户会话 |
| `GET` | `/api/v1/conversations` | 查询有权查看的会话 |
| `GET` | `/api/v1/conversations/{id}` | 获取消息、引用、工具轨迹和最新审批状态 |
| `POST` | `/api/v1/conversations/{id}/read` | 客服将客户消息标记为已读 |
| `POST` | `/api/v1/conversations/{id}/messages/stream` | 发送消息并接收 SSE |
| `POST` | `/api/v1/conversations/{id}/human-replies` | 人工客服回复；自动会话会在首次回复时由客服主动接管 |
| `GET` | `/api/v1/approvals` | 客服查询审批列表 |
| `POST` | `/api/v1/approvals/{id}/decision` | 批准或拒绝并恢复工作流 |
| `GET` | `/api/v1/metrics/summary` | 获取真实运行指标 |
| `GET` | `/api/v1/model/status` | 获取脱敏后的当前模型配置，不发起模型调用 |
| `GET` | `/api/v1/model/preferences` | 获取当前账号选择、供应商目录和脱敏配置状态 |
| `PUT` | `/api/v1/model/preferences` | 保存当前账号的 Provider、Model、Base URL 和 API Key |
| `POST` | `/api/v1/model/reply-suggestions/{conversation_id}` | 客服使用自己的模型生成可编辑回复建议 |

SSE 事件包括 `tool_started`、`tool_finished`、`model_finished`、`message_delta`、`approval_required`、`done`、`error`。详细请求和响应 schema 以运行时 `/docs` 为准。

客户和客服账号严格区分角色。客户只能读取自己的会话和订单，客服可查看工作台、审批并主动接管任意客户会话。第一条人工回复会将会话持久化为转人工状态；消息写入 PostgreSQL，重新登录后通过 `GET /conversations` 和 `GET /conversations/{id}` 恢复。

客服会话列表按 `latest_activity_at` 倒序返回，并提供 `unread_count`。只有客户发送的 `user` 消息计入客服未读数；客服打开会话后，服务端记录该会话的最后已读时间。

模型选择写入 `accounts`，每个账号的供应商配置写入 `account_model_configs`，因此退出或换浏览器重新登录后仍保留。API Key 通过服务端密钥加密后保存，接口只返回 `has_api_key`，不会回传明文，也不会进入 Token、浏览器存储或 LangGraph checkpoint。客户配置用于下一条 Agent 消息，客服配置用于“AI 回复建议”。

更新请求中 `api_key` 留空表示保留该账号已经保存的密钥。首次配置需要密钥的云供应商时必须提交 `api_key`；Ollama 可以不填。后端会验证供应商、Model、Base URL 与凭据完整性，但不会在保存时产生模型调用。
