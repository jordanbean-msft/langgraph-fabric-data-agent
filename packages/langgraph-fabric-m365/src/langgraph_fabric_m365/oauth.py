"""M365 OAuth helpers for sign-in cards and token redemption."""

import logging
import re
from typing import Any, Final

from aiohttp.client_exceptions import ClientResponseError
from microsoft_agents.activity import Activity, ActivityTypes, TokenExchangeState
from microsoft_agents.hosting.core import TurnState

from langgraph_fabric_m365.config import M365Settings

logger = logging.getLogger(__name__)

MAGIC_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\d{3,12}$")
OAUTH_CARD_ACTIVITY_ID_KEY: Final[str] = "oauth_signin_card_activity_id"
OAUTH_CARD_SIGNIN_LINK_KEY: Final[str] = "oauth_signin_link"
PENDING_PROMPT_KEY: Final[str] = "pending_prompt"


def state_get(state: TurnState, key: str) -> Any:
    """Read state value across SDK variants without relying on TurnState.get_value."""
    temp_state = getattr(state, "temp", None)
    if temp_state is not None and hasattr(temp_state, "get_value"):
        return temp_state.get_value(key)

    if hasattr(state, "get_value"):
        return state.get_value(key)

    return None


def state_set(state: TurnState, key: str, value: Any) -> None:
    """Write state value across SDK variants without relying on TurnState.set_value."""
    temp_state = getattr(state, "temp", None)
    if temp_state is not None and hasattr(temp_state, "set_value"):
        temp_state.set_value(key, value)
        return

    if hasattr(state, "set_value"):
        state.set_value(key, value)


def state_delete(state: TurnState, key: str) -> None:
    """Delete state value across SDK variants without relying on TurnState.delete_value."""
    temp_state = getattr(state, "temp", None)
    if temp_state is not None and hasattr(temp_state, "delete_value"):
        temp_state.delete_value(key)
        return

    if hasattr(state, "delete_value"):
        state.delete_value(key)


def _extract_sign_in_link(token_or_sign_in: Any) -> str | None:
    """Extract a sign-in link from the M365 SDK token/sign-in response shape."""
    if token_or_sign_in is None:
        return None

    direct_link = getattr(token_or_sign_in, "sign_in_link", None)
    if direct_link:
        return direct_link

    sign_in_resource = getattr(token_or_sign_in, "sign_in_resource", None)
    if sign_in_resource is None:
        return None

    return getattr(sign_in_resource, "sign_in_link", None)


def _build_oauth_adaptive_card(
    sign_in_link: str,
    description_text: str,
    *,
    is_signin_enabled: bool = True,
    footer_text: str = "If prompted for a verification code, paste it in this chat.",
) -> dict[str, Any]:
    """Build the adaptive card payload used to prompt OAuth sign-in."""
    action: dict[str, Any] = {
        "type": "Action.OpenUrl",
        "title": "Sign in" if is_signin_enabled else "Sign in opened",
        "url": sign_in_link,
    }
    if not is_signin_enabled:
        action["isEnabled"] = False

    return {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [
            {
                "type": "TextBlock",
                "text": "Sign in required",
                "weight": "Bolder",
                "size": "Medium",
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": description_text,
                "wrap": True,
            },
            {
                "type": "TextBlock",
                "text": footer_text,
                "isSubtle": True,
                "wrap": True,
            },
        ],
        "actions": [action],
    }


async def _send_oauth_adaptive_card(
    context: Any,
    state: TurnState,
    sign_in_link: str,
    description_text: str,
) -> None:
    """Send an OAuth prompt using an Adaptive Card."""
    send_result = await context.send_activity(
        Activity(
            type=ActivityTypes.message,
            attachments=[
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": _build_oauth_adaptive_card(sign_in_link, description_text),
                }
            ],
        )
    )

    activity_id = getattr(send_result, "id", None)
    if activity_id:
        state_set(state, OAUTH_CARD_ACTIVITY_ID_KEY, activity_id)
        state_set(state, OAUTH_CARD_SIGNIN_LINK_KEY, sign_in_link)


