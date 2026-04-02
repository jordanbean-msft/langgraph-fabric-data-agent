import base64
import json
from types import SimpleNamespace

import pytest
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import CredentialUnavailableError
from langgraph_fabric_core.core.config import CoreSettings
from langgraph_fabric_core.mcp.auth import AuthContext, TokenProvider

_MCP_SERVERS_JSON = (
    '[{"name":"fabric","description":"Fabric MCP","url":"https://api.fabric.microsoft.com/v1/mcp/demo",'
    '"scope":"https://api.fabric.microsoft.com/.default","oauth_connection_name":"FabricOAuth2"}]'
)


@pytest.fixture(name="settings_fixture")
def settings_fixture_data(monkeypatch):
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/api/projects/demo"
    )
    monkeypatch.setenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "gpt-5.4")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-11-15-preview")
    monkeypatch.setenv("MCP_SERVERS", _MCP_SERVERS_JSON)
    monkeypatch.setenv("MICROSOFT_TENANT_ID", "")
    return CoreSettings()


def _create_settings_with_tenant(monkeypatch, tenant_id: str) -> CoreSettings:
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com/api/projects/demo"
    )
    monkeypatch.setenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "gpt-5.4")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2025-11-15-preview")
    monkeypatch.setenv("MCP_SERVERS", _MCP_SERVERS_JSON)
    monkeypatch.setenv("MICROSOFT_TENANT_ID", tenant_id)
    return CoreSettings()


@pytest.mark.asyncio
async def test_m365_mode_requires_token(settings_fixture):
    provider = TokenProvider(settings_fixture)
    context = AuthContext(
        mode="m365",
        user_id="u1",
        scope="https://api.fabric.microsoft.com/.default",
        user_token=None,
    )
    with pytest.raises(ValueError):
        await provider.get_token(context)


@pytest.mark.asyncio
async def test_api_mode_requires_token(settings_fixture):
    provider = TokenProvider(settings_fixture)
    context = AuthContext(
        mode="api", user_id="u1", scope="https://api.fabric.microsoft.com/.default", user_token=None
    )
    with pytest.raises(ValueError):
        await provider.get_token(context)


@pytest.mark.asyncio
async def test_local_mode_falls_back_to_device_code(settings_fixture):
    tenant_id = settings_fixture.microsoft_tenant_id
    device_token = _create_jwt_token(tid=tenant_id)
    provider = TokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(
            get_token=lambda _scope: (_ for _ in ()).throw(ClientAuthenticationError("x"))
        ),
        device_code_credential=SimpleNamespace(
            get_token=lambda _scope: SimpleNamespace(token=device_token)
        ),
    )

    token = await provider.get_token(
        AuthContext(mode="local", user_id="u1", scope="https://api.fabric.microsoft.com/.default")
    )
    assert token == device_token


@pytest.mark.asyncio
async def test_local_mode_falls_back_to_device_code_when_default_credential_is_unavailable(
    settings_fixture,
):
    tenant_id = settings_fixture.microsoft_tenant_id
    device_token = _create_jwt_token(tid=tenant_id)
    provider = TokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(
            get_token=lambda _scope: (_ for _ in ()).throw(CredentialUnavailableError("x"))
        ),
        device_code_credential=SimpleNamespace(
            get_token=lambda _scope: SimpleNamespace(token=device_token)
        ),
    )

    token = await provider.get_token(
        AuthContext(mode="local", user_id="u1", scope="https://api.fabric.microsoft.com/.default")
    )
    assert token == device_token


@pytest.mark.asyncio
async def test_local_mode_enforces_configured_tenant_and_falls_back_to_device_code(monkeypatch):
    settings = _create_settings_with_tenant(
        monkeypatch,
        tenant_id="11111111-1111-1111-1111-111111111111",
    )
    default_token = _create_jwt_token(
        upn="cli-user@example.com",
        tid="99999999-9999-9999-9999-999999999999",
    )
    device_token = _create_jwt_token(
        upn="tenant-user@example.com",
        tid="11111111-1111-1111-1111-111111111111",
    )

    provider = TokenProvider(
        settings,
        default_credential=SimpleNamespace(
            get_token=lambda _scope: SimpleNamespace(token=default_token)
        ),
        device_code_credential=SimpleNamespace(
            get_token=lambda _scope: SimpleNamespace(token=device_token)
        ),
    )

    token = await provider.get_token(
        AuthContext(mode="local", user_id="u1", scope="https://api.fabric.microsoft.com/.default")
    )
    assert token == device_token


