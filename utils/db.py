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
                origin_guild_id  TEXT,
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
            CREATE TABLE IF NOT EXISTS autoroles (
                guild_id  TEXT NOT NULL,
                role_id   TEXT NOT NULL,
                PRIMARY KEY (guild_id, role_id)
            );

            -- ── Intelligence ───────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS intel_reports (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id         TEXT NOT NULL,
                title            TEXT NOT NULL,
                content          TEXT NOT NULL,
                classification   TEXT NOT NULL DEFAULT 'CLASSIFIED',
                created_by       TEXT NOT NULL,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                archived         INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS investigations (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id     TEXT NOT NULL,
                title        TEXT NOT NULL,
                description  TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'OPEN',
                opened_by    TEXT NOT NULL,
                opened_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at    TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS suspects (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id   TEXT NOT NULL,
                user_id    TEXT NOT NULL,
                reason     TEXT NOT NULL,
                added_by   TEXT NOT NULL,
                added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS missions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id     TEXT NOT NULL,
                name         TEXT NOT NULL,
                briefing     TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'ACTIVE',
                created_by   TEXT NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS informants (
                guild_id       TEXT NOT NULL,
                user_id        TEXT NOT NULL,
                registered_by  TEXT NOT NULL,
                registered_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS surveillance (
                guild_id    TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                reason      TEXT NOT NULL,
                added_by    TEXT NOT NULL,
                added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS clearances (
                guild_id  TEXT NOT NULL,
                user_id   TEXT NOT NULL,
                level     INTEGER NOT NULL DEFAULT 1,
                set_by    TEXT NOT NULL,
                set_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS traitor_flags (
                guild_id  TEXT NOT NULL,
                user_id   TEXT NOT NULL,
                reason    TEXT NOT NULL,
                flagged_by TEXT NOT NULL,
                flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS priority_targets (
                guild_id   TEXT NOT NULL,
                user_id    TEXT NOT NULL,
                reason     TEXT NOT NULL,
                added_by   TEXT NOT NULL,
                added_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS threat_levels (
                guild_id   TEXT NOT NULL,
                user_id    TEXT NOT NULL,
                level      TEXT NOT NULL,
                set_by     TEXT NOT NULL,
                set_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS interrogations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id   TEXT NOT NULL,
                user_id    TEXT NOT NULL,
                notes      TEXT NOT NULL,
                opened_by  TEXT NOT NULL,
                opened_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- ── Cases & Moderation ─────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS cases (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id     TEXT NOT NULL,
                user_id      TEXT NOT NULL,
                action       TEXT NOT NULL,
                reason       TEXT NOT NULL,
                actioned_by  TEXT NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active       INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    TEXT NOT NULL,
                reporter_id TEXT NOT NULL,
                target_id   TEXT NOT NULL,
                reason      TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'OPEN',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS evidence (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id      INTEGER NOT NULL,
                guild_id     TEXT NOT NULL,
                content      TEXT NOT NULL,
                submitted_by TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS watchlist (
                guild_id  TEXT NOT NULL,
                user_id   TEXT NOT NULL,
                reason    TEXT NOT NULL,
                added_by  TEXT NOT NULL,
                added_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS warnings (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id  TEXT NOT NULL,
                user_id   TEXT NOT NULL,
                reason    TEXT NOT NULL,
                warned_by TEXT NOT NULL,
                warned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS strikes (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id  TEXT NOT NULL,
                user_id   TEXT NOT NULL,
                reason    TEXT NOT NULL,
                struck_by TEXT NOT NULL,
                struck_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS blacklist (
                guild_id  TEXT NOT NULL,
                user_id   TEXT NOT NULL,
                reason    TEXT NOT NULL,
                added_by  TEXT NOT NULL,
                added_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS suspensions (
                guild_id      TEXT NOT NULL,
                user_id       TEXT NOT NULL,
                reason        TEXT NOT NULL,
                suspended_by  TEXT NOT NULL,
                suspended_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS wanted (
                guild_id  TEXT NOT NULL,
                user_id   TEXT NOT NULL,
                reason    TEXT NOT NULL,
                added_by  TEXT NOT NULL,
                added_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );

            -- ── Personnel ──────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS loas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                reason      TEXT NOT NULL,
                granted_by  TEXT NOT NULL,
                start_at    INTEGER NOT NULL,
                end_at      INTEGER NOT NULL,
                active      INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS medals (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id   TEXT NOT NULL,
                user_id    TEXT NOT NULL,
                medal_name TEXT NOT NULL,
                awarded_by TEXT NOT NULL,
                awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id   TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                user_id    TEXT NOT NULL,
                status     TEXT NOT NULL DEFAULT 'OPEN',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()


# ── Config ─────────────────────────────────────────────────────────────────────

async def get_config(key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM config WHERE key = ?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def set_config(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
        await db.commit()


async def get_all_config() -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key, value FROM config") as cur:
            return {r[0]: r[1] for r in await cur.fetchall()}


# ── Verifications ──────────────────────────────────────────────────────────────

async def save_pending_verification(discord_id: str, roblox_username: str, code: str, origin_guild_id: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO pending_verifications (discord_id, roblox_username, code, origin_guild_id) VALUES (?, ?, ?, ?)",
            (discord_id, roblox_username, code, origin_guild_id),
        )
        await db.commit()


async def get_pending_verification(discord_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT roblox_username, code, origin_guild_id FROM pending_verifications WHERE discord_id = ?",
            (discord_id,),
        ) as cur:
            row = await cur.fetchone()
            return {"roblox_username": row[0], "code": row[1], "origin_guild_id": row[2]} if row else None


async def delete_pending_verification(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM pending_verifications WHERE discord_id = ?", (discord_id,))
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
        async with db.execute("SELECT roblox_id, roblox_username FROM verified_users WHERE discord_id = ?", (discord_id,)) as cur:
            row = await cur.fetchone()
            return {"roblox_id": row[0], "roblox_username": row[1]} if row else None


async def get_verified_user_by_roblox(roblox_username: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT discord_id, roblox_id FROM verified_users WHERE LOWER(roblox_username) = LOWER(?)", (roblox_username,)
        ) as cur:
            row = await cur.fetchone()
            return {"discord_id": row[0], "roblox_id": row[1]} if row else None


async def delete_verified_user(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM verified_users WHERE discord_id = ?", (discord_id,))
        await db.commit()


# ── Game bans ──────────────────────────────────────────────────────────────────

async def is_game_banned(roblox_username: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM game_bans WHERE LOWER(roblox_username) = LOWER(?)", (roblox_username,)) as cur:
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
        await db.execute("DELETE FROM game_bans WHERE LOWER(roblox_username) = LOWER(?)", (roblox_username,))
        await db.commit()


# ── Academy ────────────────────────────────────────────────────────────────────

async def save_academy_pass_dm(discord_id: str, message_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO academy_pass_dms (discord_id, message_id) VALUES (?, ?)", (discord_id, message_id))
        await db.commit()


async def get_academy_pass_dm(discord_id: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT message_id FROM academy_pass_dms WHERE discord_id = ?", (discord_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def delete_academy_pass_dm(discord_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM academy_pass_dms WHERE discord_id = ?", (discord_id,))
        await db.commit()


# ── Timed bans ─────────────────────────────────────────────────────────────────

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
            "SELECT discord_id FROM timed_bans WHERE guild_id = ? AND unban_at <= ?", (guild_id, now)
        ) as cur:
            return [row[0] for row in await cur.fetchall()]


async def delete_timed_ban(discord_id: str, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM timed_bans WHERE discord_id = ? AND guild_id = ?", (discord_id, guild_id))
        await db.commit()


# ── Giveaways ──────────────────────────────────────────────────────────────────

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
            "SELECT message_id, channel_id, guild_id, prize, num_winners, end_at, ended FROM giveaways WHERE message_id = ?", (message_id,)
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
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT INTO giveaway_entries (message_id, user_id) VALUES (?, ?)", (message_id, user_id))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def get_giveaway_entries(message_id: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM giveaway_entries WHERE message_id = ?", (message_id,)) as cur:
            return [row[0] for row in await cur.fetchall()]


async def mark_giveaway_ended(message_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE giveaways SET ended = 1 WHERE message_id = ?", (message_id,))
        await db.commit()


async def get_active_giveaways_ending_before(timestamp: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT message_id, channel_id, guild_id, prize, num_winners, end_at FROM giveaways WHERE ended = 0 AND end_at <= ?", (timestamp,)
        ) as cur:
            rows = await cur.fetchall()
            return [{"message_id": r[0], "channel_id": r[1], "guild_id": r[2], "prize": r[3], "num_winners": r[4], "end_at": r[5]} for r in rows]


# ── Autoroles ──────────────────────────────────────────────────────────────────

async def get_autoroles(guild_id: str) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT role_id FROM autoroles WHERE guild_id = ?", (guild_id,)) as cur:
            return [row[0] for row in await cur.fetchall()]


async def add_autorole(guild_id: str, role_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO autoroles (guild_id, role_id) VALUES (?, ?)", (guild_id, role_id))
        await db.commit()


async def remove_autorole(guild_id: str, role_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM autoroles WHERE guild_id = ? AND role_id = ?", (guild_id, role_id))
        await db.commit()


async def clear_autoroles(guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM autoroles WHERE guild_id = ?", (guild_id,))
        await db.commit()


# ── Intelligence ───────────────────────────────────────────────────────────────

async def save_intel(guild_id: str, title: str, content: str, classification: str, created_by: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO intel_reports (guild_id, title, content, classification, created_by) VALUES (?, ?, ?, ?, ?)",
            (guild_id, title, content, classification, created_by),
        )
        await db.commit()
        return cur.lastrowid


async def get_intel(report_id: int, guild_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, title, content, classification, created_by, created_at, archived FROM intel_reports WHERE id = ? AND guild_id = ?",
            (report_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "title": row[1], "content": row[2], "classification": row[3], "created_by": row[4], "created_at": row[5], "archived": row[6]}


async def delete_intel(report_id: int, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM intel_reports WHERE id = ? AND guild_id = ?", (report_id, guild_id))
        await db.commit()


async def archive_intel(report_id: int, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE intel_reports SET archived = 1 WHERE id = ? AND guild_id = ?", (report_id, guild_id))
        await db.commit()


async def list_intel(guild_id: str, archived: bool = False) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, title, classification, created_by, created_at FROM intel_reports WHERE guild_id = ? AND archived = ? ORDER BY id DESC LIMIT 20",
            (guild_id, 1 if archived else 0),
        ) as cur:
            return [{"id": r[0], "title": r[1], "classification": r[2], "created_by": r[3], "created_at": r[4]} for r in await cur.fetchall()]


# ── Investigations ─────────────────────────────────────────────────────────────

async def open_investigation(guild_id: str, title: str, description: str, opened_by: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO investigations (guild_id, title, description, opened_by) VALUES (?, ?, ?, ?)",
            (guild_id, title, description, opened_by),
        )
        await db.commit()
        return cur.lastrowid


async def get_investigation(inv_id: int, guild_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, title, description, status, opened_by, opened_at, closed_at FROM investigations WHERE id = ? AND guild_id = ?",
            (inv_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "title": row[1], "description": row[2], "status": row[3], "opened_by": row[4], "opened_at": row[5], "closed_at": row[6]}


async def close_investigation(inv_id: int, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE investigations SET status = 'CLOSED', closed_at = CURRENT_TIMESTAMP WHERE id = ? AND guild_id = ?",
            (inv_id, guild_id),
        )
        await db.commit()


async def list_investigations(guild_id: str, status: str = "OPEN") -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, title, opened_by, opened_at FROM investigations WHERE guild_id = ? AND status = ? ORDER BY id DESC LIMIT 15",
            (guild_id, status),
        ) as cur:
            return [{"id": r[0], "title": r[1], "opened_by": r[2], "opened_at": r[3]} for r in await cur.fetchall()]


# ── Suspects ───────────────────────────────────────────────────────────────────

async def add_suspect(guild_id: str, user_id: str, reason: str, added_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO suspects (guild_id, user_id, reason, added_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, added_by),
        )
        await db.commit()


async def remove_suspect(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM suspects WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


async def get_suspect(guild_id: str, user_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT reason, added_by, added_at FROM suspects WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return {"reason": row[0], "added_by": row[1], "added_at": row[2]} if row else None


# ── Missions ───────────────────────────────────────────────────────────────────

async def create_mission(guild_id: str, name: str, briefing: str, created_by: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO missions (guild_id, name, briefing, created_by) VALUES (?, ?, ?, ?)",
            (guild_id, name, briefing, created_by),
        )
        await db.commit()
        return cur.lastrowid


async def get_mission(mission_id: int, guild_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, name, briefing, status, created_by, created_at FROM missions WHERE id = ? AND guild_id = ?",
            (mission_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "name": row[1], "briefing": row[2], "status": row[3], "created_by": row[4], "created_at": row[5]}


async def close_mission(mission_id: int, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE missions SET status = 'CLOSED' WHERE id = ? AND guild_id = ?", (mission_id, guild_id))
        await db.commit()


# ── Informants ─────────────────────────────────────────────────────────────────

async def add_informant(guild_id: str, user_id: str, registered_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO informants (guild_id, user_id, registered_by) VALUES (?, ?, ?)",
            (guild_id, user_id, registered_by),
        )
        await db.commit()


async def remove_informant(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM informants WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


async def is_informant(guild_id: str, user_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM informants WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cur:
            return (await cur.fetchone()) is not None


# ── Surveillance ───────────────────────────────────────────────────────────────

async def set_surveillance(guild_id: str, user_id: str, reason: str, added_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO surveillance (guild_id, user_id, reason, added_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, added_by),
        )
        await db.commit()


async def end_surveillance(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM surveillance WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


async def get_surveillance(guild_id: str, user_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT reason, added_by, added_at FROM surveillance WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return {"reason": row[0], "added_by": row[1], "added_at": row[2]} if row else None


# ── Clearances ─────────────────────────────────────────────────────────────────

async def set_clearance(guild_id: str, user_id: str, level: int, set_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO clearances (guild_id, user_id, level, set_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, level, set_by),
        )
        await db.commit()


async def get_clearance(guild_id: str, user_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT level FROM clearances WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


# ── Traitor flags ──────────────────────────────────────────────────────────────

async def add_traitor_flag(guild_id: str, user_id: str, reason: str, flagged_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO traitor_flags (guild_id, user_id, reason, flagged_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, flagged_by),
        )
        await db.commit()


async def remove_traitor_flag(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM traitor_flags WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


async def get_traitor_flag(guild_id: str, user_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT reason, flagged_by, flagged_at FROM traitor_flags WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return {"reason": row[0], "flagged_by": row[1], "flagged_at": row[2]} if row else None


# ── Priority targets ───────────────────────────────────────────────────────────

async def add_priority_target(guild_id: str, user_id: str, reason: str, added_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO priority_targets (guild_id, user_id, reason, added_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, added_by),
        )
        await db.commit()


async def remove_priority_target(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM priority_targets WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


async def get_priority_target(guild_id: str, user_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT reason, added_by, added_at FROM priority_targets WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return {"reason": row[0], "added_by": row[1], "added_at": row[2]} if row else None


# ── Threat levels ──────────────────────────────────────────────────────────────

async def set_threat_level(guild_id: str, user_id: str, level: str, set_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO threat_levels (guild_id, user_id, level, set_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, level, set_by),
        )
        await db.commit()


async def get_threat_level(guild_id: str, user_id: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT level FROM threat_levels WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


# ── Interrogations ─────────────────────────────────────────────────────────────

async def open_interrogation(guild_id: str, user_id: str, notes: str, opened_by: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO interrogations (guild_id, user_id, notes, opened_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, notes, opened_by),
        )
        await db.commit()
        return cur.lastrowid


# ── Cases ──────────────────────────────────────────────────────────────────────

async def log_case(guild_id: str, user_id: str, action: str, reason: str, actioned_by: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO cases (guild_id, user_id, action, reason, actioned_by) VALUES (?, ?, ?, ?, ?)",
            (guild_id, user_id, action, reason, actioned_by),
        )
        await db.commit()
        return cur.lastrowid


async def get_case(case_id: int, guild_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, user_id, action, reason, actioned_by, created_at, active FROM cases WHERE id = ? AND guild_id = ?",
            (case_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "user_id": row[1], "action": row[2], "reason": row[3], "actioned_by": row[4], "created_at": row[5], "active": row[6]}


async def search_cases(guild_id: str, user_id: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, action, reason, actioned_by, created_at FROM cases WHERE guild_id = ? AND user_id = ? ORDER BY id DESC LIMIT 20",
            (guild_id, user_id),
        ) as cur:
            return [{"id": r[0], "action": r[1], "reason": r[2], "actioned_by": r[3], "created_at": r[4]} for r in await cur.fetchall()]


async def terminate_case(case_id: int, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE cases SET active = 0 WHERE id = ? AND guild_id = ?", (case_id, guild_id))
        await db.commit()


async def list_recent_cases(guild_id: str, limit: int = 10) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, user_id, action, reason, actioned_by, created_at FROM cases WHERE guild_id = ? AND active = 1 ORDER BY id DESC LIMIT ?",
            (guild_id, limit),
        ) as cur:
            return [{"id": r[0], "user_id": r[1], "action": r[2], "reason": r[3], "actioned_by": r[4], "created_at": r[5]} for r in await cur.fetchall()]


# ── Reports ────────────────────────────────────────────────────────────────────

async def file_report(guild_id: str, reporter_id: str, target_id: str, reason: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO reports (guild_id, reporter_id, target_id, reason) VALUES (?, ?, ?, ?)",
            (guild_id, reporter_id, target_id, reason),
        )
        await db.commit()
        return cur.lastrowid


async def get_report(report_id: int, guild_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, reporter_id, target_id, reason, status, created_at FROM reports WHERE id = ? AND guild_id = ?",
            (report_id, guild_id),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "reporter_id": row[1], "target_id": row[2], "reason": row[3], "status": row[4], "created_at": row[5]}


async def list_reports(guild_id: str, status: str = "OPEN") -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, reporter_id, target_id, reason, created_at FROM reports WHERE guild_id = ? AND status = ? ORDER BY id DESC LIMIT 15",
            (guild_id, status),
        ) as cur:
            return [{"id": r[0], "reporter_id": r[1], "target_id": r[2], "reason": r[3], "created_at": r[4]} for r in await cur.fetchall()]


async def close_report(report_id: int, guild_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE reports SET status = 'CLOSED' WHERE id = ? AND guild_id = ?", (report_id, guild_id))
        await db.commit()


# ── Evidence ───────────────────────────────────────────────────────────────────

async def add_evidence(case_id: int, guild_id: str, content: str, submitted_by: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO evidence (case_id, guild_id, content, submitted_by) VALUES (?, ?, ?, ?)",
            (case_id, guild_id, content, submitted_by),
        )
        await db.commit()
        return cur.lastrowid


async def get_evidence(case_id: int, guild_id: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, content, submitted_by, submitted_at FROM evidence WHERE case_id = ? AND guild_id = ? ORDER BY id",
            (case_id, guild_id),
        ) as cur:
            return [{"id": r[0], "content": r[1], "submitted_by": r[2], "submitted_at": r[3]} for r in await cur.fetchall()]


# ── Watchlist ──────────────────────────────────────────────────────────────────

async def add_watchlist(guild_id: str, user_id: str, reason: str, added_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO watchlist (guild_id, user_id, reason, added_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, added_by),
        )
        await db.commit()


async def remove_watchlist(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM watchlist WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


async def get_watchlist_entry(guild_id: str, user_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT reason, added_by, added_at FROM watchlist WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)
        ) as cur:
            row = await cur.fetchone()
            return {"reason": row[0], "added_by": row[1], "added_at": row[2]} if row else None


# ── Warnings ───────────────────────────────────────────────────────────────────

async def add_warning(guild_id: str, user_id: str, reason: str, warned_by: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO warnings (guild_id, user_id, reason, warned_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, warned_by),
        )
        await db.commit()
        return cur.lastrowid


async def get_warnings(guild_id: str, user_id: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, reason, warned_by, warned_at FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
            (guild_id, user_id),
        ) as cur:
            return [{"id": r[0], "reason": r[1], "warned_by": r[2], "warned_at": r[3]} for r in await cur.fetchall()]


async def clear_warnings(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


# ── Strikes ────────────────────────────────────────────────────────────────────

async def add_strike(guild_id: str, user_id: str, reason: str, struck_by: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO strikes (guild_id, user_id, reason, struck_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, struck_by),
        )
        await db.commit()
        return cur.lastrowid


async def get_strikes(guild_id: str, user_id: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, reason, struck_by, struck_at FROM strikes WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
            (guild_id, user_id),
        ) as cur:
            return [{"id": r[0], "reason": r[1], "struck_by": r[2], "struck_at": r[3]} for r in await cur.fetchall()]


async def clear_strikes(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM strikes WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


# ── Blacklist ──────────────────────────────────────────────────────────────────

async def add_blacklist(guild_id: str, user_id: str, reason: str, added_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO blacklist (guild_id, user_id, reason, added_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, added_by),
        )
        await db.commit()


async def remove_blacklist(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM blacklist WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


async def is_blacklisted(guild_id: str, user_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM blacklist WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cur:
            return (await cur.fetchone()) is not None


# ── Suspensions ────────────────────────────────────────────────────────────────

async def add_suspension(guild_id: str, user_id: str, reason: str, suspended_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO suspensions (guild_id, user_id, reason, suspended_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, suspended_by),
        )
        await db.commit()


async def remove_suspension(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM suspensions WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


async def is_suspended(guild_id: str, user_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM suspensions WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cur:
            return (await cur.fetchone()) is not None


# ── Wanted ─────────────────────────────────────────────────────────────────────

async def add_wanted(guild_id: str, user_id: str, reason: str, added_by: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO wanted (guild_id, user_id, reason, added_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, reason, added_by),
        )
        await db.commit()


async def remove_wanted(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM wanted WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
        await db.commit()


async def is_wanted(guild_id: str, user_id: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM wanted WHERE guild_id = ? AND user_id = ?", (guild_id, user_id)) as cur:
            return (await cur.fetchone()) is not None


# ── LOAs ───────────────────────────────────────────────────────────────────────

async def add_loa(guild_id: str, user_id: str, reason: str, granted_by: str, start_at: int, end_at: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE loas SET active = 0 WHERE guild_id = ? AND user_id = ? AND active = 1",
            (guild_id, user_id),
        )
        cur = await db.execute(
            "INSERT INTO loas (guild_id, user_id, reason, granted_by, start_at, end_at) VALUES (?, ?, ?, ?, ?, ?)",
            (guild_id, user_id, reason, granted_by, start_at, end_at),
        )
        await db.commit()
        return cur.lastrowid


async def get_active_loa(guild_id: str, user_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, reason, granted_by, start_at, end_at FROM loas WHERE guild_id = ? AND user_id = ? AND active = 1",
            (guild_id, user_id),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "reason": row[1], "granted_by": row[2], "start_at": row[3], "end_at": row[4]}


async def end_loa(guild_id: str, user_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE loas SET active = 0 WHERE guild_id = ? AND user_id = ? AND active = 1",
            (guild_id, user_id),
        )
        await db.commit()


async def get_expired_loas(now: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, guild_id, user_id FROM loas WHERE active = 1 AND end_at <= ?", (now,)
        ) as cur:
            return [{"id": r[0], "guild_id": r[1], "user_id": r[2]} for r in await cur.fetchall()]


async def list_active_loas(guild_id: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, reason, granted_by, end_at FROM loas WHERE guild_id = ? AND active = 1 ORDER BY end_at",
            (guild_id,),
        ) as cur:
            return [{"user_id": r[0], "reason": r[1], "granted_by": r[2], "end_at": r[3]} for r in await cur.fetchall()]


# ── Medals ─────────────────────────────────────────────────────────────────────

async def award_medal(guild_id: str, user_id: str, medal_name: str, awarded_by: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO medals (guild_id, user_id, medal_name, awarded_by) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, medal_name, awarded_by),
        )
        await db.commit()
        return cur.lastrowid


async def get_medals(guild_id: str, user_id: str) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, medal_name, awarded_by, awarded_at FROM medals WHERE guild_id = ? AND user_id = ? ORDER BY awarded_at DESC",
            (guild_id, user_id),
        ) as cur:
            return [{"id": r[0], "medal_name": r[1], "awarded_by": r[2], "awarded_at": r[3]} for r in await cur.fetchall()]


# ── Tickets ────────────────────────────────────────────────────────────────────

async def create_ticket(guild_id: str, channel_id: str, user_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO tickets (guild_id, channel_id, user_id) VALUES (?, ?, ?)",
            (guild_id, channel_id, user_id),
        )
        await db.commit()
        return cur.lastrowid


async def get_ticket_by_channel(channel_id: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, guild_id, user_id, status, created_at FROM tickets WHERE channel_id = ?", (channel_id,)
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return {"id": row[0], "guild_id": row[1], "user_id": row[2], "status": row[3], "created_at": row[4]}


async def close_ticket_db(channel_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tickets SET status = 'CLOSED' WHERE channel_id = ?", (channel_id,))
        await db.commit()
