import copy
import logging
import logging.config
from importlib.metadata import entry_points

import uvicorn.config
from fastapi import FastAPI

from . import config

logger = logging.getLogger(__name__)


def load_modules(app=None):
    for ep in entry_points(group="cii.modules"):
        logger.info("Loading module: %s", ep.name)
        mod = ep.load()
        if app:
            init_app = getattr(mod, "init_app", None)
            if init_app:
                init_app(app)


def setup_logging(log_settings):
    if log_settings is None:
        log_settings = config.LogSettings()
    logging_config = copy.deepcopy(uvicorn.config.LOGGING_CONFIG)
    logging_config["loggers"]["cii"] = {"handlers": ["default"]}
    for _logger in logging_config["loggers"].values():
        _logger["level"] = log_settings.log_level
    logging.config.dictConfig(logging_config)


def get_app(log_settings=None):
    setup_logging(log_settings)
    app = FastAPI()
    load_modules(app)
    return app
