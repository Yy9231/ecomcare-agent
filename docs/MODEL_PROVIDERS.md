# EcomCare Agent 大模型接入指南

项目通过统一模型 Adapter 接入云端或本地大模型。Agent 路由模块只调用 `invoke_structured()`，供应商的 SDK、鉴权、Base URL 和结构化输出差异由 `backend/app/services/model_gateway.py` 处理。

## 1. 支持范围

| `MODEL_PROVIDER` | 平台 | Adapter | 默认地址 |
|---|---|---|---|
| `openai` | OpenAI | `ChatOpenAI` | `https://api.openai.com/v1` |
| `azure_openai` | Azure OpenAI v1 | `ChatOpenAI` | 必填 |
| `deepseek` | DeepSeek | OpenAI-compatible | `https://api.deepseek.com` |
| `qwen` | 阿里云百炼 / 通义千问 | OpenAI-compatible | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `moonshot` | Moonshot / Kimi | OpenAI-compatible | `https://api.moonshot.cn/v1` |
| `zhipu` | 智谱 GLM | OpenAI-compatible | `https://open.bigmodel.cn/api/paas/v4` |
| `doubao` | 火山方舟 / 豆包 | OpenAI-compatible | `https://ark.cn-beijing.volces.com/api/v3` |
| `siliconflow` | 硅基流动 | OpenAI-compatible | `https://api.siliconflow.cn/v1` |
| `openrouter` | OpenRouter | OpenAI-compatible | `https://openrouter.ai/api/v1` |
| `groq` | Groq | OpenAI-compatible | `https://api.groq.com/openai/v1` |
| `xai` | xAI | OpenAI-compatible | `https://api.x.ai/v1` |
| `mistral` | Mistral AI | OpenAI-compatible | `https://api.mistral.ai/v1` |
| `anthropic` | Anthropic Claude | `ChatAnthropic` | 原生服务地址 |
| `google_genai` | Google Gemini API | `ChatGoogleGenerativeAI` | 原生服务地址 |
| `ollama` | 本地 Ollama | `ChatOllama` | `http://localhost:11434` |
| `openai_compatible` | 任意兼容服务、vLLM、代理网关 | `ChatOpenAI` | 必填 |

各平台可能调整模型 ID、可用区和端点。接入时以供应商控制台为准，并选择支持结构化输出或 Tool Calling 的聊天模型。

## 2. 通用配置

复制环境变量文件：

```bash
cp .env.example .env
```

配置字段：

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=openai
MODEL_API_KEY=your-secret-key
MODEL_BASE_URL=
MODEL_NAME=your-model-id
MODEL_TIMEOUT_SECONDS=30
MODEL_MAX_RETRIES=2
```

- `MODEL_PROVIDER`：选择上表中的供应商。
- `MODEL_API_KEY`：只写入未提交的 `.env`，不要写进代码、README 或前端。
- `MODEL_BASE_URL`：使用预设地址时留空；私有部署、代理和 Azure 时填写。
- `MODEL_NAME`：供应商当前可用且支持结构化输出的精确模型 ID。
- `MODEL_TIMEOUT_SECONDS`：单次调用超时。
- `MODEL_MAX_RETRIES`：SDK 内部最大重试次数。

## 3. 常见平台示例

### OpenAI

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=openai
MODEL_API_KEY=your-openai-key
MODEL_BASE_URL=
MODEL_NAME=gpt-4.1-mini
```

### DeepSeek

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=deepseek
MODEL_API_KEY=your-deepseek-key
MODEL_BASE_URL=
MODEL_NAME=deepseek-chat
```

DeepSeek 的思考模型可能不接受 `response_format=json_schema` 或强制 `tool_choice`。项目会为 `deepseek` 自动使用 JSON Mode，并把目标 JSON Schema 加入 Prompt，最后仍由 Pydantic 严格校验结果。

### 通义千问

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=qwen
MODEL_API_KEY=your-dashscope-key
MODEL_BASE_URL=
MODEL_NAME=qwen-plus
```

### Kimi

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=moonshot
MODEL_API_KEY=your-moonshot-key
MODEL_BASE_URL=
MODEL_NAME=your-current-kimi-model-id
```

### 智谱 GLM

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=zhipu
MODEL_API_KEY=your-zhipu-key
MODEL_BASE_URL=
MODEL_NAME=your-current-glm-model-id
```

### 豆包 / 火山方舟

火山方舟通常使用推理接入点 ID 作为 `MODEL_NAME`，以控制台显示值为准。

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=doubao
MODEL_API_KEY=your-ark-key
MODEL_BASE_URL=
MODEL_NAME=your-endpoint-id
```

### Anthropic Claude

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=anthropic
MODEL_API_KEY=your-anthropic-key
MODEL_BASE_URL=
MODEL_NAME=your-current-claude-model-id
```

该模式使用原生 `ChatAnthropic`，不是用 OpenAI 格式模拟 Claude。

### Google Gemini

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=google_genai
MODEL_API_KEY=your-google-ai-key
MODEL_BASE_URL=
MODEL_NAME=your-current-gemini-model-id
```

该模式使用原生 Gemini Adapter，并使用 JSON Schema 生成路由结果。

### OpenRouter

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=openrouter
MODEL_API_KEY=your-openrouter-key
MODEL_BASE_URL=
MODEL_NAME=provider/model-id
```