def extract_magic_code(text: str) -> str | None:
    """Extract a magic code when the incoming text is a numeric OAuth code."""
    candidate = text.strip()
    if MAGIC_CODE_PATTERN.match(candidate):
        return candidate
    return None


async def disable_signin_card(
    context: Any,
    state: TurnState,
    description_text: str,
) -> None:
    """Disable the previously sent OAuth sign-in card action."""
    activity_id = state_get(state, OAUTH_CARD_ACTIVITY_ID_KEY)
    sign_in_link = state_get(state, OAUTH_CARD_SIGNIN_LINK_KEY)
    if not activity_id or not sign_in_link:
        return

    try:
        await context.update_activity(
            Activity(
                type=ActivityTypes.message,
                id=activity_id,
                attachments=[
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": _build_oauth_adaptive_card(
                            sign_in_link=sign_in_link,
                            description_text=description_text,
                            is_signin_enabled=False,
                            footer_text="Waiting for sign-in to complete. Paste your verification code here if prompted.",
                        ),
                    }
                ],
            )
        )
    except (RuntimeError, TypeError, ValueError):
        logger.debug("Unable to update sign-in card to disabled state")


async def get_m365_user_token(
    context: Any,
    state: TurnState,
    settings: M365Settings,
    user_id: str,
    channel_id: str | None,
    magic_code: str | None = None,
) -> str | None:
    """Get an M365 user token, or prompt sign-in with an adaptive card when needed."""
    user_token_client = context.turn_state.get(context.adapter.USER_TOKEN_CLIENT_KEY)
    if not user_token_client or not channel_id:
        return None

    try:
        token_result = await user_token_client.user_token.get_token(
            user_id=user_id,
            connection_name=settings.fabric_oauth_connection_name,
            channel_id=channel_id,
            code=magic_code,
        )
        token_value = getattr(token_result, "token", None)
        if token_value:
            await disable_signin_card(
                context,
                state,
                "Sign-in complete. You can continue chatting.",
            )
            return token_value
    except ClientResponseError as exc:
        # Bot Service returns 404 when no token/connection is available for this channel+user.
        if exc.status == 404:
            logger.info(
                "No M365 user token available",
                extra={
                    "channel_id": channel_id,
                    "user_id": user_id,
                    "connection_name": settings.fabric_oauth_connection_name,
                },
            )
        else:
            logger.warning(
                "M365 user token lookup failed",
                extra={
                    "status": exc.status,
                    "channel_id": channel_id,
                    "user_id": user_id,
                },
            )
    except ValueError:
        logger.info(
            "M365 user token lookup skipped due to invalid context",
            extra={"channel_id": channel_id, "user_id": user_id},
        )

    try:
        conversation_ref = (
            context.activity.get_conversation_reference()
            if hasattr(context.activity, "get_conversation_reference")
            else None
        )
        if not conversation_ref:
            return None

        token_state = TokenExchangeState(
            connection_name=settings.fabric_oauth_connection_name,
            conversation=conversation_ref,
            relates_to=getattr(context.activity, "relates_to", None),
            agent_url=getattr(context.activity, "service_url", None),
            ms_app_id=settings.microsoft_app_id,
        )
        encoded_state = token_state.get_encoded_state()

        get_token_or_sign_in = getattr(
            user_token_client.user_token,
            "_get_token_or_sign_in_resource",
            None,
        )
        if not callable(get_token_or_sign_in):
            return None

        token_or_sign_in = await get_token_or_sign_in(
            user_id,
            settings.fabric_oauth_connection_name,
            channel_id,
            encoded_state,
        )

        token_value = getattr(token_or_sign_in, "token", None)
        if token_value:
            return token_value

        sign_in_link = _extract_sign_in_link(token_or_sign_in)
        if sign_in_link:
            await _send_oauth_adaptive_card(
                context,
                state,
                sign_in_link,
                "To access Fabric Data Agent, sign in with your organizational account.",
            )

    except (AttributeError, ClientResponseError, RuntimeError, TypeError, ValueError):
        logger.warning(
            "Failed to get sign-in resource for M365 OAuth flow",
            extra={"channel_id": channel_id, "user_id": user_id},
        )

    return None
