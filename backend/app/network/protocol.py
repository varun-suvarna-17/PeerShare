"""Asyncio DatagramProtocol implementation for PeerShare UDP communication."""

import asyncio
import logging
from typing import Callable, Optional, Tuple

logger = logging.getLogger(__name__)


class PeerShareDatagramProtocol(asyncio.DatagramProtocol):
    """Asynchronous DatagramProtocol for sending and receiving PeerShare frames over UDP."""

    def __init__(
        self,
        on_datagram_received: Callable[[bytes, Tuple[str, int]], None],
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        self.on_datagram_received = on_datagram_received
        self.on_error = on_error
        self.transport: Optional[asyncio.DatagramTransport] = None
        self._connected = asyncio.Event()

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Called when UDP socket endpoint is created and bound."""
        self.transport = transport  # type: ignore[assignment]
        self._connected.set()

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        """Called when a raw UDP datagram is received from the network."""
        try:
            self.on_datagram_received(data, addr)
        except Exception as exc:
            logger.error("Error in datagram callback: %s", exc, exc_info=True)
            if self.on_error:
                self.on_error(exc)

    def error_received(self, exc: Exception) -> None:
        """Called when a previous send or receive operation raises an OSError."""
        logger.warning("UDP socket error received: %s", exc)
        if self.on_error:
            self.on_error(exc)

    def connection_lost(self, exc: Optional[Exception]) -> None:
        """Called when the UDP socket connection is closed."""
        self.transport = None

    async def wait_connected(self) -> None:
        """Wait until connection_made has been called."""
        await self._connected.wait()

    @property
    def local_addr(self) -> Optional[Tuple[str, int]]:
        """Return the local bound address (host, port)."""
        if self.transport is not None:
            return self.transport.get_extra_info("sockname")
        return None

