from contextlib import contextmanager

from .actions import Actions
from .multipart import Multipart

from aiohttp import web

import logging
import traceback

_logger = logging.getLogger(__name__)


async def create(request):
    with error_handling_and_response() as response:
        data = await Multipart().read(request)

        if "meta" not in data:
            raise ValueError("Missing 'meta' section in request")

        Actions().create(data.get("asset_fullpath"), request.get("jwt_payload"), data)

    return web.json_response(response, status=response.get("status_code"))


async def create_proofmode(request):
    with error_handling_and_response() as response:
        data = await Multipart().read(request)
        Actions().create_proofmode(
            data.get("asset_fullpath"), request.get("jwt_payload")
        )

    return web.json_response(response, status=response.get("status_code"))


@contextmanager
def error_handling_and_response():
    """Context manager to wrap the core of a handler implementation with error handlers.

    Yields:
        response: dict containing a status and any errors encountered
    """
    response = {"status": "ok", "status_code": 200}
    try:
        yield response
    except Exception as err:
        print(traceback.format_exc())
        _logger.error(err)
        response["error"] = f"{err}"
        response["status"] = "error"
        if type(err) == ValueError:
            response["status_code"] = 400
        else:
            response["status_code"] = 500
