"""HTTP client for real auth API."""

import hashlib
from dataclasses import dataclass

import requests

from src import config


def sha512_md5(password: str) -> str:
    """Hash password as SHA512(MD5(password))."""
    md5 = hashlib.md5(password.encode()).hexdigest()
    return hashlib.sha512(md5.encode()).hexdigest()


@dataclass
class AuthResponse:
    token: str
    account_id: str | None = None
    error: str | None = None


def login(account: str, password: str) -> AuthResponse:
    """Call /generateAuthToken endpoint."""
    endpoint = config.get("api_endpoint", "http://127.0.0.1:8000/generateAuthToken")

    try:
        response = requests.post(
            endpoint,
            json={"account_id": account, "password_hash": sha512_md5(password)},
            timeout=10,
        )
    except requests.RequestException as e:
        return AuthResponse(token="", error=f"Connection failed: {e}")

    if response.status_code == 401:
        return AuthResponse(token="", error="Invalid credentials")

    if response.status_code != 200:
        return AuthResponse(token="", error=f"Server error: {response.status_code}")

    data = response.json()
    return AuthResponse(token=data.get("zaap_token", ""), account_id=account)
