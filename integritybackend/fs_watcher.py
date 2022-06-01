from . import config
from .actions import Actions
from .asset_helper import AssetHelper
from .log_helper import LogHelper

from contextlib import contextmanager

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import multiprocessing
import time
import traceback

_actions = Actions()
_logger = LogHelper.getLogger()


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
        for collection_id, collection_config in self.org_config.get(
            "collections", {}
        ).items():
            # When all actions are harmonized to watch the input directory and
            # *.zip patterns, it might make sense to refactor the watchers to
            # have one watcher per collection. This watcher would watch the input folder
            # and dispatch the file for processing in parallel by all the
            # configured actions for the collection.
            for action_name in collection_config.get("actions", {}).keys():
                self._schedule(
                    collection_id,
                    action_name,
                    ["*.zip"],
                    self.asset_helper.path_for_input(collection_id),
                )

        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            _logger.warning("Caught keyboard interrupt. Stopping FsWatcher.")
        self.observer.join()

    def _schedule(
        self, collection_id: str, action: str, patterns: list[str], path: str
    ):
        handler_class = ACTION_HANDLER.get(action)
        if handler_class is None:
            raise ValueError(f"Could not find handler class for action {action}")

        _logger.info(
            f"Scheduling handler {handler_class.__name__} for path {path} and patterns {patterns}"
        )
        self.observer.schedule(
            handler_class(patterns=patterns).with_config(
                self.org_config, collection_id
            ),
            recursive=True,
            path=path,
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


class ArchiveHandler(OrganizationHandler):
    """Handles file changes for Archive action."""

    def on_created(self, event):
        with caught_and_logged_exceptions(event):
            _actions.archive(event.src_path, self.org_config, self.collection_id)


class C2paStarlingCaptureHandler(OrganizationHandler):
    """Handles file changes for C2PA Starling Capture action."""

    def on_created(self, event):
        with caught_and_logged_exceptions(event):
            _actions.c2pa_starling_capture(
                event.src_path, self.org_config, self.collection_id
            )


class C2paProofmodeHandler(OrganizationHandler):
    """Handles file changes for C2PA Proofmode action."""

    def on_created(self, event):
        with caught_and_logged_exceptions(event):
            _actions.c2pa_proofmode(event.src_path, self.org_config, self.collection_id)


class CopyProofmodeHandler(OrganizationHandler):
    """Handles file changes for Copy Proofmode action."""

    def on_created(self, event):
        with caught_and_logged_exceptions(event):
            _actions.copy_proofmode(event.src_path, self.org_config, self.collection_id)


# class C2paAddHandler(OrganizationHandler):
#     """Handles file changes for add action."""

#     def on_created(self, event):
#         with caught_and_logged_exceptions(event):
#             _actions.c2pa_add(event.src_path, self.org_config, self.collection_id)


# class C2paUpdateHandler(OrganizationHandler):
#     """Handles file changes for update action."""

#     def on_created(self, event):
#         with caught_and_logged_exceptions(event):
#             _actions.c2pa_update(event.src_path, self.org_config, self.collection_id)


# class C2paStoreHandler(OrganizationHandler):
#     """Handles file changes for store action."""

#     def on_created(self, event):
#         with caught_and_logged_exceptions(event):
#             _actions.c2pa_store(event.src_path, self.org_config, self.collection_id)


# class C2paCustomHandler(OrganizationHandler):
#     """Handles file changes for custom action."""

#     def on_created(self, event):
#         with caught_and_logged_exceptions(event):
#             _actions.c2pa_custom(event.src_path, self.org_config, self.collection_id)


# Mapping from action name to handler class
ACTION_HANDLER = {
    "archive": ArchiveHandler,
    "c2pa-starling-capture": C2paStarlingCaptureHandler,
    "c2pa-proofmode": C2paProofmodeHandler,
    "copy-proofmode": CopyProofmodeHandler,
    # "c2pa-add": C2paAddHandler,
    # "c2pa-update": C2paUpdateHandler,
    # "c2pa-store": C2paStoreHandler,
    # "c2pa-custom": C2paCustomHandler,
}
