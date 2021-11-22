from aiohttp import web

import handlers

if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.get('/image', handlers.process_image)])
    web.run_app(app)
