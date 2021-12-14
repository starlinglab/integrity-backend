from typing import Pattern
from .actions import Actions
from .asset_helper import AssetHelper

from contextlib import contextmanager

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import logging
import time
import traceback

_actions = Actions()
_asset_helper = AssetHelper()
_logger = logging.getLogger(__name__)


@contextmanager
def caught_and_logged_exceptions(event):
    """Helper for fiile handlers to catch and log any exceptions."""
    try:
        yield
    except Exception as err:
        print(traceback.format_exc())
        _logger.error(f"Processing of event {event} errored with: {err}")


class FsWatcher:
    """Watches directories for file changes."""

    def watch(self):
        observer = Observer()
        patterns = ["*.jpg", "*.jpeg"]
        observer.schedule(
            self.AddHandler(patterns=patterns),
            recursive=True,
            path=_asset_helper.get_assets_add(),
        )
        observer.schedule(
            self.UpdateHandler(patterns=patterns),
            recursive=True,
            path=_asset_helper.get_assets_update(),
        )
        observer.schedule(
            self.StoreHandler(patterns=patterns),
            recursive=True,
            path=_asset_helper.get_assets_store(),
        )
        _logger.info("Starting up file system watcher for action directories.")
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            _logger.warning("Caught keyboard interrupt. Stopping FsWatcher.")
        observer.join()

    class AddHandler(PatternMatchingEventHandler):
        """Handles file changes for add action."""

        def on_created(self, event):
            with caught_and_logged_exceptions(event):
                _actions.add(event.src_path)

    class UpdateHandler(PatternMatchingEventHandler):
        """Handles file changes for update action."""

        def on_created(self, event):
            with caught_and_logged_exceptions(event):
                _actions.update(event.src_path)

    class StoreHandler(PatternMatchingEventHandler):
        """Handles file changes for store action."""

        def on_created(self, event):
            with caught_and_logged_exceptions(event):
                _actions.store(event.src_path)