### Azure OpenAI v1

`MODEL_NAME` 填 Azure 部署名，地址必须以 `/openai/v1` 指向 v1 接口。

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=azure_openai
MODEL_API_KEY=your-azure-key
MODEL_BASE_URL=https://your-resource.openai.azure.com/openai/v1
MODEL_NAME=your-deployment-name
```

### 本地 Ollama

先在宿主机启动 Ollama 并拉取支持结构化输出的模型：

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=ollama
MODEL_API_KEY=
MODEL_BASE_URL=http://localhost:11434
MODEL_NAME=qwen3:8b
```

如果 FastAPI 在 Docker 容器内而 Ollama 在 macOS 宿主机，将地址改为：

```dotenv
MODEL_BASE_URL=http://host.docker.internal:11434
```

### 自定义 OpenAI-compatible 服务

适合 vLLM、LiteLLM Gateway、企业代理或其他兼容 Chat Completions 的平台：

```dotenv
MODEL_ENABLED=true
MODEL_PROVIDER=openai_compatible
MODEL_API_KEY=your-key-or-placeholder
MODEL_BASE_URL=https://your-gateway.example/v1
MODEL_NAME=your-model-id
```

## 4. 验证接入

配置完成后重新启动后端：

```bash
docker compose up --build
```

查看脱敏状态，该接口不会调用模型，也不会返回 API Key：

```bash
curl -s http://localhost:8000/api/v1/model/status
```

执行一次真实结构化请求：

```bash
make model-check
```

成功时会打印供应商、模型和结构化结果；不会打印 API Key。随后再运行完整测试：

```bash
make test
make eval
```

接入真实模型后应重新记录路由准确率、失败样本、Token、P50/P95 延迟和调用成本。默认确定性评测结果不能替代该轮评测。

## 5. 为界面同时配置多个供应商

`MODEL_PROVIDER`、`MODEL_API_KEY`、`MODEL_NAME` 是默认供应商。若希望客户和客服在界面切换更多供应商，可额外配置单行 JSON：

```dotenv
MODEL_PROVIDER_CONFIGS={"openai":{"api_key":"your-openai-key","model":"gpt-4.1-mini"},"deepseek":{"api_key":"your-deepseek-key","model":"deepseek-chat"},"ollama":{"model":"qwen3:8b","base_url":"http://host.docker.internal:11434"}}
```

每个供应商支持 `api_key`、`model`、`base_url`。这些是服务端默认配置，修改 `.env` 后需要重建后端容器。

客户和客服也可以在各自界面的模型设置面板中自行填写 Provider、Model、Base URL 和 API Key。个人配置优先于服务端默认配置，并按账号隔离：客户配置用于 Agent 意图路由和最终回答，客服配置用于工作台的“AI 回复建议”。

个人 API Key 经过 Fernet 加密后写入 `account_model_configs`，接口只返回是否已经保存密钥。生产环境必须设置稳定且独立的 `MODEL_CREDENTIALS_SECRET`；若后续修改该值，已有密钥需要用户重新填写。

## 6. 常见错误

### `MODEL_API_KEY is required`

云端供应商没有配置密钥。确认密钥只存在于 `.env`，且 Docker Compose 已重新创建后端容器。

### `MODEL_BASE_URL is required`

`azure_openai` 或 `openai_compatible` 没有配置地址。预设平台可以留空，自定义平台不能留空。

### 401 / 403

通常是密钥无效、服务区域不匹配、账户没有模型权限或 Base URL 错误。先用供应商官方最小示例验证同一组配置。

### 404 / model not found

模型 ID 或 Azure/豆包的部署、接入点 ID 不正确。模型名称是供应商配置值，不是页面上的营销名称。

### 结构化输出失败

当前路由要求模型返回符合 Pydantic Schema 的结果。确认所选模型支持 Tool Calling 或原生 JSON Schema；如果兼容端点只支持普通文本，应更换模型，不能把自由文本直接当业务指令。

### Ollama 在 Docker 中无法连接

容器中的 `localhost` 指向容器自身。macOS/Windows Docker Desktop 通常应使用 `host.docker.internal:11434`，同时确认 Ollama 正在监听可访问地址。

## 7. 实现安全边界

- 模型密钥通过 HTTPS 提交，后端用独立密钥加密入库；读取接口不会输出密钥。
- LangGraph checkpoint 只保存 `account_id`，每个节点运行时按账号读取并解密配置。
- Base URL 必须通过服务端格式和协议校验，业务权限不能因模型供应商变化而改变。
- 模型只生成 `RouteDecision`，不能生成 `customer_id` 或任意 SQL。
- 订单归属、退货资格、审批和幂等写入仍由确定性服务层执行。
- 更换模型只改变自然语言路由 Adapter，不改变业务权限模型。

## 8. 官方参考

- [LangChain ChatOpenAI](https://docs.langchain.com/oss/python/integrations/chat/openai)
- [LangChain ChatAnthropic](https://docs.langchain.com/oss/python/integrations/chat/anthropic)
- [LangChain ChatGoogleGenerativeAI](https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai)
- [LangChain ChatOllama](https://docs.langchain.com/oss/python/integrations/chat/ollama)
- [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output)
