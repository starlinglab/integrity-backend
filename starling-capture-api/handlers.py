from aiohttp import web


async def process_image(request):
    response = {"result": "ok", "jwt_payload": request["jwt_payload"]}
    # TODO(anaulin): Implement.
    return web.json_response(response)
