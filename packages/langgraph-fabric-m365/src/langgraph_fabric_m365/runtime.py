"""M365 runtime configuration helpers."""

from os import environ
from typing import Final

from langgraph_fabric_m365.config import M365Settings

REQUIRED_SERVICE_CONNECTION_KEYS: Final[tuple[str, ...]] = (
    "connections_service_connection_id",
    "connections_service_connection_name",
    "connections_service_connection_client_id",
    "connections_service_connection_tenant_id",
    "connections_service_connection_auth_type",
    "connections_service_connection_client_secret",
)


def build_m365_environment(settings: M365Settings) -> dict[str, str]:
    """Build M365 SDK environment from process vars plus strongly-typed settings."""
    m365_env = dict(environ)
    m365_env.update(
        {
            "MICROSOFT_APP_ID": settings.microsoft_app_id,
            "MICROSOFT_APP_PASSWORD": settings.microsoft_app_password,
            "MICROSOFT_TENANT_ID": settings.microsoft_tenant_id,
            "CONNECTIONS__SERVICE_CONNECTION__ID": settings.connections_service_connection_id,
            "CONNECTIONS__SERVICE_CONNECTION__NAME": settings.connections_service_connection_name,
            "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID": settings.connections_service_connection_client_id,
            "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID": settings.connections_service_connection_tenant_id,
            "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__AUTHTYPE": settings.connections_service_connection_auth_type,
            "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET": settings.connections_service_connection_client_secret,
        }
    )

    return m365_env


def build_m365_sdk_configuration(settings: M365Settings) -> dict[str, dict]:
    """Build structured SDK config expected by the Microsoft Agents runtime."""
    missing_keys = [key for key in REQUIRED_SERVICE_CONNECTION_KEYS if not getattr(settings, key)]
    if missing_keys:
        missing = ", ".join(missing_keys)
        raise ValueError(
            "Missing required M365 service connection settings: "
            f"{missing}. Configure these in .env (see .env.example) or export them in your shell."
        )

    return {
        "CONNECTIONS": {
            "SERVICE_CONNECTION": {
                "ID": settings.connections_service_connection_id,
                "NAME": settings.connections_service_connection_name,
                "SETTINGS": {
                    "CLIENTID": settings.connections_service_connection_client_id,
                    "TENANTID": settings.connections_service_connection_tenant_id,
                    "AUTHTYPE": settings.connections_service_connection_auth_type,
                    "CLIENTSECRET": settings.connections_service_connection_client_secret,
                },
            }
        }
    }
