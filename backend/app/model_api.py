import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Account, Conversation, Message, ToolTrace
from app.schemas import ModelPreferenceUpdate
from app.security import current_identity, require_agent
from app.services.account_models import (
    ModelConfigInput,
    account_runtime_settings,
    model_preferences,
    save_model_config,
)
from app.services.model_gateway import invoke_text, resolve_model

router = APIRouter(prefix="/api/v1/model", tags=["model"])


async def _account(session: AsyncSession, account_id: str) -> Account:
    account = await session.get(Account, account_id)
    if not account or not account.active:
        raise HTTPException(status_code=401, detail="账号已失效")
    return account


@router.get("/preferences")
async def get_preferences(
    identity: dict = Depends(current_identity),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await model_preferences(session, await _account(session, identity["account_id"]))


@router.put("/preferences")
async def update_preferences(
    payload: ModelPreferenceUpdate,
    identity: dict = Depends(current_identity),
    session: AsyncSession = Depends(get_session),
) -> dict:
    account = await _account(session, identity["account_id"])
    try:
        return await save_model_config(
            session,
            account,
            ModelConfigInput(
                provider=payload.provider,
                model=payload.model,
                base_url=payload.base_url,
                api_key=payload.api_key.get_secret_value(),
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _suggestion_prompt(messages: list[Message]) -> str:
    # 最近八条消息足以提供客服语境，同时限制成本和无关历史干扰。
    history = "\n".join(
        f"{('客户' if item.role == 'user' else '人工客服' if item.role == 'human' else 'Agent')}：{item.content}"
        for item in reversed(messages)
    )
    return (
        "你是 EcomCare 客服坐席助手。根据会话生成一条可直接发送给客户的中文回复建议。"
        "不得承诺未经批准的退款或售后结果；信息不足时说明正在核实；只输出回复正文。\n\n"
        f"会话记录：\n{history}"
    )


@router.post("/reply-suggestions/{conversation_id}")
async def create_reply_suggestion(
    conversation_id: str,
    identity: dict = Depends(require_agent),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """使用客服账号自己的模型生成建议，不自动发送，最终内容仍由客服确认。"""
    account = await _account(session, identity["account_id"])
    conversation = await session.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = (
        await session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(8)
        )
    ).all()
    settings = await account_runtime_settings(session, account)
    if not settings.model_enabled:
        return {
            "content": "您好，我已经收到您的问题，正在为您核实，请稍等片刻。",
            "provider": "deterministic",
            "model": None,
        }
    started = time.perf_counter()
    try:
        generated = await invoke_text(_suggestion_prompt(list(messages)), settings)
        output = {
            "provider": generated.provider,
            "model": generated.model,
            "usage": generated.usage,
        }
        session.add(
            ToolTrace(
                conversation_id=conversation_id,
                tool_name="llm_reply_suggestion",
                success=True,
                output_data=output,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        )
        await session.commit()
        return {"content": generated.content, **output}
    except Exception as exc:
        config = resolve_model(settings)
        session.add(
            ToolTrace(
                conversation_id=conversation_id,
                tool_name="llm_reply_suggestion",
                success=False,
                output_data={"provider": config.provider, "model": config.model, "error": type(exc).__name__},
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        )
        await session.commit()
        raise HTTPException(status_code=502, detail="模型生成回复建议失败，请稍后重试") from exc
