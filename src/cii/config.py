import functools
import logging
import os
from typing import Any, Optional

import fastapi
import pydantic
from edgedb import con_utils

logger = logging.getLogger(__name__)


class LogSettings(pydantic.BaseSettings):
    log_level: int = logging.INFO

    @pydantic.validator("log_level")
    def parse_log_level(cls, lvl):
        if isinstance(lvl, int):
            return lvl
        return logging.Logger("", lvl.upper()).level

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class EdgeDBSettings(pydantic.BaseSettings):
    dsn: Optional[str]
    instance: Optional[str]
    credentials_file: Optional[str]
    host: Optional[str]
    port: Optional[int]
    database: Optional[str]
    user: Optional[str]
    password: Optional[str]
    tls_ca_file: Optional[str]
    client_tls_security: Optional[str]
    connect_config: Optional[Any]
    client_config: Optional[Any]

    class Config:
        env_prefix = "edgedb_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        orig_env = os.environ
        env = orig_env.copy()
        for name in self.__fields__:
            value = getattr(self, name)
            if value is not None:
                env[f"EDGEDB_{name.upper()}"] = value
        os.environ = env
        try:
            self.connect_config, self.client_config = con_utils.parse_connect_arguments(
                dsn=self.dsn,
                credentials_file=self.credentials_file,
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                tls_ca_file=self.tls_ca_file,
                tls_security=self.client_tls_security,
                timeout=None,
                command_timeout=None,
                wait_until_available=None,
                server_settings=None,
            )
        finally:
            os.environ = orig_env

    def __hash__(self):
        return hash(self.connect_config)


async def edgedb_settings_loaders():
    async def load():
        logger.info("Loading EdgeDB settings...")
        return EdgeDBSettings()

    return load, None


async def get_edgedb_settings(
    request: fastapi.Request, loaders=fastapi.Depends(edgedb_settings_loaders)
) -> EdgeDBSettings:
    app = request.app
    state = app.state
    load, unload = loaders
    settings = getattr(state, "edgedb_settings", None)
    if settings is None:
        settings = state.edgedb_settings = await load()

        @app.on_event("shutdown")
        async def drop_edgedb_settings():
            delattr(state, "edgedb_settings")
            if unload:
                await unload(settings)

    return settings


class Settings(pydantic.BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@functools.lru_cache()
def get_cached_settings() -> Settings:
    logger.info("Loading settings...")
    return Settings()


async def get_settings() -> Settings:
    return get_cached_settings()
