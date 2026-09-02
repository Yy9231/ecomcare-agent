import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Account, Customer
from app.schemas import LoginRequest, LoginResponse, RegisterRequest
from app.security import create_token, current_identity, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _registration_id(prefix: str) -> str:
    """生成兼容早期演示库短字段的随机业务 ID。"""
    return f"{prefix}-{secrets.token_hex(6).upper()}"


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


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)):
    """注册普通客户账号；角色固定由服务端写入，不能通过请求提升为客服。"""
    existing = await session.scalar(select(Account).where(Account.username == payload.username))
    if existing:
        raise HTTPException(status_code=409, detail="该账号已被注册")
    customer = Customer(id=_registration_id("CUST"), name=payload.display_name, tier="standard")
    account = Account(
        id=_registration_id("ACC"),
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="customer",
        customer_id=customer.id,
    )
    try:
        # 两个模型没有 ORM relationship，显式 flush 保证外键目标先落库。
        session.add(customer)
        await session.flush()
        session.add(account)
        await session.commit()
    except IntegrityError as exc:
        # 并发注册同一用户名时由数据库唯一约束兜底。
        await session.rollback()
        sqlstate = getattr(exc.orig, "sqlstate", None)
        if sqlstate == "23505":
            raise HTTPException(status_code=409, detail="注册数据冲突，请更换账号后重试") from exc
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试") from exc
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
