"""The Link2Home UDP API."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable, Callable
import logging
import queue as q
from socket import AF_INET, IPPROTO_UDP, SO_BROADCAST, SOCK_DGRAM, SOL_SOCKET, socket
from typing import cast

from homeassistant.core import callback

UDP_PORT = 35932  # Link2Home Port
LOGGER = logging.getLogger(__name__)


class Link2HomeUDPServer(asyncio.DatagramProtocol):
    """The Link2Home UDP Server."""

    started = False
    stopped = False
    transport: asyncio.DatagramTransport | None = None
    remote_addr: tuple[str, int] | None = None
    sequence: int = 1
    initialized: bool = False
    handle_finished: Callable[[], None]

    def __init__(self, handle_event, local_ip: str) -> None:
        """Initialize UDP receiver."""
        self.handle_event: Callable[[], None] = handle_event
        self.queue: q.Queue = q.Queue()
        self.local_ip = local_ip

    async def start_server(self) -> int:
        """Start accepting connections."""

        def accept_connection() -> Link2HomeUDPServer:
            """Accept connection."""
            if self.started:
                raise RuntimeError("Can only start once")
            if self.stopped:
                raise RuntimeError("No longer accepting connections")

            self.started = True
            return self

        sock = socket(AF_INET, SOCK_DGRAM)
        sock.setblocking(False)

        sock.bind((self.local_ip, UDP_PORT))

        await asyncio.get_running_loop().create_datagram_endpoint(accept_connection, sock=sock)

        return cast(int, sock.getsockname()[1])

    @callback
    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Store transport for later use."""
        self.transport = cast(asyncio.DatagramTransport, transport)

    @callback
    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Handle incoming UDP packet."""
        if not self.started or self.stopped:
            return
        if self.remote_addr is None:
            self.remote_addr = addr

        LOGGER.debug("datagram_received: %s_%s_%s", data.hex(), addr[0], addr[1])
        self.queue.put(f"{data.hex()}_{addr[0]}_{addr[1]}")
        if self.initialized:
            self.handle_event()

    def error_received(self, exc: Exception) -> None:
        """Handle when a send or receive operation raises an OSError.

        (Other than BlockingIOError or InterruptedError.)
        """
        LOGGER.error("UDP server error received: %s", exc)
        self.handle_finished()

    @callback
    def stop(self) -> None:
        """Stop the receiver."""
        self.queue.put_nowait(b"")
        self.started = False
        self.stopped = True

    def close(self) -> None:
        """Close the receiver."""
        self.started = False
        self.stopped = True
        if self.transport is not None:
            self.transport.close()

    def send_status_request(self, mac_address: str, payload: str, ip: str = "255.255.255.255"):
        """Send status request as broadcast."""
        data = (
            "a100"
            + mac_address.lower()
            + "0007"
            + format(self.sequence, "04x")
            + "00000000"
            + payload
        )
        self.sequence += 1

        LOGGER.debug("send_status_request packet: %s to %s", data, ip)
        with socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP) as sock:
            sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            sock.setblocking(False)
            sock.sendto(bytes.fromhex(data), (ip, UDP_PORT))

    def send(self, data: str, ip: str):
        """Send package."""
        self.sequence += 1

        LOGGER.info("send packet: %s to %s", data, ip)
        with socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP) as sock:
            sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            sock.setblocking(False)
            sock.sendto(bytes.fromhex(data), (ip, UDP_PORT))

    async def _iterate_packets(self) -> AsyncIterable[bytes]:
        """Iterate over incoming packets."""
        if not self.started or self.stopped:
            raise RuntimeError("Not running")

        while data := await self.queue.get():
            yield data
