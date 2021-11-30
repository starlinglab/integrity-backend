import time  
from watchdog.observers import Observer  
from watchdog.events import PatternMatchingEventHandler

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
        observer.join()


    class Handler(PatternMatchingEventHandler):
        """Handles file changes."""
        patterns = ["*.jpg", "*.jpeg"]

        def process(self, event):
            """Processes file change event.

            Args:
                event: the file change event
            """
            print(event.src_path, event.event_type, event.is_directory)

        def on_created(self, event):
            self.process(event)

        def on_modified(self, event):
            self.process(event)

        def on_moved(self, event):
            self.process(event)

        def on_deleted(self, event):
            self.process(event)