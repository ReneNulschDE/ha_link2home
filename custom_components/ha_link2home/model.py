import datetime
from dataclasses import dataclass


@dataclass
class Link2HomeDevice:
    macAddress: str
    companyCode: str
    deviceType: str
    authCode: str
    deviceName: str
    imageName: str
    orderNumber: any
    lastOperation: datetime
    cityId: str
    zoneId: str
    gmtOffset: int
    longtitude: float
    latitude: float
    version: any
    groupId: any
    gColorType: any
    online: bool
    ip: str = ""
    channel1: str = "XX"
    channel2: str = "XX"
    online_local: bool = False
    lastOperation_local: datetime = None
