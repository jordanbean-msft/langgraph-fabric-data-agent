"""Authentication helpers for Fabric token acquisition."""

import base64
import json
from dataclasses import dataclass

from azure.core.exceptions import ClientAuthenticationError
from azure.identity import CredentialUnavailableError, DefaultAzureCredential, DeviceCodeCredential

from langgraph_fabric_core.core.config import CoreSettings

_AZURE_CLI_PUBLIC_CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"


@dataclass(slots=True)
class AuthContext:
    """Per-request authentication context."""

    mode: str
    user_id: str
    user_token: str | None = None


@dataclass(slots=True)
class AuthenticatedIdentity:
    """Identity extracted from a local access token."""

    user_id: str
    tenant_id: str


class FabricTokenProvider:
    """Resolve Fabric tokens for local and m365/api scenarios."""

    def __init__(
        self,
        settings: CoreSettings,
        default_credential: DefaultAzureCredential | None = None,
        device_code_credential: DeviceCodeCredential | None = None,
        device_code_fallback_credential: DeviceCodeCredential | None = None,
    ):
        self._settings = settings
        self._device_code_client_id = settings.microsoft_app_id or _AZURE_CLI_PUBLIC_CLIENT_ID
        self._default_credential = default_credential or DefaultAzureCredential()
        self._device_code_credential = device_code_credential or DeviceCodeCredential(
            tenant_id=settings.microsoft_tenant_id or None,
            client_id=self._device_code_client_id,
        )
        self._device_code_fallback_credential = (
            device_code_fallback_credential
            or DeviceCodeCredential(
                tenant_id=settings.microsoft_tenant_id or None,
                client_id=_AZURE_CLI_PUBLIC_CLIENT_ID,
            )
        )

    async def get_token(self, context: AuthContext) -> str:
        """Return an access token for Fabric API."""
        if context.mode != "local":
            if not context.user_token:
                raise ValueError(
                    f"Auth mode '{context.mode}' requires a pre-provided Fabric user token"
                )
            return context.user_token

        return self._get_local_access_token()

    def _get_local_access_token(self) -> str:
        """Acquire a local token using the configured credential fallback chain."""
        configured_tenant = self._settings.microsoft_tenant_id.strip()

        try:
            token = self._default_credential.get_token(self._settings.fabric_data_agent_scope)
            if self._token_matches_configured_tenant(token.token, configured_tenant):
                return token.token
        except (ClientAuthenticationError, CredentialUnavailableError):
            pass

        token = self._get_device_code_token_with_fallback()
        if self._token_matches_configured_tenant(token.token, configured_tenant):
            return token.token

        raise ValueError(
            "Unable to acquire a token for configured MICROSOFT_TENANT_ID. "
            "Ensure your .env tenant matches the authenticated account."
        )

    def _token_matches_configured_tenant(self, token: str, configured_tenant: str) -> bool:
        """Return True when token tenant matches configured tenant, or when no tenant is configured."""
        if not configured_tenant:
            return True

        claims = self._decode_token_claims(token)
        return claims.get("tid") == configured_tenant

    def _get_device_code_token_with_fallback(self):
        """Acquire a device-code token and retry with Azure CLI app ID for invalid client IDs."""
        try:
            return self._device_code_credential.get_token(self._settings.fabric_data_agent_scope)
        except ClientAuthenticationError as exc:
            if self._should_retry_with_azure_cli_public_client(exc):
                return self._device_code_fallback_credential.get_token(
                    self._settings.fabric_data_agent_scope
                )
            raise

    def _should_retry_with_azure_cli_public_client(self, exc: ClientAuthenticationError) -> bool:
        """Detect invalid-client failures from non-public app IDs for device-code auth."""
        if self._device_code_client_id == _AZURE_CLI_PUBLIC_CLIENT_ID:
            return False
        message = str(exc)
        return (
            "AADSTS7000218" in message
            or "client_assertion" in message
            or "client_secret" in message
        )

    @staticmethod
    def _decode_token_claims(token: str) -> dict[str, str]:
        """Decode JWT payload claims from a bearer token."""
        parts = token.split(".")
        if len(parts) < 2:
            return {}

        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding

        try:
            decoded = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded)
        except (ValueError, KeyError, json.JSONDecodeError):
            return {}

        if not isinstance(claims, dict):
            return {}
        return {str(key): str(value) for key, value in claims.items()}

    def get_authenticated_identity(self) -> AuthenticatedIdentity:
        """Extract authenticated local identity from token claims."""
        claims = self._decode_token_claims(self._get_local_access_token())
        user_id = (
            claims.get("preferred_username")
            or claims.get("upn")
            or claims.get("unique_name")
            or claims.get("email")
            or claims.get("oid")
            or "unknown"
        )
        tenant_id = claims.get("tid") or "unknown"
        return AuthenticatedIdentity(user_id=user_id, tenant_id=tenant_id)

    def get_authenticated_user_id(self) -> str:
        """Extract the authenticated user ID (UPN) from the credential token."""
        return self.get_authenticated_identity().user_id
