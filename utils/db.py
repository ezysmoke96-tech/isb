import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "bot_data.db")


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS verified_users (
                discord_id       TEXT PRIMARY KEY,
                roblox_id        TEXT NOT NULL,
                roblox_username  TEXT NOT NULL,
                verified_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS pending_verifications (
                discord_id       TEXT PRIMARY KEY,
                roblox_username  TEXT NOT NULL,
                code             TEXT NOT NULL,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS game_bans (
                roblox_username  TEXT PRIMARY KEY,
                banned_by        TEXT,
                reason           TEXT,
                banned_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS academy_pass_dms (
                discord_id  TEXT PRIMARY KEY,
                message_id  TEXT NOT NULL,
                sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS timed_bans (
                discord_id  TEXT NOT NULL,
                guild_id    TEXT NOT NULL,
                unban_at    INTEGER NOT NULL,
                PRIMARY KEY (discord_id, guild_id)
            );
            CREATE TABLE IF NOT EXISTS giveaways (
                message_id   TEXT PRIMARY KEY,
                channel_id   TEXT NOT NULL,
                guild_id     TEXT NOT NULL,
                prize        TEXT NOT NULL,
                num_winners  INTEGER NOT NULL DEFAULT 1,
                end_at       INTEGER NOT NULL,
                ended        INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS giveaway_entries (
                message_id  TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                PRIMARY KEY (message_id, user_id)
            );
        """)
        await db.commit()


async def get_config(key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM config WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def set_config(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value)
        )
        await db.commit()


async def get_all_config() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key, value FROM config") as cur:
            return {r[0]: r[1] for r in await cur.fetchall()}


async def save_pending_verification(discord_id: str, roblox_username: str, code: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO pending_verifications (discord_id, roblox_username, code) VALUES (?, ?, ?)",
            (discord_id, roblox_username, code),
        )
        await db.commit()


async def get_pending_verification(discord_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT roblox_username, code FROM pending_verifications WHERE discord_id = ?",
            (discord_id,),
        ) as cur:
            row = await cur.fetchone()
            return {"roblox_username": row[0], "code": row[1]} if row else None


async def delete_pending_verification(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM pending_verifications WHERE discord_id = ?", (discord_id,)
        )
        await db.commit()


async def save_verified_user(discord_id: str, roblox_id: str, roblox_username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO verified_users (discord_id, roblox_id, roblox_username) VALUES (?, ?, ?)",
            (discord_id, roblox_id, roblox_username),
        )
        await db.commit()


async def get_verified_user(discord_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT roblox_id, roblox_username FROM verified_users WHERE discord_id = ?",
            (discord_id,),
        ) as cur:
            row = await cur.fetchone()
            return {"roblox_id": row[0], "roblox_username": row[1]} if row else None


async def get_verified_user_by_roblox(roblox_username: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT discord_id, roblox_id FROM verified_users WHERE LOWER(roblox_username) = LOWER(?)",
            (roblox_username,),
        ) as cur:
            row = await cur.fetchone()
            return {"discord_id": row[0], "roblox_id": row[1]} if row else None


async def delete_verified_user(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM verified_users WHERE discord_id = ?", (discord_id,)
        )
        await db.commit()


async def is_game_banned(roblox_username: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM game_bans WHERE LOWER(roblox_username) = LOWER(?)",
            (roblox_username,),
        ) as cur:
            return (await cur.fetchone()) is not None


async def add_game_ban(roblox_username: str, banned_by: str, reason: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO game_bans (roblox_username, banned_by, reason) VALUES (?, ?, ?)",
            (roblox_username, banned_by, reason),
        )
        await db.commit()


async def remove_game_ban(roblox_username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM game_bans WHERE LOWER(roblox_username) = LOWER(?)",
            (roblox_username,),
        )
        await db.commit()


async def save_academy_pass_dm(discord_id: str, message_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO academy_pass_dms (discord_id, message_id) VALUES (?, ?)",
            (discord_id, message_id),
        )
        await db.commit()


async def get_academy_pass_dm(discord_id: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT message_id FROM academy_pass_dms WHERE discord_id = ?", (discord_id,)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def delete_academy_pass_dm(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM academy_pass_dms WHERE discord_id = ?", (discord_id,)
        )
        await db.commit()


# ── Timed Bans ────────────────────────────────────────────────────────────────

async def save_timed_ban(discord_id: str, guild_id: str, unban_at: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO timed_bans (discord_id, guild_id, unban_at) VALUES (?, ?, ?)",
            (discord_id, guild_id, unban_at),
        )
        await db.commit()


async def get_expired_timed_bans(guild_id: str, now: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT discord_id FROM timed_bans WHERE guild_id = ? AND unban_at <= ?",
            (guild_id, now),
        ) as cur:
            return [row[0] for row in await cur.fetchall()]


async def delete_timed_ban(discord_id: str, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM timed_bans WHERE discord_id = ? AND guild_id = ?",
            (discord_id, guild_id),
        )
        await db.commit()


# ── Giveaways ─────────────────────────────────────────────────────────────────

async def save_giveaway(message_id: str, channel_id: str, guild_id: str, prize: str, num_winners: int, end_at: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO giveaways (message_id, channel_id, guild_id, prize, num_winners, end_at, ended) VALUES (?, ?, ?, ?, ?, ?, 0)",
            (message_id, channel_id, guild_id, prize, num_winners, end_at),
        )
        await db.commit()


async def get_giveaway(message_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT message_id, channel_id, guild_id, prize, num_winners, end_at, ended FROM giveaways WHERE message_id = ?",
            (message_id,),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {"message_id": row[0], "channel_id": row[1], "guild_id": row[2], "prize": row[3], "num_winners": row[4], "end_at": row[5], "ended": row[6]}


async def get_latest_giveaway_in_channel(channel_id: str, active_only: bool = True) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        query = "SELECT message_id, channel_id, guild_id, prize, num_winners, end_at, ended FROM giveaways WHERE channel_id = ?"
        params: list = [channel_id]
        if active_only:
            query += " AND ended = 0"
        query += " ORDER BY end_at DESC LIMIT 1"
        async with db.execute(query, params) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {"message_id": row[0], "channel_id": row[1], "guild_id": row[2], "prize": row[3], "num_winners": row[4], "end_at": row[5], "ended": row[6]}


async def add_giveaway_entry(message_id: str, user_id: str) -> bool:
    """Returns True if successfully entered, False if already entered."""
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO giveaway_entries (message_id, user_id) VALUES (?, ?)",
                (message_id, user_id),
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_giveaway_entries(message_id: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM giveaway_entries WHERE message_id = ?", (message_id,)
        ) as cur:
            return [row[0] for row in await cur.fetchall()]


async def mark_giveaway_ended(message_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (message_id,))
        await db.commit()


async def get_active_giveaways_ending_before(timestamp: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT message_id, channel_id, guild_id, prize, num_winners, end_at FROM giveaways WHERE ended = 0 AND end_at <= ?",
            (timestamp,),
        ) as cur:
            rows = await cur.fetchall()
            return [{"message_id": r[0], "channel_id": r[1], "guild_id": r[2], "prize": r[3], "num_winners": r[4], "end_at": r[5]} for r in rows]
