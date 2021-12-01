import asyncio
import logging

import asgi_lifespan
import edgedb
import pytest
import uvloop
from httpx import AsyncClient

from cii import config
from cii.main import get_app

uvloop.install()
logger = logging.getLogger("cii.tests")
local_settings = config.EdgeDBSettings()

TEST_ENV_FILE = ".test.env"


@pytest.fixture
def anyio_backend():
    return "asyncio"


class TestEdgeDBSettings(config.EdgeDBSettings):
    class Config(config.EdgeDBSettings.Config):
        env_prefix = "edgedb_test_"
        env_file = TEST_ENV_FILE


async def edgedb_settings_loaders():
    async def load():
        logger.info("Loading test EdgeDB settings...")

        settings = TestEdgeDBSettings()
        if settings.connect_config.address == local_settings.connect_config.address:
            dbname = settings.connect_config.database
            if dbname == local_settings.connect_config.database:
                dbname = dbname + "_test"
                settings = TestEdgeDBSettings(database=dbname)
            db = edgedb.create_async_client(edgedb_settings=local_settings)
            try:
                await db.execute(f"CREATE DATABASE {dbname}")
                proc = await asyncio.create_subprocess_exec(
                    "edgedb", "-d", dbname, "migrate"
                )
                await proc.wait()
                assert proc.returncode == 0
            except BaseException:
                await db.execute(f"DROP DATABASE {dbname}")
                raise
            finally:
                await db.aclose()
        else:
            args = ["edgedb"]
            if settings.credentials_file:
                args.extend(["--credentials-file", settings.credentials_file])
            elif settings.dsn:
                args.extend(["--dsn", settings.dsn])
            elif settings.instance:
                args.extend(["--instance", settings.instance])
            else:
                args.extend(
                    [
                        "--host",
                        settings.connect_config.address[0],
                        "--port",
                        settings.connect_config.address[1],
                    ]
                )
            if settings.database:
                args.extend(["--database", settings.connect_config.database])
            if settings.user:
                args.extend(["--user", settings.connect_config.user])
            if settings.tls_ca_file:
                args.extend(["--tls-ca-file", settings.tls_ca_file])
            if settings.client_tls_security:
                args.extend(["--tls-security", settings.connect_config.tls_security])
            if settings.password:
                args.extend(["--password-from-stdin"])
            args.append("migrate")
            proc = await asyncio.create_subprocess_exec(
                *args, stdin=asyncio.subprocess.PIPE if settings.password else None
            )
            if settings.password:
                await proc.communicate(settings.password.encode("utf-8"))
            else:
                await proc.wait()
            assert proc.returncode == 0

        logger.info("Loaded test EdgeDB settings: %r", settings)
        return settings

    async def unload(settings):
        if settings.connect_config.address == local_settings.connect_config.address:
            logger.info("Drop test EdgeDB settings...")
            db = edgedb.create_async_client(edgedb_settings=local_settings)
            try:
                await db.execute(f"DROP DATABASE {settings.connect_config.database}")
            finally:
                await db.aclose()

    return load, unload


async def get_settings():
    logger.info("Loading test settings...")
    settings = config.Settings(_env_file=TEST_ENV_FILE)
    logger.info("Loaded test settings: %r", settings)
    return settings


@pytest.fixture
async def client():
    app = get_app(log_settings=config.LogSettings(_env_file=TEST_ENV_FILE))
    app.dependency_overrides[config.edgedb_settings_loaders] = edgedb_settings_loaders
    app.dependency_overrides[config.get_settings] = get_settings
    async with asgi_lifespan.LifespanManager(app):
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
