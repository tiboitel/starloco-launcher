"""Blocking TCP server for ZaapConnect protocol."""

import contextlib
import logging
import socket
import sys
import threading
from collections.abc import Callable

from src.zaap import protocol
from src.zaap.exceptions import BindError, ProtocolError

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5559


class ZaapAuth:
    """Blocking TCP server for ZaapConnect protocol.

    This zaap auth server listens on a local interface and handles the minimal protocol
    needed for Dofus client autologin.

    The auth server does not generate auth tokens — it receives them from the caller
    via set_token() before starting the client.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        token_provider: Callable[[str, str], str] | None = None,
    ) -> None:
        """Initialize the bridge.

        Args:
            host: The interface to bind to. Must be 127.0.0.1 for security.
            port: The port to listen on.
            token_provider: Optional callback(session_id, game_id) -> token.
                       If not provided, tokens must be set via set_token() before client connect.
        """
        if host != "127.0.0.1":
            msg = f"Invalid host: {host}. Bridge must bind to 127.0.0.1 only."
            raise BindError(msg)

        self.host = host
        self.port = port
        self.token_provider = token_provider
        self._server_socket: socket.socket | None = None
        self._running = False
        self._sessions: dict[str, str] = {}
        self._lock = threading.Lock()
        self._username: str | None = None

    def set_token(self, session_id: str, token: str) -> None:
        """Store a token for a session.

        Args:
            session_id: The session ID to associate with the token.
            token: The auth token to return when the client requests it.
        """
        with self._lock:
            self._username = session_id
            self._sessions[session_id] = token

    def start(self) -> None:
        """Start the bridge server.

        Raises:
            BindError: If the port is unavailable or the socket fails to bind.
        """
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(5)
            self._running = True
            logger.info("ZaapBridge listening on %s:%d", self.host, self.port)
        except OSError as e:
            msg = f"Failed to bind to {self.host}:{self.port}: {e}"
            raise BindError(msg) from e

    def stop(self) -> None:
        """Stop the bridge server."""
        self._running = False
        if self._server_socket:
            with contextlib.suppress(OSError):
                self._server_socket.close()
        with self._lock:
            self._sessions.clear()
        logger.info("ZaapBridge stopped")

    def accept_loop(self) -> None:
        """Accept connections in a blocking loop.

        This method blocks until stop() is called. Each connection
        is handled in a separate thread.
        """
        while self._running:
            try:
                client_socket, address = self._server_socket.accept()
                logger.debug("Accepted connection from %s", address)
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,),
                    daemon=True,
                )
                thread.start()
            except OSError:
                if self._running:
                    logger.warning("Error accepting connection", exc_info=True)
                break

    def _handle_client(self, client_socket: socket.socket) -> None:
        """Handle a single client connection.

        Args:
            client_socket: The connected client socket.
        """
        address = client_socket.getpeername()
        logger.debug("Handling client from %s", address)

        try:
            client_socket.settimeout(10.0)

            buffer = b""
            while self._running:
                try:
                    chunk = client_socket.recv(4096)
                except TimeoutError:
                    logger.debug("Client %s timed out", address)
                    break
                except OSError as e:
                    logger.debug("Client %s error: %s", address, e)
                    break

                if not chunk:
                    break

                buffer += chunk

                while b"\x00" in buffer:
                    message, buffer = buffer.split(b"\x00", 1)
                    if message:
                        self._process_message(client_socket, message, address)

        except Exception as e:
            logger.exception("Client %s error: %s", address, e)
        finally:
            client_socket.close()
            logger.debug("Client %s disconnected", address)

    def _process_message(
        self,
        client_socket: socket.socket,
        message: bytes,
        address: tuple,
    ) -> None:
        """Process a single protocol message.

        Args:
            client_socket: The client socket for sending responses.
            message: The raw message bytes.
            address: The client address (for logging).
        """
        logger.info(">>> RAW CLIENT DATA: %r", message)
        try:
            parsed = protocol.parse_message(message)
        except ProtocolError as e:
            logger.warning("Protocol error from %s: %s", address, e)
            response = protocol.build_response("error")
            logger.info("<<< BRIDGE RESPONSE: %r", response)
            client_socket.sendall(response)
            return

        if parsed is None:
            logger.debug("Unknown message from %s: %r", address, message)
            response = protocol.build_response("ignored")
            logger.info("<<< BRIDGE RESPONSE: %r", response)
            client_socket.sendall(response)
            return

        try:
            if isinstance(parsed, protocol.ConnectMessage):
                response = self._handle_connect(client_socket, parsed, address)
            elif isinstance(parsed, protocol.AuthGameTokenMessage):
                response = self._handle_auth(client_socket, parsed, address)
            else:
                response = protocol.build_response("ignored")
            logger.info("<<< BRIDGE RESPONSE: %r", response)
        except Exception as e:
            logger.exception("Error processing message from %s: %s", address, e)
            response = protocol.build_response("error")
            logger.info("<<< BRIDGE RESPONSE (ERROR): %r", response)
            client_socket.sendall(response)

    def _handle_connect(
        self,
        client_socket: socket.socket,
        message: protocol.ConnectMessage,
        address: tuple,
    ) -> bytes:
        """Handle a connect message.

        Args:
            client_socket: The client socket for sending responses.
            message: The parsed connect message.
            address: The client address (for logging).

        Returns:
            The response bytes sent to the client.
        """
        game_type = message.game_type
        zaap_hash = message.zaap_hash
        logger.info("CONNECT from %s, game_type: %s, zaap_hash: %s", address, game_type, zaap_hash)

        with self._lock:
            username = self._username
            if not username:
                username = "unknown"
            self._sessions[username] = self._sessions.get(username)
            logger.info("Session created for user: %s", username)

        response = protocol.build_connect_response(username)
        client_socket.sendall(response)
        logger.info("Sent CONNECT response: %r", response)
        return response

    def _handle_auth(
        self,
        client_socket: socket.socket,
        message: protocol.AuthGameTokenMessage,
        address: tuple,
    ) -> bytes:
        """Handle an auth_getGameToken message.

        Args:
            client_socket: The client socket for sending responses.
            message: The parsed auth message.
            address: The client address (for logging).

        Returns:
            The response bytes sent to the client.
        """
        session_id = message.session_id
        game_id = message.game_id

        logger.info(
            "AUTH_GETGAME_TOKEN from %s, session: %s, game_id: %s", address, session_id, game_id
        )

        # Get or generate token for this session
        with self._lock:
            token = self._sessions.get(session_id)

            # If no token stored, try to get from provider or generate placeholder
            if not token:
                if self.token_provider:
                    token = self.token_provider(session_id, game_id)
                    self._sessions[session_id] = token
                    logger.info("Token generated via provider for session: %s", session_id)
                else:
                    # Placeholder token for testing
                    token = "test_token_12345"
                    self._sessions[session_id] = token
                    logger.info("Using placeholder token for session: %s", session_id)

        response = protocol.build_auth_response(token)
        logger.info(
            "Sent AUTH_GETGAME_TOKEN response (token): %s",
            token[:20] + "..." if len(token) > 20 else token,
        )
        client_socket.sendall(response)
        return response


def start_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    token_provider: Callable[[str, str], str] | None = None,
) -> ZaapAuth:
    """Factory to create and start a zaap auth server.

    Args:
        host: The interface to bind to.
        port: The port to listen on.
        token_provider: Optional callback(session_id, game_id) -> token.

    Returns:
        Running ZaapAuth instance.
    """
    zaap = ZaapAuth(host=host, port=port, token_provider=token_provider)
    zaap.start()
    return zaap
