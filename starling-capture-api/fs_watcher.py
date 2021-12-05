from actions import Actions
from asset_helper import AssetHelper

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import logging
import time

_actions = Actions()
_asset_helper = AssetHelper()
_logger = logging.getLogger(__name__)


class FsWatcher:
    """Watches directories for file changes."""

    def watch(self):
        observer = Observer()
        observer.schedule(self.AddHandler(), recursive=True, path=_asset_helper.get_assets_add())
        observer.schedule(self.UpdateHandler(), recursive=True, path=_asset_helper.get_assets_update())
        observer.schedule(self.StoreHandler(), recursive=True, path=_asset_helper.get_assets_store())
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

        # File patterns we want to watch for
        # Overrides the patterns property of PatternMatchingEventHandler
        patterns = ["*.jpg", "*.jpeg"]

        def on_created(self, event):
            _actions.add(event.src_path)

    class UpdateHandler(PatternMatchingEventHandler):
        """Handles file changes for update action."""

        # File patterns we want to watch for
        # Overrides the patterns property of PatternMatchingEventHandler
        patterns = ["*.jpg", "*.jpeg"]

        def on_created(self, event):
            _actions.update(event.src_path)

    class StoreHandler(PatternMatchingEventHandler):
        """Handles file changes for store action."""

        # File patterns we want to watch for
        # Overrides the patterns property of PatternMatchingEventHandler
        patterns = ["*.jpg", "*.jpeg"]

        def on_created(self, event):
            _actions.store(event.src_path)