"""
API client module.

For local testing, use src.api.mock.login().
Replace with real API client for production.
"""

from src.api.mock import AuthResponse, login

__all__ = ["AuthResponse", "login"]
