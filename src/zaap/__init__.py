"""
Local Zaap Auth server for Dofus client autologin.

This module provides a blocking TCP server that implements the minimal ZaapConnect protocol
needed for Dofus client autologin.
"""

from src.zaap.protocol import build_response, parse_message
from src.zaap.server import ZaapAuth

__all__ = ["ZaapAuth", "build_response", "parse_message"]
