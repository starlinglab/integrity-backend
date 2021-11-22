from re import S
from aiohttp import web

import handlers
import logging
import sys

_logger = logging.getLogger(__name__)


def configure_logging():
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z"
    )


def start_server():
    app = web.Application()
    app.add_routes([web.get("/image", handlers.process_image)])
    _logger.info("Starting up server")
    web.run_app(app)


if __name__ == "__main__":
    configure_logging()
    start_server()
