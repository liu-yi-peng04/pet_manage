"""旧库缺列补丁。

生产环境只能通过 Aerich 迁移执行，应用启动不得再跑这些 ALTER。
演示模式在 DEMO_AUTO_SCHEMA=true 时仍会调用 apply_legacy_column_guards，
这样未执行 aerich upgrade 的本地库不会丢列。语句都是加法，不删表、不清数据。
"""
from __future__ import annotations

# (表名, 列名, ADD COLUMN 的列定义)
LEGACY_COLUMN_DDL: list[tuple[str, str, str]] = [
    ("conversation", "channel", "`channel` VARCHAR(32) NOT NULL DEFAULT 'user'"),
    ("appointment", "trainer_id", "`trainer_id` INT NULL"),
    ("trainerprofile", "avatar_url", "`avatar_url` VARCHAR(500) NULL"),
    # 已有行时 LONGTEXT NOT NULL 且无默认值会失败，先加可空列，再回填。
    ("trainerprofile", "experience", "`experience` LONGTEXT NULL"),
    ("trainerprofile", "cert_note", "`cert_note` LONGTEXT NULL"),
    ("trainerprofile", "proof_images", "`proof_images` LONGTEXT NULL"),
]

# 只填空值，不覆盖已有文案。
LEGACY_BACKFILL_SQL: list[str] = [
    "UPDATE `trainerprofile` SET `experience` = COALESCE(`experience`, '')",
    "UPDATE `trainerprofile` SET `cert_note` = COALESCE(`cert_note`, '')",
    "UPDATE `trainerprofile` SET `proof_images` = COALESCE(NULLIF(`proof_images`, ''), '[]')",
]


def assemble_upgrade_sql(create_sql: str, extra: list[str]) -> str:
    script = create_sql.strip()
    cleaned = [item.strip().rstrip(";") for item in extra if item and item.strip()]
    if not script.endswith(";"):
        script += ";"
    if not cleaned:
        return script
    return script + "\n" + ";\n".join(cleaned) + ";"


async def _exists(db, query: str, values: list) -> bool:
    _count, rows = await db.execute_query(query, values)
    return bool(rows)


async def _table_exists(db, table: str) -> bool:
    return await _exists(
        db,
        """
        SELECT 1 AS ok FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND LOWER(TABLE_NAME) = LOWER(%s)
        LIMIT 1
        """,
        [table],
    )


async def _column_exists(db, table: str, column: str) -> bool:
    return await _exists(
        db,
        """
        SELECT 1 AS ok FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND LOWER(TABLE_NAME) = LOWER(%s)
          AND LOWER(COLUMN_NAME) = LOWER(%s)
        LIMIT 1
        """,
        [table, column],
    )


async def pending_legacy_statements(db) -> list[str]:
    """根据当前库生成补列与空值回填。新库还没有表时不发 ALTER，交给 CREATE TABLE。"""
    statements: list[str] = []
    for table, column, ddl in LEGACY_COLUMN_DDL:
        if await _table_exists(db, table) and not await _column_exists(db, table, column):
            statements.append(f"ALTER TABLE `{table}` ADD COLUMN {ddl}")
    if await _table_exists(db, "trainerprofile"):
        statements.extend(LEGACY_BACKFILL_SQL)
    return statements


async def apply_legacy_column_guards(conn) -> None:
    """演示模式启动补丁：重复执行时吞掉“列已存在”。生产路径禁止调用。"""
    for table, _column, ddl in LEGACY_COLUMN_DDL:
        try:
            await conn.execute_query(f"ALTER TABLE `{table}` ADD COLUMN {ddl}")
        except Exception:
            pass
    for sql in LEGACY_BACKFILL_SQL:
        try:
            await conn.execute_query(sql)
        except Exception:
            pass


async def assert_aerich_baseline(conn) -> None:
    """生产环境确认至少执行过一次 aerich upgrade，否则拒绝启动。"""
    try:
        _count, rows = await conn.execute_query(
            "SELECT `version` FROM `aerich` WHERE `app`=%s ORDER BY `id` DESC LIMIT 1",
            ["models"],
        )
    except Exception as exc:
        raise RuntimeError(
            "生产环境未检测到 aerich 迁移记录，已拒绝在启动时建表或 ALTER。"
            "请在 backend 目录执行：aerich upgrade"
        ) from exc
    if not rows:
        raise RuntimeError("aerich 表为空，请先在 backend 目录执行 aerich upgrade")
