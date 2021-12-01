import asyncio
import logging

import edgedb
import fastapi
import pydantic
from edgedb import asyncio_con
from edgedb import con_utils
from edgedb.protocol import protocol
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from . import config

logger = logging.getLogger(__name__)


async def async_connect_raw(
    dsn: str = None,
    *,
    credentials_file: str = None,
    host: str = None,
    port: int = None,
    user: str = None,
    password: str = None,
    database: str = None,
    tls_ca_file: str = None,
    tls_security: str = None,
    edgedb_settings=None,
    connection_class=None,
    wait_until_available: int = 30,
    timeout: int = 10
) -> edgedb.AsyncIOConnection:
    loop = asyncio.get_running_loop()

    if connection_class is None:
        connection_class = edgedb.AsyncIOConnection

    if edgedb_settings is None:
        connect_config, client_config = con_utils.parse_connect_arguments(
            dsn=dsn,
            credentials_file=credentials_file,
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            timeout=timeout,
            tls_ca_file=tls_ca_file,
            tls_security=tls_security,
            wait_until_available=wait_until_available,
            # ToDos
            command_timeout=None,
            server_settings=None,
        )
    else:
        connect_config, client_config = (
            edgedb_settings.connect_config,
            edgedb_settings.client_config,
        )

    connection = connection_class(
        loop,
        [connect_config.address],
        client_config,
        connect_config,
        codecs_registry=protocol.CodecsRegistry(),
        query_cache=protocol.QueryCodecsCache(),
    )
    await connection.ensure_connected()
    return connection


edgedb.async_connect_raw = asyncio_con.async_connect_raw = async_connect_raw


class JSONTextResponse(fastapi.Response):
    media_type = "application/json"


class Error(pydantic.BaseModel):
    message: str


class DatabaseClient(edgedb.AsyncIOClient):
    pass


async def get_db_client(
    request: fastapi.Request,
    edgedb_settings=fastapi.Depends(config.get_edgedb_settings),
):
    app = request.app
    state = app.state
    client = getattr(state, "db_client", None)
    if client is None:
        logger.info("Initializing database client...")
        state.db_client = client = edgedb.create_async_client(
            edgedb_settings=edgedb_settings
        )

        async def shutdown_db_client():
            delattr(app.state, "db_client")
            logger.info("Shutting down database client...")
            await client.aclose()

        app.router.on_shutdown.insert(0, shutdown_db_client)

    return client


def init_app(app):
    @app.exception_handler(edgedb.NoDataError)
    async def no_data_error_handler(_request, _exc):
        return JSONResponse(
            jsonable_encoder(Error(message="Not found")),
            status_code=status.HTTP_404_NOT_FOUND,
        )
