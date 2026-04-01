"""Authentication helpers for Fabric token acquisition."""

from dataclasses import dataclass

from azure.core.exceptions import ClientAuthenticationError
from azure.identity import CredentialUnavailableError, DefaultAzureCredential, DeviceCodeCredential

from langgraph_fabric_data_agent.core.config import AppSettings


@dataclass(slots=True)
class AuthContext:
    """Per-request authentication context."""

    mode: str
    user_id: str
    hosted_user_token: str | None = None


class FabricTokenProvider:
    """Resolve Fabric tokens for local and hosted scenarios."""

    def __init__(
        self,
        settings: AppSettings,
        default_credential: DefaultAzureCredential | None = None,
        device_code_credential: DeviceCodeCredential | None = None,
    ):
        self._settings = settings
        self._default_credential = default_credential or DefaultAzureCredential()
        self._device_code_credential = device_code_credential or DeviceCodeCredential(
            tenant_id=settings.microsoft_tenant_id or None,
            client_id=settings.microsoft_app_id or "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
        )

    async def get_token(self, context: AuthContext) -> str:
        """Return an access token for Fabric API."""
        if context.mode == "hosted":
            if not context.hosted_user_token:
                raise ValueError("Hosted mode requires a Bot Service user token")
            return context.hosted_user_token

        try:
            token = self._default_credential.get_token(self._settings.fabric_data_agent_scope)
            return token.token
        except (ClientAuthenticationError, CredentialUnavailableError):
            token = self._device_code_credential.get_token(self._settings.fabric_data_agent_scope)
            return token.token
