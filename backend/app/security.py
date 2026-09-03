import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

bearer = HTTPBearer(auto_error=False)


PASSWORD_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    """使用随机盐和 PBKDF2 保存密码摘要，数据库不保存明文密码。"""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    """校验密码并用常量时间比较摘要，降低时序侧信道风险。"""
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), base64.b64decode(salt), int(iterations)
        )
        return hmac.compare_digest(base64.b64encode(digest).decode(), expected)
    except (ValueError, TypeError):
        return False


def create_token(account_id: str, customer_id: str, role: str) -> str:
    """签发包含账号、客户身份和角色的短期访问令牌。"""
    settings = get_settings()
    payload = {
        "sub": account_id,
        "customer_id": customer_id,
        "role": role,
        "exp": datetime.now(UTC) + timedelta(minutes=settings.token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_ecomcare_token: str | None = Header(default=None),
) -> dict[str, str]:
    """只从已验签 JWT 构造可信身份，禁止使用请求正文中的 customer_id。"""
    token = x_ecomcare_token or (credentials.credentials if credentials else None)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    try:
        payload = jwt.decode(
            token, get_settings().jwt_secret, algorithms=["HS256"]
        )
        return {
            "account_id": payload["sub"],
            "customer_id": payload["customer_id"],
            "role": payload["role"],
        }
    except (jwt.PyJWTError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def require_agent(identity: dict[str, str] = Depends(current_identity)) -> dict[str, str]:
    if identity["role"] != "agent":
        raise HTTPException(status_code=403, detail="Agent role required")
    return identity


def require_customer(identity: dict[str, str] = Depends(current_identity)) -> dict[str, str]:
    if identity["role"] != "customer":
        raise HTTPException(status_code=403, detail="Customer role required")
    return identity
