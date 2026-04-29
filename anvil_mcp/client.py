"""AnvilClient — async HTTP wrapper around the Anvil FastAPI backend."""

from __future__ import annotations

from typing import Any

import httpx


class AnvilClient:
    """Thin async httpx wrapper that talks to the FastAPI backend at port 8000."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000") -> None:
        self._base = base_url.rstrip("/")

    async def get(self, path: str, **kwargs: Any) -> Any:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self._base}{path}", **kwargs)
            r.raise_for_status()
            return r.json()

    async def post(self, path: str, json: Any = None, **kwargs: Any) -> Any:
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self._base}{path}", json=json, **kwargs)
            r.raise_for_status()
            return r.json()

    async def delete(self, path: str, **kwargs: Any) -> Any:
        async with httpx.AsyncClient() as client:
            r = await client.delete(f"{self._base}{path}", **kwargs)
            r.raise_for_status()
            return None


_client = AnvilClient()


def get_client() -> AnvilClient:
    return _client