@pytest.mark.asyncio
async def test_local_mode_enforces_configured_tenant_and_raises_when_unmatched(monkeypatch):
    settings = _create_settings_with_tenant(
        monkeypatch,
        tenant_id="11111111-1111-1111-1111-111111111111",
    )
    default_token = _create_jwt_token(
        upn="cli-user@example.com",
        tid="99999999-9999-9999-9999-999999999999",
    )
    device_token = _create_jwt_token(
        upn="wrong-device-user@example.com",
        tid="22222222-2222-2222-2222-222222222222",
    )

    provider = TokenProvider(
        settings,
        default_credential=SimpleNamespace(
            get_token=lambda _scope: SimpleNamespace(token=default_token)
        ),
        device_code_credential=SimpleNamespace(
            get_token=lambda _scope: SimpleNamespace(token=device_token)
        ),
    )

    with pytest.raises(ValueError, match="MICROSOFT_TENANT_ID"):
        await provider.get_token(
            AuthContext(
                mode="local", user_id="u1", scope="https://api.fabric.microsoft.com/.default"
            )
        )


@pytest.mark.asyncio
async def test_local_mode_retries_device_code_with_azure_cli_public_client_on_invalid_client(
    monkeypatch,
):
    settings = _create_settings_with_tenant(
        monkeypatch,
        tenant_id="11111111-1111-1111-1111-111111111111",
    )
    monkeypatch.setenv("MICROSOFT_APP_ID", "18b54e45-71e8-4fb3-8826-80d8c2c02f35")
    monkeypatch.setenv("MCP_SERVERS", _MCP_SERVERS_JSON)
    settings = CoreSettings()

    fallback_token = _create_jwt_token(
        upn="fallback-user@example.com",
        tid="11111111-1111-1111-1111-111111111111",
    )

    provider = TokenProvider(
        settings,
        default_credential=SimpleNamespace(
            get_token=lambda _scope: (_ for _ in ()).throw(ClientAuthenticationError("x"))
        ),
        device_code_credential=SimpleNamespace(
            get_token=lambda _scope: (_ for _ in ()).throw(
                ClientAuthenticationError(
                    "AADSTS7000218: The request body must contain 'client_assertion' or 'client_secret'."
                )
            )
        ),
        device_code_fallback_credential=SimpleNamespace(
            get_token=lambda _scope: SimpleNamespace(token=fallback_token)
        ),
    )

    token = await provider.get_token(
        AuthContext(mode="local", user_id="u1", scope="https://api.fabric.microsoft.com/.default")
    )
    assert token == fallback_token


def _create_jwt_token(
    preferred_username: str | None = None,
    upn: str | None = None,
    unique_name: str | None = None,
    email: str | None = None,
    oid: str | None = None,
    tid: str | None = None,
) -> str:
    """Create a valid JWT token with the given claims."""
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {}
    if preferred_username:
        payload["preferred_username"] = preferred_username
    if upn:
        payload["upn"] = upn
    if unique_name:
        payload["unique_name"] = unique_name
    if email:
        payload["email"] = email
    if oid:
        payload["oid"] = oid
    if tid:
        payload["tid"] = tid

    # Encode header and payload
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    # Signature is fake but valid format
    signature_b64 = base64.urlsafe_b64encode(b"fake-signature").rstrip(b"=").decode()

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def test_get_authenticated_user_id_extracts_upn(settings_fixture):
    """Should extract user principal name (UPN) from token."""
    token = _create_jwt_token(
        upn="user@example.com",
        tid=settings_fixture.microsoft_tenant_id,
    )
    provider = TokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(get_token=lambda _: SimpleNamespace(token=token)),
    )

    user_id = provider.get_authenticated_user_id("https://api.fabric.microsoft.com/.default")
    assert user_id == "user@example.com"


def test_get_authenticated_user_id_prefers_preferred_username_over_upn(settings_fixture):
    token = _create_jwt_token(
        preferred_username="preferred@example.com",
        upn="user@example.com",
        tid=settings_fixture.microsoft_tenant_id,
    )
    provider = TokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(get_token=lambda _: SimpleNamespace(token=token)),
    )

    user_id = provider.get_authenticated_user_id("https://api.fabric.microsoft.com/.default")
    assert user_id == "preferred@example.com"


def test_get_authenticated_user_id_falls_back_to_oid(settings_fixture):
    """Should fall back to OID when UPN is not available."""
    token = _create_jwt_token(
        oid="12345678-1234-1234-1234-123456789012",
        tid=settings_fixture.microsoft_tenant_id,
    )
    provider = TokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(get_token=lambda _: SimpleNamespace(token=token)),
    )

    user_id = provider.get_authenticated_user_id("https://api.fabric.microsoft.com/.default")
    assert user_id == "12345678-1234-1234-1234-123456789012"


