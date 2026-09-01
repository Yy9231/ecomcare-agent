from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy import text

from app.api import router
from app.auth import router as auth_router
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.model_api import router as model_router
from app.seed import seed_database
from app.services.agent import build_graph
from app.services.model_gateway import resolve_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动顺序固定为：业务表/向量扩展 → 合成数据 → checkpoint → Agent 图。
    # 这样开始接收请求前，数据库与可恢复工作流已经全部就绪。
    settings = get_settings()
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await seed_database(session)
    async with AsyncExitStack() as stack:
        checkpointer = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(settings.checkpoint_database_url)
        )
        # checkpoint 持久化 interrupt 的执行位置，服务重启后仍可恢复审批流程。
        await checkpointer.setup()
        app.state.agent_graph = build_graph(checkpointer)
        app.state.session_factory = SessionLocal
        yield
    await engine.dispose()


app = FastAPI(title="EcomCare Agent API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(auth_router)
app.include_router(model_router)


@app.get("/api/v1/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health/ready")
async def ready() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/api/v1/model/status")
async def model_status() -> dict:
    settings = get_settings()
    if not settings.model_enabled:
        return {
            "enabled": False,
            "provider": "deterministic",
            "model": None,
            "message": "External model is disabled",
        }
    return resolve_model(settings).public_status(enabled=True)
