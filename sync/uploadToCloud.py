import sys
import os
import time
import logging
import signal
import threading
import mimetypes
import pathlib

from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler

# The object holding our file watcher instance.
OBSERVER = None
# Object handling logging.
LOGGER = None
# Object blocking main thread until it should shutdown.
SHUTDOWN_EVENT = None
# Object representing the cloud storage medium.
CDN_BUCKET = None
# Object for guessing the MIME type and encoding of a file.
TYPE_GUESSER = None

### Build logging infrastructure ###
logging.basicConfig(level=logging.DEBUG,
                    #format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
LOGGER = logging.getLogger(__name__) # Root logger
LOGGER.info("Logger initialised")

### Build Shutdown event ###
SHUTDOWN_EVENT = threading.Event()

def termination_signal_handler(signal, frame):
    """
    Properly shutdown observer by catching termination signals.

    signal: OS defined enumeration of SIG* events
    """
    global OBSERVER
    global LOGGER
    global SHUTDOWN_EVENT
    
    LOGGER.debug("Received signal %s", signal.name)
    # Wake main thread waiting to shutdown
    SHUTDOWN_EVENT.set()
    if OBSERVER is not None:
        LOGGER.info("Interrupting observer")
        OBSERVER.stop()

# Catch signals coming from outside the program.
signal.signal(signal.SIGTERM, termination_signal_handler)
signal.signal(signal.SIGINT, termination_signal_handler)

### Configure type guesser ###
mimetypes.init()
TYPE_GUESSER = mimetypes.MimeTypes()

#############
## Methods ##
#############

def configure_cloud_bucket():
    """
    Builds connection to google cloud.
    """
    global CDN_BUCKET
    global LOGGER

    client = storage.Client(project='labo-cdn')
    CDN_BUCKET = client.bucket('labo-cdn.appspot.com')
    
    LOGGER.info("Cloud connection succesfully setup")

    return True

def upload_file(file_path):
    """
    Uploads the given file to google cloud.
    The blob data will be overwritten if a blob with the same filename
    is already present!

    file_name: Absolute path to the file to be uploaded.
    """
    global CDN_BUCKET
    global LOGGER
    global TYPE_GUESSER

    try:
        abs_path = os.path.abspath(file_path)
        uri_path = pathlib.Path(abs_path).as_uri()
        file_name = pathlib.Path(abs_path).name
    except ValueError as error:
        LOGGER.exception(error)
        return ("", False)

    try:
        # Build new blob object
        blob = storage.Blob(file_name, CDN_BUCKET)

        # Guess content type (and encoding)
        (content_type, encoding) = TYPE_GUESSER.guess_type(uri_path)

        # Upload file.
        with open(file_name, 'rb') as file_stream: # OSError
            # Because of a lack of object versioning policies
            # the blob data will overwrite previous data for existing
            # blobs with the same filename.
            blob.upload_from_file(file_stream)
        
        # Configure file.
        if content_type:
            blob.content_type = content_type
        if encoding:
            blob.content_encoding = encoding
        blob.make_public()
        # Commit changes to the cloud.
        blob.patch()

        # Get resource url, which is a Unicode string.
        url = blob.public_url

        return (url, True)
    except GoogleCloudError as error:
        LOGGER.exception(error)
        return ("", False)

class FSEventHandler(FileSystemEventHandler):
    """
    Object responding to events coming from the observer as a 
    consequence of a filesystem change.
    """
    def __init__(self, logger):
        self.logging = logger.getChild('Watcher')
        self.expect_directory_modification = False

    def on_any_event(self, event):
        """
        event: FileSystemEvent
        """
        pass

    def on_moved(self, event):
        """
        event: DirMovedEvent / FileMovedEvent
        """
        super().on_moved(event)

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Moved %s: from %s to %s", what, event.src_path, event.dest_path)

    def on_created(self, event):
        """
        event: DirCreatedEvent / FileCreatedEvent
        """
        super().on_created(event)

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Created %s: %s", what, event.src_path)

        if what is 'file':
            (url, success) = upload_file(event.src_path)
            if success:
                self.logging.info("CDN-URL: %s", url)
            else:
                self.logging.error("Failed to upload file to CDN!")

    def on_deleted(self, event):
        """
        event: DirDeletedEvent / FileDeletedEvent
        """
        super().on_deleted(event)

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Deleted %s: %s", what, event.src_path)

    def on_modified(self, event):
        """
        event: DirModifiedEvent / FileModifiedEvent
        """
        super().on_modified(event)

        what = 'directory' if event.is_directory else 'file'
        self.logging.info("Modified %s: %s", what, event.src_path)

        if what is 'file':
            (url, success) = upload_file(event.src_path)
            if success:
                self.logging.info("CDN-URL: %s", url)
            else:
                self.logging.error("Failed to upload file to CDN!")

def main(path):
    global OBSERVER
    global LOGGER
    global SHUTDOWN_EVENT

    event_handler = FSEventHandler(LOGGER)
    OBSERVER = Observer()
    OBSERVER.schedule(event_handler, path, recursive=True)

    OBSERVER.start()
    LOGGER.debug("Observer started")
    # Wait until observer has finished.
    # -> Triggered by interrupt!
    try:
        # MAIN Thread MUST be kept running because of signals are only sent
        # to the main thread!
        flag = SHUTDOWN_EVENT.wait(1)
        while flag is False:
            flag = SHUTDOWN_EVENT.wait(1)
        
        # Await observer cleanup.
        OBSERVER.join()
    except Exception:
        pass

################
## MAIN entry ##
################

if __name__ == "__main__":
    # Fallback to current CWD when no path is provided.
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    LOGGER.debug("Target path: `%s`", path)
    try:
        if configure_cloud_bucket() is True:
            main(path)
        LOGGER.info("Finishing program")
    except Exception as error:
        LOGGER.exception(error)

