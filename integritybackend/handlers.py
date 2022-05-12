from contextlib import contextmanager

from .actions import Actions
from .log_helper import LogHelper
from .multipart import Multipart

from aiohttp import web

import traceback


_logger = LogHelper.getLogger()


async def create(request):
    with error_handling_and_response() as response:
        data = await Multipart(request).read()

        if "meta" not in data:
            raise ValueError("Missing 'meta' section in request")

        Actions().create(data.get("asset_fullpath"), request.get("jwt_payload"), data)

    return web.json_response(response, status=response.get("status_code"))


# TODO: change for new action c2pa_proofmode
# Maybe remove API path entirely?
async def create_proofmode(request):
    with error_handling_and_response() as response:
        data = await Multipart(request).read()
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
