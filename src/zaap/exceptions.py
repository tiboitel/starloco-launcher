"""Custom exceptions for the zaap module."""


class ZaapError(Exception):
    """Base exception for zaap-related errors."""


class ProtocolError(ZaapError):
    """Raised when the protocol message is invalid or malformed."""



class SessionError(ZaapError):
    """Raised when a session-related error occurs (invalid session, missing token)."""


class BindError(ZaapError):
    """Raised when the zaap server fails to bind to the configured port."""

