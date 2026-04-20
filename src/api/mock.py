"""Mock API client for local testing only.

This module provides a stub auth implementation that returns a fixed token.
DO NOT use in production - replace with real API client.
"""

from dataclasses import dataclass


@dataclass
class AuthResponse:
    """Mock auth response."""
    token: str
    account_id: str | None = None
    error: str | None = None


def login(account: str, password: str) -> AuthResponse:
    """Stub login that returns a fixed token for any valid credentials.

    Args:
        account: Account username (ignored in mock).
        password: Account password (ignored in mock).

    Returns:
        AuthResponse with token, or error if inputs are empty.
    """
    if not account or not account.strip():
        return AuthResponse(token="", error="Account is required")

    if not password or not password.strip():
        return AuthResponse(token="", error="Password is required")

    return AuthResponse(token="test_token", account_id=account)
