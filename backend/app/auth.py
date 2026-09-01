from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Account, Customer
from app.schemas import LoginRequest, LoginResponse
from app.security import create_token, current_identity, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _response(account: Account, customer: Customer) -> LoginResponse:
    """统一登录与会话恢复的公开响应结构。"""
    return LoginResponse(
        access_token=create_token(account.id, account.customer_id, account.role),
        username=account.username,
        customer_id=account.customer_id,
        display_name=customer.name,
        role=account.role,
    )


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)):
    # 对外统一返回“用户名或密码错误”，避免泄露账号是否存在。
    account = await session.scalar(select(Account).where(Account.username == payload.username))
    if not account or not account.active or not verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    customer = await session.get(Customer, account.customer_id)
    if not customer:
        raise HTTPException(status_code=401, detail="账号未绑定有效身份")
    return _response(account, customer)


@router.get("/me", response_model=LoginResponse)
async def me(
    identity: dict = Depends(current_identity), session: AsyncSession = Depends(get_session)
):
    account = await session.get(Account, identity["account_id"])
    if not account or not account.active:
        raise HTTPException(status_code=401, detail="账号已失效")
    customer = await session.get(Customer, account.customer_id)
    if not customer:
        raise HTTPException(status_code=401, detail="账号未绑定有效身份")
    return _response(account, customer)
