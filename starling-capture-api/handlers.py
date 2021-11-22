from aiohttp import web

async def process_image(request):
    return web.json_response({'result': 'ok'})
