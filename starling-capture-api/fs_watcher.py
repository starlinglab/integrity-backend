import logging
import time

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from filecoin import Filecoin

_logger = logging.getLogger(__name__)
_filecoin = Filecoin()


class FsWatcher:
    """Watches directories for file changes."""

    def watch(self, dir_path):
        observer = Observer()
        observer.schedule(self.Handler(), recursive=True, path=dir_path)
        _logger.info("Starting up file system watcher for directory: %s", dir_path)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            _logger.warning("Caught keyboard interrupt. Stopping FsWatcher.")
        observer.join()

    class Handler(PatternMatchingEventHandler):
        """Handles file changes."""

        # File patterns we want to watch for
        # Overrides the patterns property of PatternMatchingEventHandler
        patterns = ["*.jpg", "*.jpeg"]

        def on_created(self, event):
            _logger.info(f"Processing event: {event}")
            cid = _filecoin.upload(event.src_path)
            _logger.info(f"Uploaded {event.src_path}. CID: {cid}")
