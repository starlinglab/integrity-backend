import logging
import time

import watchdog

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

        # Event types that we want to ignore
        ignored_event_types = [
            watchdog.events.EVENT_TYPE_CLOSED,
            watchdog.events.EVENT_TYPE_CREATED,
            watchdog.events.EVENT_TYPE_DELETED,
            watchdog.events.EVENT_TYPE_MOVED,
        ]

        # Used for duplicate modified debouncing issue in watchdog (see below)
        last_modified_trigger_time = time.time()
        last_modified_trigger_path = ""

        def process(self, event):
            """Processes file change event.

            Args:
                event: the file change event
            """
            _logger.info(f"Processing event: {event}")
            # TODO: Only process files in the appropriate directories.
            # TODO: Something in the implementation of the upload triggers another
            #       FileModified event, which causes a second upload (but only a second one).
            #       Figure out how to prevent that from happening.
            cid = _filecoin.upload(event.src_path)
            _logger.info(f"Uploaded {event.src_path}. CID: {cid}")

        def on_any_event(self, event):
            """Receives events of all types and dispatches them appropriately."""
            if self._should_process(event):
                self.process(event)

        def _should_process(self, event):
            """Returns True if this is an event we want to process."""
            if event.is_directory:
                return False

            if event.event_type in self.ignored_event_types:
                return False

            if self._is_duplicate_modified_event(event):
                return False

            return True

        def _is_duplicate_modified_event(self, event):
            # Duplicate modified event debouncing
            # Workaround for issue https://github.com/gorakhargosh/watchdog/issues/346
            current_time = time.time()
            if (
                event.event_type == watchdog.events.EVENT_TYPE_MODIFIED
                and event.src_path == self.last_modified_trigger_path
                and (current_time - self.last_modified_trigger_time) <= 1
            ):
                return True
            else:
                self.last_modified_trigger_time = current_time
                self.last_modified_trigger_path = event.src_path
                return False
