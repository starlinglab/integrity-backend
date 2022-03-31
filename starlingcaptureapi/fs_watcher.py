from . import config
from .actions import Actions
from .asset_helper import AssetHelper

from contextlib import contextmanager

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import logging
import multiprocessing
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

    def __init__(self, org_config: dict, collection_id: str = None):
        self.org_config = org_config
        self.collection_id = collection_id
        self.organization_id = org_config.get("id")
        self.asset_helper = AssetHelper(self.organization_id)
        self.observer = Observer()

    @staticmethod
    def start(org_config: dict):
        FsWatcher(org_config).watch()

    @staticmethod
    def init_all(
        all_org_config: config.OrganizationConfig = config.ORGANIZATION_CONFIG,
    ) -> list[multiprocessing.Process]:
        """Initialize file watcher processes for the given configuration.

        Args:
            org_config: configuration for all organizations and their actions

        Returns:
            list of un-started processes containing FsWatcher instances
        """
        procs = []
        for org_id, org_config in all_org_config.config.items():
            procs.append(
                multiprocessing.Process(
                    name=f"fs_watcher_{org_id}",
                    target=FsWatcher.start,
                    args=(org_config,),
                )
            )
        return procs

    def watch(self):
        """Start file watching handlers."""
        self._schedule_legacy_handlers()
        for collection_id, collection_config in self.org_config.get(
            "collections", {}
        ).items():
            patterns = [
                f"*.{ext}"
                for ext in collection_config.get("conf", {}).get("asset_extensions", [])
            ]
            for action_name in collection_config.get("actions", {}).keys():
                self._schedule(collection_id, action_name, patterns)

        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            _logger.warning("Caught keyboard interrupt. Stopping FsWatcher.")
        self.observer.join()

    def _schedule(self, collection_id: str, action: str, patterns: list[str]):
        handler_class = ACTION_HANDLER.get(action)
        path = self.asset_helper.path_for(collection_id, action)
        _logger.info(
            f"Scheduling handler {handler_class} for path {path} and patterns {patterns}"
        )
        self.observer.schedule(
            handler_class(patterns=patterns).with_config(
                self.org_config, collection_id
            ),
            recursive=True,
            path=self.asset_helper.path_for(collection_id, action),
        )

    def _schedule_legacy_handlers(self):
        _logger.info(
            "Setting up watcher handlers for legacy action directories of organization %s",
            self.organization_id,
        )
        patterns = ["*.jpg", "*.jpeg"]
        self.observer.schedule(
            AddHandler(patterns=patterns).with_config(self.org_config),
            recursive=True,
            path=self.asset_helper.legacy_path_for("add"),
        )
        self.observer.schedule(
            StoreHandler(patterns=patterns).with_config(self.org_config),
            recursive=True,
            path=self.asset_helper.legacy_path_for("store"),
        )
        self.observer.schedule(
            CustomHandler(patterns=patterns).with_config(self.org_config),
            recursive=True,
            path=self.asset_helper.legacy_path_for("custom"),
        )


class OrganizationHandler(PatternMatchingEventHandler):
    """A base handler that knows which organization it is working for."""

    def with_config(self, org_config: dict, collection_id: str = None):
        """Sets the organization configuration and an optional collection id for this handler.

        Args:
            org_config: a dictionary containing the indexed configuration for this organization
            collection_id: an optional id for the collection this handler is watching for

        Returns:
            the handler itself
        """
        self.org_config = org_config
        self.collection_id = collection_id
        self.organization_id = org_config.get("id")
        return self


class AddHandler(OrganizationHandler):
    """Handles file changes for add action."""

    def on_created(self, event):
        with caught_and_logged_exceptions(event):
            _actions.add(event.src_path, self.org_config, self.collection_id)


class UpdateHandler(OrganizationHandler):
    """Handles file changes for update action."""

    def on_created(self, event):
        with caught_and_logged_exceptions(event):
            _actions.update(event.src_path, self.org_config, self.collection_id)


class StoreHandler(OrganizationHandler):
    """Handles file changes for store action."""

    def on_created(self, event):
        with caught_and_logged_exceptions(event):
            _actions.store(event.src_path, self.org_config, self.collection_id)


class CustomHandler(OrganizationHandler):
    """Handles file changes for custom action."""

    def on_created(self, event):
        with caught_and_logged_exceptions(event):
            _actions.custom(event.src_path, self.org_config, self.collection_id)


class ArchiveHandler(OrganizationHandler):
    """Handles file changes for Archive action."""

    def on_created(self, event):
        with caught_and_logged_exceptions(event):
            _actions.archive(event.src_path, self.org_config, self.collection_id)


# Mapping from action name to handler class
ACTION_HANDLER = {
    "add": AddHandler,
    "archive": ArchiveHandler,
    "custom": CustomHandler,
    "store": StoreHandler,
    "update": UpdateHandler,
}
