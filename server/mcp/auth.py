import json
import logging
import os

from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

logger = logging.getLogger(__name__)


def _load_tokens_from_env() -> dict:
    """Load token configuration from MCP_TOKENS environment variable."""
    tokens_json = os.getenv("MCP_TOKENS", "{}")
    try:
        return json.loads(tokens_json)
    except json.JSONDecodeError:
        logger.warning("Failed to parse MCP_TOKENS, using empty token set")
        return {}


verifier = StaticTokenVerifier(
    tokens=_load_tokens_from_env(),
    required_scopes=["read:data"],
)
