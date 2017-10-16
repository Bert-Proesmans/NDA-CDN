import argparse
import sys
import os
import time
import logging
import signal
import threading
import pathlib

from watchdog.observers import Observer

import watchdog_handling
from processors.html_handling import HTMLHandler
from upload_handler import UploadHandler

def main(logger):
    """
    Main entry point for the file watcher.

    watchdir_path: Path object of the watch directory.
    """

    logger.debug("Starting main")

    arg_parser = argparse.ArgumentParser(description="Watch a provided folder and upload files to the cloud")
    
    arg_parser.add_argument("-wd", "--watch_dir", type=str, default='',
                            help="the directory to watch filesystem events for")
    arg_parser.add_argument("-n", "--namespace", type=str, default='',
                            help="the namespace for storing files on the cloud")

    args = arg_parser.parse_args()

    # Fallback to current CWD when no path is provided.
    if args.watch_dir:
        path = args.watch_dir
    else:
        path = os.getcwd()

    namespace = args.namespace

    ##############
    # Path processing
    ###################
    abs_path = os.path.abspath(path)
    watchdir_path = pathlib.Path(abs_path)
    if watchdir_path.is_dir() is False:
        raise ValueError("Provided path is NOT a directory or doesn't exist")
    logger.info("Provided path: %s", watchdir_path.as_posix())

    #############
    # Processor setup
    ###################
    processors = [
        HTMLHandler(logger, watchdir_path)
    ]

    #############
    # Handler setup
    ###################
    upload_handler = UploadHandler(logger, 'labo-cdn.appspot.com', namespace, watchdir_path, processors)

    event_handler = watchdog_handling.FSEventHandler(logger, watchdir_path, upload_handler)
    observer = Observer()
    observer.schedule(event_handler, watchdir_path.as_posix(), recursive=True)

    ##################
    # Termination handling
    ##########################
    shutdown_observable = threading.Event()

    def termination_signal_handler(_signal, _frame):
        """
        Properly shutdown observer by catching termination signals.

        signal: OS defined enumeration of SIG* events
        """
        logger.debug("Received signal %s", _signal.name)
        # Wake main thread waiting to shutdown
        shutdown_observable.set()
        if observer is not None:
            logger.info("Interrupting observer")
            observer.stop()

    # Catch signals coming from outside the program.
    signal.signal(signal.SIGTERM, termination_signal_handler)
    signal.signal(signal.SIGINT, termination_signal_handler)

    ##########
    # FS watching 
    ####################
    observer.start()
    logger.debug("Observer started")
    # Wait until observer has finished.
    # -> Triggered by interrupt!
    try:
        # MAIN Thread MUST be kept running because of signals are only sent
        # to the main thread!
        flag = shutdown_observable.wait(1)
        while flag is False:
            flag = shutdown_observable.wait(1)
        
        # Await observer cleanup.
        observer.join()
    except Exception:
        pass

################
## MAIN entry ##
################

if __name__ == "__main__":
    ### Build logging infrastructure ###
    logging.basicConfig(level=logging.INFO,
                        #format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    ROOT_LOGGER = logging.getLogger(__name__) # Root logger
    ROOT_LOGGER.info("Logger initialised")

    try:
        main(ROOT_LOGGER)
    except Exception as error:
        ROOT_LOGGER.exception(error)

