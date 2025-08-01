"""The Link2Home Data Coordinator."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectorError
from awesomeversion import AwesomeVersion

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HAVERSION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, GENERAL_AUTH_CODE
from .model import Link2HomeDevice
from .udpapi import Link2HomeUDPServer
from .webapi import Link2HomeWebApi

UPDATE_INTERVAL = timedelta(minutes=60)
BROADCAST_IP = "255.255.255.255"
LOGGER = logging.getLogger(__name__)

# Version threshold for config_entry setting in options flow
# See: https://github.com/home-assistant/core/pull/127980
HA_DATACOORDINATOR_CONTEXTVAR_VERSION_THRESHOLD = "2025.07.99"


class Link2HomeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Link2Home data web and udp API."""

    initialized: bool = False
    udp_data: dict[str, Any] = {}

    def __init__(
        self,
        hass: HomeAssistant,
        session: ClientSession,
        username: str,
        password: str,
        local_ip: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize."""

        self.hass: HomeAssistant = hass
        self.username: str = username
        self.password: str = password
        self.session: ClientSession = session
        self.local_ip: str = local_ip

        if AwesomeVersion(HAVERSION) < HA_DATACOORDINATOR_CONTEXTVAR_VERSION_THRESHOLD:
            super().__init__(hass, LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        else:
            super().__init__(
                hass,
                LOGGER,
                name=DOMAIN,
                config_entry=config_entry,
                update_interval=UPDATE_INTERVAL,
            )

        self.webapi: Link2HomeWebApi = Link2HomeWebApi(
            self.hass, self.session, self.username, self.password
        )
        self.udpsession: Link2HomeUDPServer = Link2HomeUDPServer(
            self.handle_udp_events, self.local_ip
        )

    async def _async_update_data(self) -> dict[str, Link2HomeDevice]:
        """Update data via library."""
        LOGGER.debug("_async_update_data: started")

        try:
            if not self.udpsession.started:
                await self.udpsession.start_server()

            # async with asyncio.timeout(10):
            if not self.initialized:
                devices = await self.webapi.get_device_list()
                LOGGER.info(
                    "Link2Home Cloud delivered %s device(s). Starting local discovery",
                    len(devices),
                )
                LOGGER.debug(devices)

                for result in devices:
                    await asyncio.sleep(0.5)

                    for _x in range(0, 3):
                        # 02-query, 01-channel
                        self.udpsession.send_status_request(result, "0201", BROADCAST_IP)
                        self.udpsession.send_status_request(result, "0202", BROADCAST_IP)
                        await asyncio.sleep(0.2)

                self.udpsession.initialized = True
                self.initialized = True

            else:
                devices = self.data

            self.udp_data.clear()

            while not self.udpsession.queue.empty():
                queue_item: str = self.udpsession.queue.get_nowait()
                item = queue_item.split("_")
                self.process_udp_message(item[0], item[1], item[2])

            for switch, switch_state in self.udp_data.items():
                mac = switch.split("_")[0]
                channel = switch.split("_")[1]
                ip = switch.split("_")[2]

                if mac in devices:
                    if channel == "01":
                        devices[mac].channel1 = switch_state
                    if channel == "02":
                        devices[mac].channel2 = switch_state
                    devices[mac].online_local = True
                    devices[mac].ip = ip
                    devices[mac].last_operation_local = datetime.now(UTC)
                else:
                    LOGGER.debug("_async_update_data: mac not in devices")

            return devices

        except (ClientConnectorError,) as error:
            raise UpdateFailed(error) from error

    def set_state(self, device: Link2HomeDevice, state: bool, channel: str = "01"):
        """Prepare udp package and send."""
        data = [
            "a104",
            device.mac_address.lower(),
            "0009",
            format(self.udpsession.sequence, "04x"),
            device.company_code,
            device.device_type,
            GENERAL_AUTH_CODE,
            "01",
            channel,
            "FF" if state else "00",
        ]

        msg = "".join(data)

        LOGGER.debug("set_state: IP: %s, data: %s", device.ip, msg)
        self.udpsession.send(msg, device.ip if device.ip != "" else BROADCAST_IP)

    def process_udp_message(self, data: str, ip, port):
        """Process UDP message and extract data."""

        LOGGER.debug("process_udp_message start: %s - %s - %s", ip, port, data)

        msg_type = data[2:4]

        if msg_type not in ("04", "06"):
            return

        mac = data[4:16]

        lengthPayload = data[16:20]
        commandType = data[32:34]
        payload = data[34 : 34 + int(lengthPayload)]

        if commandType in ("01", "02", "03"):
            channel = payload[0:2]
            key = f"{mac}_{channel}_{ip}"
            if len(payload) < 4:
                state = False
            else:
                state = payload[2:4] == "ff"

            self.udp_data[key] = "ff" if state else "00"
            LOGGER.debug("process_udp_message - end: %s", self.udp_data)

    @callback
    def handle_udp_events(self):
        """Alart HA incoming udp packages."""
        self.hass.loop.create_task(self.async_refresh())
