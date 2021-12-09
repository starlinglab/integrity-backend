from .actions import Actions
from .multipart import Multipart

from aiohttp import web


async def create(request):
    data = await Multipart().read(request)
    Actions().create(data["asset_fullpath"], request["jwt_payload"], data["meta"])

    # TODO(anaulin): Add error handling.
    # TODO(anaulin): Add all the required metadata, errors, etc, to response.
    response = {
        "result": "ok",
        "asset_fullpath": data["asset_fullpath"],
        "jwt_payload": request["jwt_payload"],
    }
    return web.json_response(response)
