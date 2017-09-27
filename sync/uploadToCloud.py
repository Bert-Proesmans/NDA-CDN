import sys
import time
import logging
import signal
import threading

from google.cloud import storage
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler, FileSystemEventHandler

# The object holding our file watcher instance.
OBSERVER = None
# Object handling logging.
LOGGER = None
# Object blocking main thread until it should shutdown.
SHUTDOWN_EVENT = None

### Build logging infrastructure ###
logging.basicConfig(level=logging.DEBUG,
                    #format='%(asctime)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
LOGGER = logging.getLogger("Watcher")
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


#############
## Methods ##
#############

def upload_file(file_stream, filename):
    """
    Uploads the given file to google cloud.

    file_stream: 
    """
    client = storage.Client()
    bucket = client.bucket('labo-cdn.appspot.com')
    blob = bucket.blob(filename)
    success = False

    blob.upload_from_file(file_stream)
    blob.make_public()
    url = blob.public_url

    if url:
        success = True
        url = url.decode('utf-8')

    return (url, success)

class FSEventHandler(FileSystemEventHandler):
    """
    Object responding to events coming from the observer as a 
    consequence of a filesystem change.
    """
    def __init__(self, logger):
        self.logging = logger

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



# if len(sys.argv) is 2:
#     with open(sys.argv[1], 'rb') as f:
#         print(upload_file(f, sys.argv[1]))

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
        main(path)
        LOGGER.info("Finishing program")
    except Exception as error:
        LOGGER.exception(error)

