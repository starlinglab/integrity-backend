from aiohttp import web
from aiohttp_jwt import JWTMiddleware
from fs_watcher import FsWatcher

import config
import handlers
import logging
import multiprocessing
import os
import signal
import sys
import time

_logger = logging.getLogger(__name__)
_procs = list()

def signalHandler(signum, frame):
    '''
    SIGINT handler for the main process.
    '''
    print('Terminating processes...')
    killProcesses(_procs)
    sys.exit(0)


def killProcesses(procs):
    for proc in procs:
        if proc.is_alive():
            try:
                proc.terminate()

                # Allow up to 10 seconds for the process to terminate
                i = 0
                while proc.is_alive() and i < 20:
                    time.sleep(0.5)
                    i += 1
            except os.error:
                pass

        if proc.is_alive():
            print('Process %s [%s] is not terminated' % (proc.pid, proc.name))
        else:
            print('Process %s [%s] is terminated' % (proc.pid, proc.name))


def configure_logging():
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )


def start_api_server():
    configure_logging()
    app = web.Application(
        middlewares=[
            JWTMiddleware(
                config.JWT_SECRET, request_property="jwt_payload", algorithms="HS256"
            )
        ]
    )
    app.add_routes([web.post("/assets/create", handlers.create)])
    _logger.info("Starting up API server")
    web.run_app(app)


def start_fs_watcher():
    configure_logging()
    _logger.info("Starting up file system watcher")
    FsWatcher().watch(config.IMAGES_DIR)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signalHandler)
    configure_logging()

    proc_fs_watcher = multiprocessing.Process(name='proc_fs_watcher', target=start_fs_watcher)
    _procs.append(proc_fs_watcher)
    proc_api_server = multiprocessing.Process(name='proc_api_server', target=start_api_server)
    _procs.append(proc_api_server)
    
    proc_fs_watcher.start()
    proc_api_server.start()