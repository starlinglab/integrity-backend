from aiohttp import web
from aiohttp_jwt import JWTMiddleware

import logging
import multiprocessing
import os
import signal
import sys
import time


from starlingcaptureapi import config, handlers
from starlingcaptureapi.asset_helper import AssetHelper
from starlingcaptureapi.fs_watcher import FsWatcher


_logger = logging.getLogger(__name__)
_procs = list()


def signal_handler(signum, frame):
    """
    SIGINT handler for the main process.
    """
    _logger.info("Terminating processes...")
    kill_processes(_procs)
    sys.exit(0)


def kill_processes(procs):
    for proc in procs:
        if proc.is_alive():
            try:
                proc.terminate()

                # Allow up to 10 seconds for the process to terminate
                i = 0
                while proc.is_alive() and i < 20:
                    time.sleep(0.5)
                    i += 1
            except os.error as err:
                _logger.warning("Caught error while killing processes: %s", err)

        if proc.is_alive():
            _logger.info("Process %s [%s] is not terminated" % (proc.pid, proc.name))
        else:
            _logger.info("Process %s [%s] is terminated" % (proc.pid, proc.name))


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
    app.add_routes([web.post("/v1/assets/create", handlers.create)])
    app.add_routes([web.post("/v1/assets/create-proofmode", handlers.create_proofmode)])
    _logger.info("Starting up API server")
    web.run_app(app)


def start_fs_watcher(org_id):
    FsWatcher(org_id).watch()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    configure_logging()

    # Configure asset directories.
    for org_id in config.ORGANIZATION_CONFIG.all_orgs():
        AssetHelper(org_id).init_dirs()

    # Start up processes for services.

    # Start up a file watcher for each organization
    for org_id in config.ORGANIZATION_CONFIG.all_orgs():
        _procs.append(
            multiprocessing.Process(
                name=f"fs_watcher_{org_id}", target=start_fs_watcher, args=(org_id,)
            )
        )

    proc_api_server = multiprocessing.Process(
        name="api_server", target=start_api_server
    )
    _procs.append(proc_api_server)

    for proc in _procs:
        proc.start()
