import pathlib
import html

from watchdog.events import FileSystemEventHandler

class FSEventHandler(FileSystemEventHandler):
    """
    Object responding to events coming from the observer as a 
    consequence of a filesystem change.
    """
    def __init__(self, logger, watched_path, upload_handler):
        self.logging = logger.getChild('Watcher')
        self.expect_directory_modification = False
        self.watched_path = watched_path

        assert upload_handler is not None, 'Upload handler is None!'
        self.handler = upload_handler

    def on_moved(self, event):
        """
        event: DirMovedEvent / FileMovedEvent
        """
        super().on_moved(event)

        src_path = pathlib.Path(event.src_path)
        dest_path = pathlib.Path(event.dest_path)

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Moved %s: from %s to %s", what, src_path.as_posix(), dest_path.as_posix())

        if what is 'file':
            self.handler.queue_file_upload(dest_path)

    def on_created(self, event):
        """
        event: DirCreatedEvent / FileCreatedEvent
        """
        super().on_created(event)

        target_path = pathlib.Path(event.src_path)

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Created %s: %s", what, target_path.as_posix())

        if what is 'file':
            self.handler.queue_file_upload(target_path)

    def on_deleted(self, event):
        """
        event: DirDeletedEvent / FileDeletedEvent
        """
        super().on_deleted(event)

        src_path = pathlib.Path(event.src_path)

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Deleted %s: %s", what, src_path.as_posix())

        # TODO; Use processor

    def on_modified(self, event):
        """
        event: DirModifiedEvent / FileModifiedEvent
        """
        super().on_modified(event)

        src_path = pathlib.Path(event.src_path)

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Modified %s: %s", what, src_path.as_posix())

        if what is 'file':
            self.handler.queue_file_upload(src_path)