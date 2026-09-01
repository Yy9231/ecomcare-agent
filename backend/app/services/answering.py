import json
from dataclasses import dataclass, field

from app.config import Settings, get_settings
from app.services.model_gateway import invoke_text, resolve_model


@dataclass(frozen=True)
class AnswerResult:
    content: str
    used_model: bool = False
    provider: str | None = None
    model: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None


def deterministic_answer(intent: str, result: dict) -> str:
    """将可信工具结果转为稳定回答，也是外部模型失败时的降级输出。"""
    if "error" in result:
        return str(result["error"])
    if intent == "knowledge_query":
        chunks = result.get("chunks", [])
        return "根据知识库：" + "；".join(chunk["content"] for chunk in chunks)
    if intent == "logistics_query":
        status = {"delivered": "已签收", "shipping": "运输中"}.get(
            result["status"], result["status"]
        )
        return (
            f"订单 {result['order_no']} 由 {result['carrier']} 承运，运单号 "
            f"{result['tracking_no']}，当前状态：{status}。"
        )
    if intent == "order_query":
        status = {"delivered": "已签收", "shipping": "运输中"}.get(
            result["status"], result["status"]
        )
        return f"订单 {result['order_no']}：{result['product']}，状态 {status}。"
    if intent == "escalate":
        return "已为你转接人工客服，请稍候。"
    return str(result.get("reason", "暂时无法处理该请求。"))


def _history_text(messages: list) -> str:
    # 只取最近六条消息，控制上下文长度并避免历史无限增长。
    rows: list[str] = []
    for message in messages[-6:]:
        if isinstance(message, dict):
            role, content = message.get("role", "user"), message.get("content", "")
        else:
            role, content = getattr(message, "type", "user"), getattr(message, "content", "")
        if isinstance(content, str) and content.strip():
            rows.append(f"{role}: {content.strip()}")
    return "\n".join(rows)


async def generate_answer(
    user_message: str,
    intent: str,
    tool_result: dict,
    references: list[dict],
    messages: list,
    settings: Settings | None = None,
) -> AnswerResult:
    """让模型只负责表达，不允许覆盖已校验的业务结果与知识引用。"""
    fallback = deterministic_answer(intent, tool_result)
    settings = settings or get_settings()
    if not settings.model_enabled or "error" in tool_result or intent == "escalate":
        return AnswerResult(content=fallback)

    config = resolve_model(settings)
    prompt = (
        "你是 EcomCare 3C 电商 AI 客服。根据已经过服务端权限校验的工具结果回答客户。\n"
        "要求：不得修改或否认工具结果；不得编造订单、物流、政策或审批结果；信息不足时明确说明；"
        "知识问答需说明依据的文档名称；使用自然、简洁的中文，不要输出 JSON 或 Markdown 标题。\n\n"
        f"最近对话：\n{_history_text(messages)}\n\n"
        f"当前问题：{user_message}\n意图：{intent}\n"
        f"工具结果：{json.dumps(tool_result, ensure_ascii=False, default=str)}\n"
        f"知识引用：{json.dumps(references, ensure_ascii=False, default=str)}\n"
        f"确定性参考答案：{fallback}"
    )
    try:
        generated = await invoke_text(prompt, settings)
        return AnswerResult(
            content=generated.content,
            used_model=True,
            provider=generated.provider,
            model=generated.model,
            usage=generated.usage,
        )
    except Exception as exc:
        # 主聊天链路优先保持可用；失败类型进入 trace，但不向客户泄露异常细节。
        return AnswerResult(
            content=fallback,
            provider=config.provider,
            model=config.model,
            error=type(exc).__name__,
        )
