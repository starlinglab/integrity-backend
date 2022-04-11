import logging
import sys


class LogHelper:

    @staticmethod
    def getLogger():
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.INFO,
            format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        return logging.getLogger(__name__)