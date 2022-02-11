from .actions import Actions
from .asset_helper import AssetHelper

from contextlib import contextmanager

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import logging
import time
import traceback

_actions = Actions()
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

    def __init__(self, organization_id):
        self.organization_id = organization_id

    def watch(self):
        """
        Args:
            organization_id: a string identifying the organization we are watching for
        """
        observer = Observer()
        patterns = ["*.jpg", "*.jpeg"]
        asset_helper = AssetHelper(self.organization_id)
        observer.schedule(
            self.AddHandler(patterns=patterns).set_org_id(self.organization_id),
            recursive=True,
            path=asset_helper.get_assets_add(),
        )
        observer.schedule(
            self.UpdateHandler(patterns=patterns).set_org_id(self.organization_id),
            recursive=True,
            path=asset_helper.get_assets_update(),
        )
        observer.schedule(
            self.StoreHandler(patterns=patterns).set_org_id(self.organization_id),
            recursive=True,
            path=asset_helper.get_assets_store(),
        )
        observer.schedule(
            self.CustomHandler(patterns=patterns).set_org_id(self.organization_id),
            recursive=True,
            path=asset_helper.get_assets_custom(),
        )
        _logger.info(
            "Starting up file system watcher for action directories of organization %s",
            self.organization_id,
        )
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            _logger.warning("Caught keyboard interrupt. Stopping FsWatcher.")
        observer.join()

    class OrganizationHandler(PatternMatchingEventHandler):
        """A base handler that knows which organization it is working for."""

        def set_org_id(self, organization_id):
            """Sets the organization id for this handler.

            Args:
                organization_id: string with the unique organization id this handler is for

            Returns:
                the handler itself
            """
            self.organization_id = organization_id
            return self

    class AddHandler(OrganizationHandler):
        """Handles file changes for add action."""

        def on_created(self, event):
            with caught_and_logged_exceptions(event):
                _actions.add(self.organization_id, event.src_path)

    class UpdateHandler(OrganizationHandler):
        """Handles file changes for update action."""

        def on_created(self, event):
            with caught_and_logged_exceptions(event):
                _actions.update(self.organization_id, event.src_path)

    class StoreHandler(OrganizationHandler):
        """Handles file changes for store action."""

        def on_created(self, event):
            with caught_and_logged_exceptions(event):
                _actions.store(self.organization_id, event.src_path)

    class CustomHandler(OrganizationHandler):
        """Handles file changes for custom action."""

        def on_created(self, event):
            with caught_and_logged_exceptions(event):
                _actions.custom(self.organization_id, event.src_path)
