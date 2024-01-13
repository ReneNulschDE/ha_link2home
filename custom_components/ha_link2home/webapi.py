"""The Link2Home WebAPI."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import traceback
from typing import Any

from aiohttp import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from .const import DISABLE_SSL_CERT_CHECK, LOGIN_BASE_URI, SYSTEM_PROXY
from .model import Link2HomeDevice

LOGGER = logging.getLogger(__name__)


class Link2HomeWebApi:
    """Define the WebAPI object."""

    def __init__(
        self,
        session: ClientSession,
        username: str,
        password: str,
    ) -> None:
        """Initialize."""
        self._session: ClientSession = session
        self._username: str = username
        self._password: str = password
        self.initialized: bool = False
        self.token: str = ""

    def _create_sign(self, data):
        # DER / PKCS#8
        privateKeyHash = "308204BD020100300D06092A864886F70D0101010500048204A7308204A30201000282010100829C8319985E2B93D5660F597D2C8E62E0A41B00F64CC418E90DD91BADD786AABCBF3622054F72711BD6C9CB56B8EBE29BD466221C3677F38C1F56000B6A6C3F105A52AC747EAE59BECCB0032FA100CCBE1DC701F7D14556730D61D5121D62D4972A6D9EA7FFB7AB3C500E6C8E6BAE98380E2240A7D197FFA57DA42F59E0735FBA8526FFFA12363456E6CE3633DE792FDB8DFDFC09693C1B14862BC6281815AFB6234EE56D3B033939FCA66DEADD13ED349C0FB1F29D9341C15934E1055231F5D658AEAF5F15CFA5CDAC294C9B899A1F302B7A7C2D6A8A846D14ADE727140CE3C33C7DCED1D037F477B7331BF6409A42CF7AEF1407E09CFAD3BB07477B3AE7F30203010001028201000B055DE29902C9368E39306E62AB91D0321866D6EBF18A5277C7DD5C028D3F25C50B756BE57AD0B34EA00F23034C534B29CF00573C7E341CEEE3EE03CEF2C9F38053BECA228255FFE8A3A8EE7BE46006E6BBE880F802469186DFC8338C75C25321F6488DACAB5D3A2BBAAD9CE75F9AB9E970F7DEF0CA34C33399A872FE687C13A68CA926C16D7DF34B337131E9FC96482920E97316564EDC262A6492F188FB52B476573B857A0F2EE3E2CC84C98E4B2E60A9FCCA7CBA4CFD9038F1728C721E3F651CCED9F1868F41B520BF42E7E617554A05753C6A82CC07F23FF0ACC78014C3DE1B7D49B76FDA221016F7E2804E60FF4DC0CF8DA05715D83EE7CD739FEA048102818100D6D67CDBE9FF73EB49B8F81C74C30DCC95F3642A3D2398DE27352E8E3CE79BFED4673B2D0E7D48313BEA176E67BC14CC6AF3A37FACB48A0DC41891AAE2E96BCC116A70A3F2CEEE8B90B5E7CC7658DBFA0BA869EC878EA1BBD0DDD246A0F8EDFCC528E6210672C912D0159E7E2244E80CF1FD92E98B9F672F9B449C6EA6B39C13028181009BA2D3D4E0027E1B135925F07DB7E09121134E5CAFC8975DA7AAABAE54BDA10DF0C71BDFC761F289EEFED1ADD9175563161DF07ACA458AD4626CE8ACA63881358EAA789DE05B3644E7056C0378906B66E893061AD0F2A90CD540A1145737B7ABE1DE1B1853C393458B6FF4A713EB573692364942198674B0CC81537303DB40A1028180261779A3F4655AC4491A06C3E4E000BE598802268B1898AE2AFD7EF7B14CCF97EB493270D6B4D7EC02D78AB804A4907B7E2B1CBE327D004D588B92A85DFB4D25ADA0D5BFFBF93CCA7A2A06A3760863587E60AA074A31BBF375211F7B6E6734AB30BA03B3AF5502D9D7133E3AD710A8A442F3D6EC99D8F58EB754FEF78F8F21090281803B10C8A3F97FF8ABFDE3CF6A3DCC1306012F7A85E29096218D0850AF90A986FDEB6B2541004243F1E52A0019A25220ADC22F0A9D0F36E54145395FF46600FBC87FA462B247FB55D54077E64E4AEB445781DC8A6C92F0050841C68D5B52DE6A6E690209F66993C7C894EAA046E8606070ED7C7CC1013EEDFA4B22A9B0F4BDB90102818100BA638FDCB02F73D5883AE5F3AB958218844CA306E926E0ED550280A57EE7E5560B7FAFDC51609C757FF03C3BF9C13A34FB440FB862FF14F33ECCA3880D5E609CA40E30F61A255A5CB9DD87EB72FB6B83B4FC8517F2542E119922F4694C10C906442F3EED696D01D7FDFA1346E9D8E28859CC75D58E17B7F7730500A3066F9707"
        private_key = serialization.load_der_private_key(
            bytes.fromhex(privateKeyHash), password=None, backend=default_backend()
        )

        data_url = self.dict_to_querystring(data)
        data_bytes = data_url.encode("utf-8")

        signature = base64.b64encode(
            private_key.sign(data_bytes, padding.PKCS1v15(), hashes.SHA1())  # type: ignore
        )

        return signature

    async def login(self) -> bool:
        """Get the login token from link2home cloud."""
        LOGGER.debug("login: Start")

        data = {
            "appName": "Link2Home",
            "appType": "2",
            "appVersion": "1.1.1",
            "password": hashlib.md5(self._password.encode()).hexdigest().upper(),
            "phoneSysVersion": "iOS 17.3",
            "phoneType": "iPhone13,3",
            "username": self._username,
        }

        data |= {"sign": {self._create_sign(data)}}

        LOGGER.debug("login: %s", data)

        login_response = await self._request("post", "/api/service/user/login", data=data)

        if login_response.get("code") and login_response.get("code") == 600:
            LOGGER.debug("login: %s", login_response)
            self.token = login_response.get("data").get("token")
            return True

        if login_response.get("code"):
            return False

        LOGGER.warning("login: other error -  %s", login_response)
        return False

    async def get_device_list(self) -> dict[str, Link2HomeDevice]:
        """Get device list from link2home cloud."""
        data = {"token": self.token}
        data |= {"sign": self._create_sign(data).decode("utf-8")}

        response = await self._request("get", "/api/app/device/list", params=data)

        if response.get("code") and response.get("code") == 600:
            LOGGER.debug("get_device_dist: %s", response)

            devices = []

            for result in response.get("data"):
                dev: Link2HomeDevice = Link2HomeDevice(
                    auth_code=result.get("authCode"),
                    city_id=result.get("cityId"),
                    company_code=result.get("companyCode"),
                    device_name=result.get("deviceName"),
                    device_type=result.get("deviceType"),
                    gcolor_type=result.get("gColorType"),
                    gmt_offset=result.get("gmtOffset"),
                    group_id=result.get("groupId"),
                    image_name=result.get("imageName"),
                    last_operation=datetime.fromtimestamp(
                        result.get("lastOperation") / 1000,
                        tz=timezone(timedelta(minutes=result.get("gmtOffset"))),
                    ),
                    latitude=result.get("latitude"),
                    longtitude=result.get("longtitude"),
                    mac_address=result.get("macAddress").lower(),
                    online=result.get("online"),
                    order_number=result.get("orderNumber"),
                    version=result.get("version"),
                    zone_id=result.get("zoneId"),
                )
                devices.append(dev)

            return {result.mac_address: result for result in devices}

        LOGGER.warning("get_device_dist failed: %s", response)
        return {}

    async def _request(
        self,
        method: str,
        endpoint: str,
        ignore_errors: bool = False,
        **kwargs,
    ) -> Any:
        """Make a request against the API."""

        url = f"{LOGIN_BASE_URI}{endpoint}"
        kwargs.setdefault("headers", {})
        kwargs.setdefault("proxy", SYSTEM_PROXY)
        kwargs.setdefault("ssl", DISABLE_SSL_CERT_CHECK)

        kwargs["headers"] = {
            "Accept": "*/*",
            "User-Agent": "Link2Home/1.1.1 (iPhone; iOS 16.1.1; Scale/3.00)",
            "Accept-Language": "de-DE;q=1.0, en-DE;q=0.9",
        }

        use_running_session = self._session and not self._session.closed

        if use_running_session:
            session = self._session
        else:
            session = ClientSession(timeout=ClientTimeout(total=30))

        try:
            # async with session.request(method, url, proxy=proxy, ssl=False, **kwargs) as resp:
            if "url" in kwargs:
                async with session.request(method, **kwargs) as resp:
                    # resp.raise_for_status()
                    return await resp.json(content_type=None)
            else:
                async with session.request(method, url, **kwargs) as resp:
                    resp.raise_for_status()
                    return await resp.json(content_type=None)

        except ClientError as err:
            LOGGER.debug(traceback.format_exc())
            if not ignore_errors:
                raise ClientError from err
            return None
        except Exception:
            LOGGER.debug(traceback.format_exc())
        finally:
            if not use_running_session:
                await session.close()

    def dict_to_querystring(self, params):
        """Convert a dict in querystring without encoding."""

        query_parts = []
        for key, value in params.items():
            query_parts.append(f"{key}={value}")
        return "&".join(query_parts)
