"""The Link2Home integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import async_timeout
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientConnectorError
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, GENERAL_AUTH_CODE
from .model import Link2HomeDevice
from .udpapi import Link2HomeUDPServer
from .webapi import Link2HomeWebApi

UPDATE_INTERVAL = timedelta(minutes=0.5)
BROADCAST_IP = "255.255.255.255"
LOGGER = logging.getLogger(__name__)


class Link2HomeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Link2Home data web and udp API."""

    initialized: bool = False
    udp_data: {str, any} = {}

    def __init__(
        self,
        hass: HomeAssistant,
        session: ClientSession,
        username: str,
        password: str,
    ) -> None:
        """Initialize."""

        self.hass: HomeAssistant = hass
        self.webapi: Link2HomeWebApi = Link2HomeWebApi(session, username, password)
        self.udpsession: Link2HomeUDPServer = Link2HomeUDPServer(self.handle_udp_events)

        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)

    async def async_init(self):
        try:
            async with async_timeout.timeout(10):
                login_result: bool = await self.webapi.login()
        except ConfigEntryAuthFailed as auth_error:
            raise auth_error
        except (ClientConnectorError,) as error:
            raise UpdateFailed(error) from error

    async def _async_update_data(self) -> dict[str, Link2HomeDevice]:
        """Update data via library."""
        LOGGER.debug("_async_update_data: started")

        try:
            if not self.udpsession.started:
                await self.udpsession.start_server()

            # async with async_timeout.timeout(10):
            if not self.initialized:
                devices = await self.webapi.get_device_list()
                LOGGER.info("Link2Home Cloud delivered %s devices", len(devices))
                LOGGER.debug(devices)

                for result in devices:
                    LOGGER.debug(result)
                    await asyncio.sleep(0.5)

                    for x in range(0, 3):
                        # 02-query, 01-channel
                        self.udpsession.send_status_request(
                            result, "0201", BROADCAST_IP
                        )
                        self.udpsession.send_status_request(
                            result, "0202", BROADCAST_IP
                        )
                        await asyncio.sleep(0.2)

                self.udpsession.initialized = True
                self.initialized = True

            else:
                devices = self.data

            LOGGER.debug(devices)

            while not self.udpsession.queue.empty():
                queue_item: str = self.udpsession.queue.get_nowait()
                item = queue_item.split("_")
                self.process_udp_message(item[0], item[1], item[2])

            for switch in self.udp_data.keys():
                mac = switch.split("_")[0]
                channel = switch.split("_")[1]
                ip = switch.split("_")[2]

                LOGGER.debug("_async_update_data: switch - %s", switch)
                LOGGER.debug("_async_update_data: mac - %s", mac)
                LOGGER.debug("_async_update_data: channel - %s", channel)

                if mac in devices:
                    LOGGER.debug("_async_update_data: mac in devices")
                    if channel == "01":
                        devices[mac].channel1 = self.udp_data[switch]
                    if channel == "02":
                        devices[mac].channel2 = self.udp_data[switch]
                    devices[mac].online_local = True
                    devices[mac].ip = ip
                    devices[mac].lastOperation_local = datetime.now(timezone.utc)
                else:
                    LOGGER.debug("_async_update_data: mac not in devices")

            LOGGER.debug("_async_update_data: udp_data - %s", self.udp_data)
            LOGGER.debug("_async_update_data: devices - %s", devices)
            return devices

        except (ClientConnectorError,) as error:
            raise UpdateFailed(error) from error

    def set_state(self, device: Link2HomeDevice, state: bool, channel: str = "01"):
        data = [
            "a104",
            device.macAddress.lower(),
            "0009",
            format(self.udpsession.sequence, "04x"),
            device.companyCode,
            device.deviceType,
            GENERAL_AUTH_CODE,
            "01",
            channel,
            "FF" if state else "00",
        ]

        msg = "".join(data)

        LOGGER.debug("set_state: IP: %s, data: %s", device.ip, msg)
        self.udpsession.send(msg, device.ip if device.ip != "" else BROADCAST_IP)

    def process_udp_message(self, data: str, ip, port):
        LOGGER.debug("process_udp_message: started - %s", data)

        msg_type = data[2:4]

        if msg_type not in ("04", "06"):
            LOGGER.debug(
                "process_udp_message: unknown/unwanted msg_type - %s", msg_type
            )
            return

        mac = data[4:16]

        lengthPayload = data[16:20]
        commandType = data[32:34]
        payload = data[34 : 34 + int(lengthPayload)]

        if commandType in ("02", "03"):
            channel = payload[0:2]
            key = f"{mac}_{channel}_{ip}"
            if len(payload) < 4:
                state = False
            else:
                state = True if payload[2:4] == "ff" else False

            self.udp_data[key] = "ff" if state else "00"
            LOGGER.debug("process_udp_message: %s", self.udp_data)

    @callback
    def handle_udp_events(self):
        LOGGER.debug("handle_udp_events: start async_refresh")
        self.hass.loop.create_task(self.async_refresh())
