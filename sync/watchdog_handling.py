import os
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

        src_path = pathlib.Path(event.src_path).resolve()
        dest_path = pathlib.Path(event.dest_path).resolve()

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Moved %s: from %s to %s", what, src_path.as_posix(), dest_path.as_posix())

        if what == 'file':
            self.handler.remove_file(src_path)
            self.handler.queue_file_upload(dest_path)
        else:
            self.move_recursive(src_path, dest_path)

    def on_created(self, event):
        """
        event: DirCreatedEvent / FileCreatedEvent
        """
        super().on_created(event)

        src_path = pathlib.Path(event.src_path).resolve()

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Created %s: %s", what, src_path.as_posix())

        if what == 'file':
            self.handler.queue_file_upload(src_path)

    def on_deleted(self, event):
        """
        event: DirDeletedEvent / FileDeletedEvent
        """
        super().on_deleted(event)

        src_path = pathlib.Path(event.src_path).resolve()

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Deleted %s: %s", what, src_path.as_posix())

        if what == 'file':
            self.handler.remove_file(src_path)
        else:
            self.remove_recursive(src_path)

    def on_modified(self, event):
        """
        event: DirModifiedEvent / FileModifiedEvent
        """
        super().on_modified(event)

        src_path = pathlib.Path(event.src_path).resolve()

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Modified %s: %s", what, src_path.as_posix())

        if what == 'file':
            self.handler.queue_file_upload(src_path)

    def remove_recursive(self, dir_path):
        for root, dirs, files in os.walk(dir_path.as_posix()):
            for name in files:
                self.handler.remove_file(dir_path.joinpath(name))
            for dir_name in dirs:
                self.remove_recursive(dir_path.joinpath(dir_name))
    
    def move_recursive(self, src_path, target_path):
        for root, dirs, files in os.walk(src_path.as_posix()):
            for name in files:
                self.handler.remove_file(src_path.joinpath(name))
                self.handler.queue_file_upload(target_path.joinpath(name))
            for dir_name in dirs:
                self.move_recursive(src_path.joinpath(dir_name), target_path.joinpath(dir_name))