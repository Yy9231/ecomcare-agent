import asyncio
import json

from pydantic import BaseModel, Field

from app.config import get_settings
from app.services.model_gateway import invoke_structured, resolve_model


class ConnectionResult(BaseModel):
    ok: bool
    message: str = Field(description="一句简短中文回复")


async def check() -> None:
    settings = get_settings()
    if not settings.model_enabled:
        raise SystemExit("MODEL_ENABLED=false; enable a provider before running model-check")
    config = resolve_model(settings)
    print(json.dumps(config.public_status(True), ensure_ascii=False, indent=2))
    result = await invoke_structured(
        "返回 ok=true，并用一句中文说明模型连接成功。",
        ConnectionResult,
        settings,
    )
    print(result.model_dump_json(indent=2))


def main() -> None:
    asyncio.run(check())


if __name__ == "__main__":
    main()
