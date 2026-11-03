"""鉴权配置、媒体 ACL 与迁移补丁的单元测试。不连接数据库。"""
from __future__ import annotations

import asyncio
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.core.config import Settings
from app.core.legacy_schema import assemble_upgrade_sql, pending_legacy_statements
from app.core.runtime_config import (
    DEMO_JWT_SECRET,
    apply_runtime_defaults,
    assert_production_admin_password,
    demo_user_password,
    ensure_media_backend_supported,
    resolve_cors_origins,
    validate_runtime_config,
)
from app.core.security import check_password_strength
from app.services.media_access import can_read_media
from app.services.media_storage import (
    DatabaseMediaStorage,
    FilesystemMediaStorage,
    read_stored_bytes,
)


def _settings(**kwargs) -> Settings:
    base = dict(
        APP_ENV="production",
        DEMO_MODE=False,
        SECRET_KEY="",
        DATABASE_URL="",
        CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:5173",
        MEDIA_STORAGE="db",
        SUPER_ADMIN_PASSWORD="",
        DEMO_PASSWORD="",
        DEMO_ADMIN_PASSWORD="",
    )
    base.update(kwargs)
    return Settings(_env_file=None, **base)


class RuntimeConfigTests(unittest.TestCase):
    def test_production_rejects_empty_secret_and_demo_database(self):
        settings = _settings(DATABASE_URL="mysql://root:123456@mysql:3306/ai_kb")
        with self.assertRaises(RuntimeError) as ctx:
            validate_runtime_config(settings)
        message = str(ctx.exception)
        self.assertIn("SECRET_KEY", message)
        self.assertIn("DATABASE_URL", message)
        self.assertIn("APP_ENV=demo", message)

    def test_production_rejects_placeholder_secret(self):
        settings = _settings(
            SECRET_KEY="change-me-in-prod",
            DATABASE_URL="mysql://app:another-secret@db.internal:3306/pet",
        )
        with self.assertRaises(RuntimeError):
            validate_runtime_config(settings)

    def test_production_rejects_wildcard_cors(self):
        settings = _settings(
            SECRET_KEY="p" * 40,
            DATABASE_URL="mysql://app:another-secret@db.internal:3306/pet",
            CORS_ORIGINS="*",
        )
        with self.assertRaises(RuntimeError):
            validate_runtime_config(settings)

    def test_production_accepts_real_secrets(self):
        settings = _settings(
            SECRET_KEY="p" * 40,
            DATABASE_URL="mysql://app:another-secret@db.internal:3306/pet",
            CORS_ORIGINS="https://pet.example.com, https://admin.example.com/",
        )
        validate_runtime_config(settings)
        self.assertEqual(
            resolve_cors_origins(settings),
            ["https://pet.example.com", "https://admin.example.com"],
        )

    def test_demo_mode_fills_local_defaults_and_still_rejects_star(self):
        settings = _settings(APP_ENV="demo", SECRET_KEY="", DATABASE_URL="", CORS_ORIGINS="")
        apply_runtime_defaults(settings)
        validate_runtime_config(settings)
        self.assertEqual(settings.SECRET_KEY, DEMO_JWT_SECRET)
        self.assertIn("root:123456", settings.DATABASE_URL)
        self.assertIn("http://localhost:5173", resolve_cors_origins(settings))
        settings.CORS_ORIGINS = "*"
        with self.assertRaises(RuntimeError):
            resolve_cors_origins(settings)

    def test_demo_password_helpers_are_closed_in_production(self):
        settings = _settings()
        with self.assertRaises(RuntimeError):
            demo_user_password(settings)
        self.assertEqual(check_password_strength("Passw0rd!a"), "")
        with self.assertRaises(RuntimeError):
            assert_production_admin_password("Passw0rd!a")
        with self.assertRaises(RuntimeError):
            assert_production_admin_password("admin123")
        assert_production_admin_password("GoodPass1!")

    def test_s3_backend_is_rejected(self):
        settings = _settings(MEDIA_STORAGE="s3", S3_BUCKET="", S3_ENDPOINT="")
        with self.assertRaises(RuntimeError) as ctx:
            ensure_media_backend_supported(settings)
        self.assertIn("s3", str(ctx.exception).lower())


