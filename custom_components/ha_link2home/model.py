"""Data models for Link2Home."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class Link2HomeDevice:
    """Dataclass for Link2HomeDevices."""

    mac_address: str
    company_code: str
    device_type: str
    auth_code: str
    device_name: str
    image_name: str
    order_number: str
    last_operation: datetime
    city_id: str
    zone_id: str
    gmt_offset: int
    longtitude: float
    latitude: float
    version: str
    group_id: str
    gcolor_type: str
    online: bool
    ip: str = ""
    channel1: str = "XX"
    channel2: str = "XX"
    online_local: bool = False
    last_operation_local: datetime = datetime.fromtimestamp(0, UTC)