def test_get_authenticated_user_id_prefers_upn_over_oid(settings_fixture):
    """Should prefer UPN over OID when both are present."""
    token = _create_jwt_token(
        upn="user@example.com",
        oid="12345678-1234-1234-1234-123456789012",
        tid=settings_fixture.microsoft_tenant_id,
    )
    provider = TokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(get_token=lambda _: SimpleNamespace(token=token)),
    )

    user_id = provider.get_authenticated_user_id("https://api.fabric.microsoft.com/.default")
    assert user_id == "user@example.com"


def test_get_authenticated_user_id_falls_back_to_unique_name_then_email_then_oid(settings_fixture):
    token_with_unique_name = _create_jwt_token(
        unique_name="legacy-user@example.com",
        oid="12345678-1234-1234-1234-123456789012",
        tid=settings_fixture.microsoft_tenant_id,
    )
    provider = TokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(
            get_token=lambda _: SimpleNamespace(token=token_with_unique_name)
        ),
    )
    assert (
        provider.get_authenticated_user_id("https://api.fabric.microsoft.com/.default")
        == "legacy-user@example.com"
    )

    token_with_email = _create_jwt_token(
        email="email-user@example.com",
        oid="12345678-1234-1234-1234-123456789012",
        tid=settings_fixture.microsoft_tenant_id,
    )
    provider = TokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(
            get_token=lambda _: SimpleNamespace(token=token_with_email)
        ),
    )
    assert (
        provider.get_authenticated_user_id("https://api.fabric.microsoft.com/.default")
        == "email-user@example.com"
    )


def test_get_authenticated_user_id_handles_malformed_token(monkeypatch):
    """Should return 'unknown' for a malformed token."""
    settings = _create_settings_with_tenant(monkeypatch, tenant_id="")
    provider = TokenProvider(
        settings,
        default_credential=SimpleNamespace(get_token=lambda _: SimpleNamespace(token="not.a.jwt")),
    )

    user_id = provider.get_authenticated_user_id("https://api.fabric.microsoft.com/.default")
    assert user_id == "unknown"


def test_get_authenticated_user_id_handles_invalid_payload_json(monkeypatch):
    """Should return 'unknown' for invalid JSON in payload."""
    settings = _create_settings_with_tenant(monkeypatch, tenant_id="")
    header_b64 = base64.urlsafe_b64encode(b'{"alg":"RS256"}').rstrip(b"=").decode()
    # Invalid JSON payload
    payload_b64 = base64.urlsafe_b64encode(b"not-json").rstrip(b"=").decode()
    signature_b64 = "sig"
    token = f"{header_b64}.{payload_b64}.{signature_b64}"

    provider = TokenProvider(
        settings,
        default_credential=SimpleNamespace(get_token=lambda _: SimpleNamespace(token=token)),
    )

    user_id = provider.get_authenticated_user_id("https://api.fabric.microsoft.com/.default")
    assert user_id == "unknown"


def test_get_authenticated_user_id_falls_back_to_device_code(settings_fixture):
    """Should use device code credential when default credential fails."""
    token = _create_jwt_token(
        upn="device-user@example.com",
        tid=settings_fixture.microsoft_tenant_id,
    )
    provider = TokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(
            get_token=lambda _: (_ for _ in ()).throw(ClientAuthenticationError("x"))
        ),
        device_code_credential=SimpleNamespace(get_token=lambda _: SimpleNamespace(token=token)),
    )

    user_id = provider.get_authenticated_user_id("https://api.fabric.microsoft.com/.default")
    assert user_id == "device-user@example.com"


def test_get_authenticated_identity_extracts_user_and_tenant(settings_fixture):
    token = _create_jwt_token(
        upn="identity-user@example.com",
        tid="11111111-2222-3333-4444-555555555555",
    )
    provider = TokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(get_token=lambda _: SimpleNamespace(token=token)),
    )

    identity = provider.get_authenticated_identity("https://api.fabric.microsoft.com/.default")
    assert identity.user_id == "identity-user@example.com"
    assert identity.tenant_id == "11111111-2222-3333-4444-555555555555"


def test_get_authenticated_identity_handles_missing_claims(settings_fixture):
    token = _create_jwt_token(tid=settings_fixture.microsoft_tenant_id)
    provider = TokenProvider(
        settings_fixture,
        default_credential=SimpleNamespace(get_token=lambda _: SimpleNamespace(token=token)),
    )

    identity = provider.get_authenticated_identity("https://api.fabric.microsoft.com/.default")
    assert identity.user_id == "unknown"
    assert identity.tenant_id == "unknown"