class MediaAccessTests(unittest.TestCase):
    def test_catalog_and_owner_rules(self):
        owner = SimpleNamespace(id=1, role="user")
        other = SimpleNamespace(id=2, role="user")
        admin = SimpleNamespace(id=9, role="admin")
        pet = SimpleNamespace(owner_id=1, purpose="pet")
        listing = SimpleNamespace(owner_id=1, purpose="listing")
        legacy = SimpleNamespace(owner_id=None, purpose="other")

        self.assertTrue(can_read_media(owner, pet))
        self.assertFalse(can_read_media(other, pet))
        self.assertTrue(can_read_media(admin, pet))
        self.assertTrue(can_read_media(other, listing))
        self.assertTrue(can_read_media(other, legacy))
        self.assertFalse(can_read_media(other, SimpleNamespace(owner_id=1, purpose="other")))


class MediaStorageTests(unittest.TestCase):
    def test_filesystem_roundtrip_and_legacy_base64(self):
        async def scenario():
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                files = FilesystemMediaStorage(root)
                pointer = await files.put(
                    asset_id=7,
                    filename="a.png",
                    content_type="image/png",
                    data=b"png-bytes",
                )
                self.assertTrue(pointer.startswith("storage:filesystem:"))
                self.assertEqual(await files.read(pointer), b"png-bytes")
                database = DatabaseMediaStorage(root)
                legacy = await database.put(
                    asset_id=1,
                    filename="b.jpg",
                    content_type="image/jpeg",
                    data=b"jpg-bytes",
                )
                self.assertNotIn("storage:", legacy)
                self.assertEqual(await database.read(legacy), b"jpg-bytes")
                self.assertEqual(await database.read(pointer), b"png-bytes")
                with self.assertRaises(ValueError):
                    read_stored_bytes("storage:filesystem:../secret", root)

        asyncio.run(scenario())


class _FakeDB:
    def __init__(self, tables: set[str], columns: set[tuple[str, str]]):
        self.tables = {name.lower() for name in tables}
        self.columns = {(table.lower(), column.lower()) for table, column in columns}

    async def execute_query(self, query, values=None):
        compact = " ".join(query.split()).lower()
        if "information_schema.columns" in compact:
            ok = (values[0].lower(), values[1].lower()) in self.columns
        elif "information_schema.tables" in compact:
            ok = values[0].lower() in self.tables
        else:
            raise AssertionError(query)
        return (1, [{"ok": 1}]) if ok else (0, [])


class MigrationTests(unittest.TestCase):
    def _migration(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "models"
            / "0_20261103030000_init.py"
        )
        spec = importlib.util.spec_from_file_location("aerich_init", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_fresh_database_has_no_alter(self):
        async def scenario():
            module = self._migration()
            sql = await module.upgrade(_FakeDB(set(), set()))
            self.assertIn("CREATE TABLE IF NOT EXISTS `user`", sql)
            self.assertIn("CREATE TABLE IF NOT EXISTS `media_asset`", sql)
            self.assertNotIn("ALTER TABLE", sql)

        asyncio.run(scenario())

    def test_existing_database_only_adds_missing_columns(self):
        async def scenario():
            module = self._migration()
            sql = await module.upgrade(
                _FakeDB(
                    {"conversation", "trainerprofile"},
                    {("conversation", "id"), ("trainerprofile", "id")},
                )
            )
            self.assertIn("ALTER TABLE `conversation` ADD COLUMN `channel`", sql)
            self.assertIn("ALTER TABLE `trainerprofile` ADD COLUMN `experience`", sql)
            self.assertIn("UPDATE `trainerprofile`", sql)
            self.assertNotIn("DROP TABLE", sql)
            with self.assertRaises(RuntimeError):
                await module.downgrade(None)

        asyncio.run(scenario())

    def test_assemble_keeps_statements_ordered(self):
        sql = assemble_upgrade_sql("CREATE TABLE IF NOT EXISTS `user` (`id` INT);", ["ALTER TABLE `user` ADD COLUMN `role` VARCHAR(20) NULL"])
        self.assertTrue(sql.index("CREATE TABLE") < sql.index("ALTER TABLE"))


if __name__ == "__main__":
    unittest.main()
