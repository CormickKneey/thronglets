"""Authentication configuration for Thronglets ServiceBus.

Supports JWT token verification using Supabase JWKS.
Clients should obtain access_token from Supabase and pass it as Bearer token.
"""

import os
from fastmcp.server.auth import AuthProvider

# Auth enabled flag
AUTH_ENABLED = os.getenv("THRONGLETS_AUTH_ENABLED", "false").lower() == "true"

# Supabase configuration
SUPABASE_PROJECT_URL = os.getenv("THRONGLETS_SUPABASE_PROJECT_URL", "")
SUPABASE_ANON_KEY = os.getenv("THRONGLETS_SUPABASE_ANON_KEY", "")


def get_auth_provider() -> AuthProvider | None:
    """Get the JWT authentication provider.

    Returns:
        JWTVerifier if auth is enabled and configured, None otherwise.
    """
    if not AUTH_ENABLED:
        return None

    if not SUPABASE_PROJECT_URL:
        raise ValueError(
            "THRONGLETS_SUPABASE_PROJECT_URL is required when auth is enabled"
        )

    from fastmcp.server.auth.providers.jwt import JWTVerifier

    # Supabase JWKS endpoint
    jwks_uri = f"{SUPABASE_PROJECT_URL}/auth/v1/.well-known/jwks.json"

    # Note: Supabase uses ES256 algorithm for JWT signing
    return JWTVerifier(
        jwks_uri=jwks_uri,
        algorithm="ES256",  # Supabase uses ES256
        issuer=None,  # Skip issuer validation
        audience=None,  # Supabase tokens don't have audience claim
    )


def get_auth_config() -> dict:
    """Get auth configuration for frontend.

    Returns:
        Dict with auth status and Supabase config for token generation.
    """
    return {
        "enabled": AUTH_ENABLED,
        "supabase_url": SUPABASE_PROJECT_URL if AUTH_ENABLED else None,
        "supabase_anon_key": SUPABASE_ANON_KEY if AUTH_ENABLED else None,
    }
