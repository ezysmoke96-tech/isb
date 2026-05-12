import os
import aiohttp
from datetime import datetime, timezone

MAIN_GROUP_ID = 36051087
SECURITY_BUREAU_GROUP_ID = 34100596


def _cookie_jar() -> dict:
    """Returns cookie header dict if ROBLOX_COOKIE is configured, else empty."""
    cookie = os.environ.get("ROBLOX_COOKIE", "").strip()
    if cookie:
        return {".ROBLOSECURITY": cookie}
    return {}


def _headers() -> dict:
    cookie = os.environ.get("ROBLOX_COOKIE", "").strip()
    if cookie:
        return {"Cookie": f".ROBLOSECURITY={cookie}"}
    return {}


async def get_user_by_username(username: str) -> dict | None:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [username], "excludeBannedUsers": False},
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            users = data.get("data", [])
            return users[0] if users else None


async def get_user_info(user_id: int) -> dict | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://users.roblox.com/v1/users/{user_id}") as resp:
            if resp.status != 200:
                return None
            return await resp.json()


async def get_user_groups(user_id: int) -> list:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://groups.roblox.com/v2/users/{user_id}/groups/roles"
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            return data.get("data", [])


async def get_group_allies(group_id: int) -> list[int]:
    allies = []
    async with aiohttp.ClientSession() as session:
        for start in range(0, 300, 100):
            async with session.get(
                f"https://groups.roblox.com/v1/groups/{group_id}/relationships/allies"
                f"?maxRows=100&startRowIndex={start}"
            ) as resp:
                if resp.status != 200:
                    break
                data = await resp.json()
                groups = data.get("relatedGroups", [])
                if not groups:
                    break
                allies.extend(g["id"] for g in groups)
    return allies


async def get_badge_info(user_id: int) -> tuple[int, bool, str | None]:
    """Returns (badge_count, is_farming_suspicious, top_game_name).
    Requires ROBLOX_COOKIE env var — Roblox's badge API mandates authentication.
    Returns (-1, False, None) if no cookie is configured."""
    cookie = os.environ.get("ROBLOX_COOKIE", "").strip()
    if not cookie:
        return -1, False, None

    total = 0
    cursor = None
    game_counts: dict[int, int] = {}
    game_names: dict[int, str] = {}

    headers = {"Cookie": f".ROBLOSECURITY={cookie}"}

    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            url = (
                f"https://badges.roblox.com/v1/users/{user_id}/badges"
                f"?limit=100&sortOrder=Asc"
            )
            if cursor:
                url += f"&cursor={cursor}"

            async with session.get(url) as resp:
                if resp.status != 200:
                    break
                data = await resp.json()

                if data.get("errors"):
                    break

                page = data.get("data", [])
                total += len(page)

                for badge in page:
                    awarder = badge.get("awarder", {})
                    gid = awarder.get("id")
                    gname = awarder.get("name", "Unknown")
                    if gid:
                        game_counts[gid] = game_counts.get(gid, 0) + 1
                        game_names[gid] = gname

                cursor = data.get("nextPageCursor")
                if not cursor:
                    break

    is_suspicious = False
    top_game_name = None

    if total > 30 and game_counts:
        top_gid = max(game_counts, key=game_counts.get)
        top_count = game_counts[top_gid]
        top_game_name = game_names.get(top_gid)
        if top_count / total > 0.55:
            is_suspicious = True

    return total, is_suspicious, top_game_name


def account_age_days(created_at: str) -> int:
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - created).days


async def check_profile_for_code(user_id: int, code: str) -> bool:
    info = await get_user_info(user_id)
    if not info:
        return False
    return code in (info.get("description") or "")
