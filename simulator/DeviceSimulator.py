"""Simulate a Link2Home Device."""
from __future__ import annotations

import asyncio
import logging
import socket
import sys

PORT: int = 35932
LOCAL_CODE: str = "7150"

LOGGER: logging.Logger = logging.getLogger(__package__)

SIMULATED_DEVICES = {
    "999999999999": {
        "device": "d1",
        "01": "FF",
    },
    "888888888888": {
        "device": "d2",
        "01": "FF",
        "02": "FF",
    },
}


class Link2HomeSimulatedDeviceProtocol(asyncio.DatagramProtocol):
    """UDP Server class."""

    def __init__(self):
        """Initialize protocol handler."""
        super().__init__()

    def send_message(self, message: str, host: str) -> None:
        """Send message via UDP."""
        LOGGER.debug("Send_message: %s - %s", host, message)
        sock = socket.socket(
            socket.AF_INET,  # Internet
            socket.SOCK_DGRAM,
        )  # UDP
        sock.sendto(bytes.fromhex(message), (host, PORT))

    def connection_made(self, transport):
        """Process connection ready."""
        LOGGER.debug("connection_made:")
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        """Process incoming message."""

        msg: str = data.hex()

        LOGGER.debug("Received: %s", msg)

        mac: str = msg[4:16]

        if mac not in SIMULATED_DEVICES:
            LOGGER.debug("mac %s not in SIMULATED_DEVICES", mac)
            return

        msg_type: str = msg[2:4]
        lengthPayload: str = msg[16:20]
        payload: str = msg[28 : 29 + int(lengthPayload)]
        commandType: str = payload[4:6]
        channel: str = payload[6:8]

        if channel not in SIMULATED_DEVICES[mac]:
            LOGGER.debug("channel %s not in SIMULATED_DEVICES.channel", channel)
            return

        if msg_type == "00":
            new_msg_data = [
                "a1",
                "06",
                mac,
                "0009",  # Payload Length
                msg[20:24],  # Sequence
                "02",  # Vendor
                SIMULATED_DEVICES[mac]["device"],  # DeviceType
                LOCAL_CODE,
                commandType,
                channel,
                SIMULATED_DEVICES[mac][channel],
            ]

            self.send_message("".join(new_msg_data), addr[0])
            return

        if msg_type == "04":
            requested_channel_state: str = payload[8:10]

            LOGGER.debug(
                "Switch %s event for device %s and channel %s",
                requested_channel_state,
                mac,
                channel,
            )

            SIMULATED_DEVICES[mac][channel] = requested_channel_state

            new_msg_data = [
                "a1",
                "04",
                mac,
                "0011",  # Payload Length
                msg[20:24],  # Sequence
                "02",  # Vendor
                SIMULATED_DEVICES[mac]["device"],  # DeviceType
                LOCAL_CODE,
                "03",
                channel,
                SIMULATED_DEVICES[mac][channel],
            ]

            self.send_message("".join(new_msg_data), addr[0])


def set_logger():
    """Set Logger properties."""

    fmt = "%(asctime)s.%(msecs)03d %(levelname)s (%(threadName)s) [%(name)s] %(message)s"
    LOGGER.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)


if __name__ == "__main__":
    set_logger()
    LOGGER.debug("__Mmain started:")
    loop = asyncio.get_event_loop()
    t = loop.create_datagram_endpoint(
        Link2HomeSimulatedDeviceProtocol, local_addr=("0.0.0.0", PORT)
    )
    LOGGER.debug("__Mmain started: Endpoint created")
    loop.run_until_complete(t)  # Server starts listening
    LOGGER.debug("__Mmain started: run_until_complete finished")
    loop.run_forever()
