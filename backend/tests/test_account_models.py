import pytest
from pydantic import SecretStr

from app.config import Settings
from app.models import Account, AccountModelConfig
from app.services.account_models import (
    ModelConfigInput,
    account_runtime_settings,
    decrypt_api_key,
    encrypt_api_key,
    save_model_config,
)


def settings(secret: str = "credential-secret") -> Settings:
    return Settings(
        _env_file=None,
        jwt_secret="jwt-secret",
        model_enabled=False,
        model_credentials_secret=SecretStr(secret),
    )


class Result:
    def __init__(self, rows: list[AccountModelConfig]):
        self.rows = rows

    def all(self) -> list[AccountModelConfig]:
        return self.rows


class FakeSession:
    def __init__(self):
        self.configs: list[AccountModelConfig] = []

    async def scalar(self, statement):
        return self.configs[0] if self.configs else None

    async def scalars(self, statement) -> Result:
        return Result(self.configs)

    def add(self, record: AccountModelConfig) -> None:
        if record not in self.configs:
            self.configs.append(record)

    async def commit(self) -> None:
        return None


def account() -> Account:
    return Account(
        id="account-1",
        username="customer1",
        password_hash="hash",
        role="customer",
        customer_id="CUST-001",
    )


def test_api_key_encryption_round_trip_never_stores_plaintext() -> None:
    ciphertext = encrypt_api_key("sk-private-value", settings())
    assert "sk-private-value" not in ciphertext
    assert decrypt_api_key(ciphertext, settings()) == "sk-private-value"


def test_changed_encryption_secret_rejects_ciphertext() -> None:
    ciphertext = encrypt_api_key("sk-private-value", settings("first"))
    with pytest.raises(ValueError, match="无法解密"):
        decrypt_api_key(ciphertext, settings("second"))


@pytest.mark.asyncio
async def test_personal_config_is_saved_and_used_without_exposing_key() -> None:
    session = FakeSession()
    owner = account()
    preferences = await save_model_config(
        session,
        owner,
        ModelConfigInput(
            provider="deepseek",
            model="deepseek-chat",
            base_url="https://api.deepseek.com/",
            api_key="sk-account-secret",
        ),
        settings(),
    )
    assert owner.model_provider == "deepseek"
    assert session.configs[0].base_url == "https://api.deepseek.com"
    assert "sk-account-secret" not in str(preferences)
    assert preferences["selected"]["source"] == "account"
    runtime = await account_runtime_settings(session, owner, settings())
    assert runtime.model_name == "deepseek-chat"
    assert runtime.model_api_key.get_secret_value() == "sk-account-secret"


@pytest.mark.asyncio
async def test_blank_key_preserves_existing_encrypted_key() -> None:
    session = FakeSession()
    owner = account()
    first = ModelConfigInput("deepseek", "deepseek-chat", api_key="first-secret")
    await save_model_config(session, owner, first, settings())
    ciphertext = session.configs[0].api_key_encrypted
    second = ModelConfigInput("deepseek", "deepseek-reasoner", api_key="")
    await save_model_config(session, owner, second, settings())
    assert session.configs[0].api_key_encrypted == ciphertext
    runtime = await account_runtime_settings(session, owner, settings())
    assert runtime.model_name == "deepseek-reasoner"
    assert runtime.model_api_key.get_secret_value() == "first-secret"


@pytest.mark.asyncio
async def test_cloud_base_url_rejects_private_network() -> None:
    with pytest.raises(ValueError, match="内部网络"):
        await save_model_config(
            FakeSession(),
            account(),
            ModelConfigInput("openai_compatible", "model", "https://127.0.0.1:8080", "key"),
            settings(),
        )


@pytest.mark.asyncio
async def test_public_demo_forces_rule_mode_and_rejects_external_config() -> None:
    public_settings = settings().model_copy(
        update={"public_demo_mode": True, "model_enabled": True}
    )
    session = FakeSession()
    owner = account()
    runtime = await account_runtime_settings(session, owner, public_settings)
    assert runtime.model_enabled is False
    with pytest.raises(ValueError, match="锁定规则模式"):
        await save_model_config(
            session,
            owner,
            ModelConfigInput("deepseek", "deepseek-v4-flash", api_key="test-key"),
            public_settings,
        )
