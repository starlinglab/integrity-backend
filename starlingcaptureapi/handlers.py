from .actions import Actions
from .multipart import Multipart

from aiohttp import web

import logging
import traceback

_logger = logging.getLogger(__name__)

async def create(request):
    data = await Multipart().read(request)
    status = 200
    response = {
        "asset_fullpath": data.get("asset_fullpath"),
        "jwt_payload": request.get("jwt_payload"),
    }
    try:
        Actions().create(
            data.get("asset_fullpath"), request.get("jwt_payload"), data.get("meta")
        )
    except Exception as err:
        print(traceback.format_exc())
        _logger.error(err)
        status = 500
        response["error"] = f"{err}"

    # TODO(anaulin): Add all the required metadata, errors, etc, to response.
    return web.json_response(response, status=status)

async def create_proofmode(request):
    data = await Multipart().read(request)
    status = 200
    response = {
        "asset_fullpath": data.get("asset_fullpath"),
        "jwt_payload": request.get("jwt_payload"),
    }
    try:
        Actions().create_proofmode(
            data.get("asset_fullpath"), request.get("jwt_payload")
        )
    except Exception as err:
        print(traceback.format_exc())
        _logger.error(err)
        status = 500
        response["error"] = f"{err}"

    # TODO(anaulin): Add all the required metadata, errors, etc, to response.
    return web.json_response(response, status=status)