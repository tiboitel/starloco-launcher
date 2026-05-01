"""ZaapConnect protocol message parsing and building."""

from dataclasses import dataclass

from src.zaap.exceptions import ProtocolError


@dataclass
class ConnectMessage:
    """Parsed connect message."""
    account_id: str
    game_type: str
    zaap_hash: str


@dataclass
class AuthGameTokenMessage:
    """Parsed auth_getGameToken message."""
    session_id: str
    game_id: str


@dataclass
class Response:
    """Protocol response."""
    command: str
    data: str | None = None


def parse_message(data: bytes) -> ConnectMessage | AuthGameTokenMessage | None:
    """Parse a raw protocol message.

    Args:
        data: Raw bytes from the client, expected to be null-terminated.

    Returns:
        Parsed message object (ConnectMessage or AuthGameTokenMessage), or None if malformed.

    Raises:
        ProtocolError: If the message format is invalid.
    """
    try:
        text = data.decode("utf-8").replace("\x00", "").strip()
    except UnicodeDecodeError as e:
        msg = f"Invalid UTF-8 in message: {e}"
        raise ProtocolError(msg) from e

    if not text:
        return None

    parts = text.split()
    command = parts[0] if parts else ""

    if command == "connect":
        if len(parts) < 2:
            msg = "connect requires at least 2 parts: connect <game_type> <version> [-1] [-1]"
            raise ProtocolError(msg)
        game_type = parts[1] if len(parts) > 1 else ""
        zaap_hash = parts[4] if len(parts) > 4 and parts[4] != "-1" else ""
        return ConnectMessage(account_id="", game_type=game_type, zaap_hash=zaap_hash)

    if command == "auth_getGameToken":
        if len(parts) < 3:
            msg = "auth_getGameToken requires at least 3 parts: auth_getGameToken <session_id> <game_id>"
            raise ProtocolError(msg)
        return AuthGameTokenMessage(session_id=parts[1], game_id=parts[2])

    return None


def build_response(command: str, data: str | None = None) -> bytes:
    """Build a protocol response.

    Args:
        command: The command name (e.g., "connect", "auth_getGameToken", "error").
        data: Optional data to include in the response.

    Returns:
        Encoded response as bytes with newline terminator.
    """
    if command == "error":
        response = "error"
    elif data:
        response = f"{command} {data}"
    else:
        response = command

    return f"{response}\x00".encode()


def build_connect_response(account_id: str) -> bytes:
    """Build a connect OK response.

    Args:
        account_id: The account ID to return to the client.

    Returns:
        Encoded response.
    """
    return build_response("connect", account_id)


def build_auth_response(token: str) -> bytes:
    """Build an auth_getGameToken response.

    Args:
        token: The auth token to return to the client.

    Returns:
        Encoded response.
    """
    return build_response("auth_getGameToken", token)
