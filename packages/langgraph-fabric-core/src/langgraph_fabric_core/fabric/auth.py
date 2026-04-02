"""Authentication helpers for Fabric token acquisition."""

from dataclasses import dataclass

from azure.core.exceptions import ClientAuthenticationError
from azure.identity import CredentialUnavailableError, DefaultAzureCredential, DeviceCodeCredential

from langgraph_fabric_core.core.config import CoreSettings


@dataclass(slots=True)
class AuthContext:
    """Per-request authentication context."""

    mode: str
    user_id: str
    user_token: str | None = None


class FabricTokenProvider:
    """Resolve Fabric tokens for local and m365/api scenarios."""

    def __init__(
        self,
        settings: CoreSettings,
        default_credential: DefaultAzureCredential | None = None,
        device_code_credential: DeviceCodeCredential | None = None,
    ):
        self._settings = settings
        self._default_credential = default_credential or DefaultAzureCredential()
        self._device_code_credential = device_code_credential or DeviceCodeCredential(
            tenant_id=settings.microsoft_tenant_id or None,
            # Fallback to the first-party Azure CLI public client app ID.
            client_id=settings.microsoft_app_id or "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
        )

    async def get_token(self, context: AuthContext) -> str:
        """Return an access token for Fabric API."""
        if context.mode != "local":
            if not context.user_token:
                raise ValueError(
                    f"Auth mode '{context.mode}' requires a pre-provided Fabric user token"
                )
            return context.user_token

        try:
            token = self._default_credential.get_token(self._settings.fabric_data_agent_scope)
            return token.token
        except (ClientAuthenticationError, CredentialUnavailableError):
            token = self._device_code_credential.get_token(self._settings.fabric_data_agent_scope)
            return token.token
