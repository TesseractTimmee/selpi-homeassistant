"""Client for the selpi add-on's HA API (web/api.py in selpi)."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp


class SelpiError(Exception):
    """Could not talk to the add-on, or it couldn't talk to the SP PRO."""


class SelpiAuthError(SelpiError):
    """The token was refused."""


class SelpiClient:
    def __init__(self, session: aiohttp.ClientSession, host: str, port: int, token: str) -> None:
        host = f"[{host}]" if ":" in host and not host.startswith("[") else host
        self._base = f"http://{host}:{port}/api/v1"
        self._session = session
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, path: str, timeout: float = 45, **params: str) -> dict[str, Any]:
        try:
            async with self._session.request(
                method, self._base + path, headers=self._headers, params=params or None,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 401:
                    raise SelpiAuthError("token refused by the selpi add-on")
                data = await resp.json(content_type=None)
                if resp.status != 200:
                    raise SelpiError((data or {}).get("error") or f"HTTP {resp.status}")
                return data
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise SelpiError(f"selpi add-on not reachable: {err}") from err

    async def info(self) -> dict[str, Any]:
        return await self._request("GET", "/info")

    async def fields(self) -> list[dict[str, Any]]:
        return (await self._request("GET", "/fields"))["fields"]

    async def values(self, keys: list[str]) -> dict[str, Any]:
        return await self._request("GET", "/values", keys=",".join(keys))

    async def diagnostics(self) -> dict[str, Any]:
        return await self._request("GET", "/diagnostics", timeout=10)

    async def backup(self) -> dict[str, Any]:
        return await self._request("POST", "/backup", timeout=10)

    async def control(self, name: str, state: str = "", confirm: str | None = None) -> dict[str, Any]:
        """State-aware control through the app: generator on/off, output on/idle (idle needs confirm), equalise.
        The app presses a front panel button only when the unit's state needs it."""
        params = {"name": name}
        if state:
            params["state"] = state
        if confirm:
            params["confirm"] = confirm
        return await self._request("POST", "/control", timeout=90, **params)

    async def press(self, button: str, confirm: str | None = None) -> dict[str, Any]:
        """Press a front panel button on the SP PRO through the app (generator, silence; on needs confirm)."""
        params = {"name": button}
        if confirm:
            params["confirm"] = confirm
        return await self._request("POST", "/button", timeout=60, **params)
