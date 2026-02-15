from __future__ import annotations

import os
from typing import Any, Dict

import httpx


def _base_url() -> str:
    return os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


def _headers() -> Dict[str, str]:
    token = os.getenv("API_BOT_TOKEN", "").strip()
    if not token:
        return {}
    return {"X-API-Key": token}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=_base_url(), headers=_headers(), timeout=15.0)


async def get_active_run(telegram_id: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/runs/active", params={"telegram_id": telegram_id})
        response.raise_for_status()
        return response.json()


async def run_action(
    telegram_id: int,
    username: str | None,
    action: str,
) -> Dict[str, Any]:
    payload = {
        "telegram_id": telegram_id,
        "username": username,
        "action": action,
    }
    async with _client() as client:
        response = await client.post("/v1/runs/action", json=payload)
        response.raise_for_status()
        return response.json()


async def start_state(telegram_id: int, username: str | None) -> Dict[str, Any]:
    payload = {"telegram_id": telegram_id, "username": username}
    async with _client() as client:
        response = await client.post("/v1/start", json=payload)
        response.raise_for_status()
        return response.json()


async def get_profile(telegram_id: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get(
            "/v1/profile",
            params={"telegram_id": telegram_id},
        )
        response.raise_for_status()
        return response.json()


async def get_stats(telegram_id: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/stats", params={"telegram_id": telegram_id})
        response.raise_for_status()
        return response.json()


async def get_leaderboard(page: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/leaderboard", params={"page": page})
        response.raise_for_status()
        return response.json()


async def get_rules(section: str) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/rules", params={"section": section})
        response.raise_for_status()
        return response.json()


async def get_heroes_menu(telegram_id: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get(
            "/v1/heroes/menu",
            params={"telegram_id": telegram_id},
        )
        response.raise_for_status()
        return response.json()


async def get_hero_detail(telegram_id: int, hero_id: str) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get(
            "/v1/heroes/detail",
            params={"telegram_id": telegram_id, "hero_id": hero_id},
        )
        response.raise_for_status()
        return response.json()


async def unlock_hero(telegram_id: int, hero_id: str) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.post(
            "/v1/heroes/unlock",
            params={"telegram_id": telegram_id, "hero_id": hero_id},
        )
        response.raise_for_status()
        return response.json()


async def stars_menu() -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/stars/menu")
        response.raise_for_status()
        return response.json()


async def stars_validate(payload: str, telegram_id: int, currency: str, total_amount: int) -> Dict[str, Any]:
    data = {
        "payload": payload,
        "telegram_id": telegram_id,
        "currency": currency,
        "total_amount": total_amount,
    }
    async with _client() as client:
        response = await client.post("/v1/stars/validate", json=data)
        response.raise_for_status()
        return response.json()


async def stars_success(
    payload: str,
    telegram_id: int,
    username: str | None,
    telegram_charge_id: str,
    provider_charge_id: str | None,
    currency: str,
    total_amount: int,
) -> Dict[str, Any]:
    data = {
        "payload": payload,
        "telegram_id": telegram_id,
        "username": username,
        "telegram_charge_id": telegram_charge_id,
        "provider_charge_id": provider_charge_id,
        "currency": currency,
        "total_amount": total_amount,
    }
    async with _client() as client:
        response = await client.post("/v1/stars/success", json=data)
        response.raise_for_status()
        return response.json()


async def get_story_state(telegram_id: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/story", params={"telegram_id": telegram_id})
        response.raise_for_status()
        return response.json()


async def get_story_chapter(chapter: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/story/chapter", params={"chapter": chapter})
        response.raise_for_status()
        return response.json()


async def get_story_photo(chapter: int) -> bytes:
    async with _client() as client:
        response = await client.get("/v1/story/photo", params={"chapter": chapter})
        response.raise_for_status()
        return response.content


async def get_hero_photo(hero_id: str) -> bytes:
    async with _client() as client:
        response = await client.get("/v1/assets/hero", params={"hero_id": hero_id})
        response.raise_for_status()
        return response.content


async def get_broadcast_photo(key: str) -> bytes:
    async with _client() as client:
        response = await client.get("/v1/assets/broadcast", params={"key": key})
        response.raise_for_status()
        return response.content


async def get_share(telegram_id: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/share", params={"telegram_id": telegram_id})
        response.raise_for_status()
        return response.json()


async def get_broadcast_targets(broadcast_key: str) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/broadcast/targets", params={"broadcast_key": broadcast_key})
        response.raise_for_status()
        return response.json()


async def get_all_broadcast_targets() -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/broadcast/targets/all")
        response.raise_for_status()
        return response.json()


async def mark_broadcast_sent(user_id: int, broadcast_key: str) -> Dict[str, Any]:
    payload = {"user_id": user_id, "broadcast_key": broadcast_key}
    async with _client() as client:
        response = await client.post("/v1/broadcast/sent", json=payload)
        response.raise_for_status()
        return response.json()


async def get_season_summary(season_number: int, recalc: bool) -> Dict[str, Any]:
    payload = {"season_number": season_number, "recalc": recalc}
    async with _client() as client:
        response = await client.post("/v1/broadcast/season-summary", json=payload)
        response.raise_for_status()
        return response.json()


async def get_admin_panel(telegram_id: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/admin/panel", params={"telegram_id": telegram_id})
        response.raise_for_status()
        return response.json()


async def get_admin_season_prompt(telegram_id: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.get("/v1/admin/season/prompt", params={"telegram_id": telegram_id})
        response.raise_for_status()
        return response.json()


async def admin_season_badges(telegram_id: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.post("/v1/admin/season/badges", params={"telegram_id": telegram_id})
        response.raise_for_status()
        return response.json()


async def admin_season_advance(telegram_id: int) -> Dict[str, Any]:
    async with _client() as client:
        response = await client.post("/v1/admin/season/advance", params={"telegram_id": telegram_id})
        response.raise_for_status()
        return response.json()
