import pathlib
import queue
import mimetypes
import html

from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

from processors.processor import BaseProcessor

class UploadHandler:
    def __init__(self, logger, cdn_bucket_name, cdn_namespace, watchdir_path, processors):
        self.logger = logger.getChild('Uploader')
        self.client = None
        self.bucket = None
        self.processors = []
        self.upload_queue = queue.Queue()
        self.type_guesser = mimetypes.MimeTypes()

        assert isinstance(cdn_namespace, str), 'Namespace name MUST be a string!'
        self.namespace = cdn_namespace

        assert isinstance(watchdir_path, pathlib.PurePath), 'The watchdir argument is not a PATH object!'
        assert watchdir_path.exists(), 'The watchdir path DOES NOT point to a directory!'
        self.watchdir_path = watchdir_path

        ############
        # Initialise
        ###################
        self._setup_cloud_bucket(cdn_bucket_name)

        # Asserts the parameter can be iterated over
        assert hasattr(processors, "__iter__")
        for p in processors:
            self._register_processor(p)

    def _register_processor(self, processor):
        assert isinstance(processor, BaseProcessor), 'Given processor is not a BaseProcessor object!'
        self.processors.append(processor)

    def _setup_cloud_bucket(self, bucket_name):
        self.logger.debug("Setting up cloud bucket")
        
        assert isinstance(bucket_name, str), 'Bucket name MUST be a string!'
        self.client = storage.Client(project='labo-cdn')
        self.bucket = self.client.bucket(bucket_name)
    
        self.logger.info("Cloud connection succesfully setup")

        return True

    def get_cdn_name_exerpt(self, file_path):
        file_name_exerpt = file_path.relative_to(self.watchdir_path)
        # Build path with namespace, if provided
        file_name_exerpt = pathlib.Path(self.namespace, file_name_exerpt)
        file_name = file_name_exerpt.as_posix()
        return file_name

    def queue_file_upload(self, file_path):
        if not isinstance(file_path, pathlib.PurePath):
            raise ValueError("Provided parameter is NOT a PATH object")
        if not file_path.exists():
            self.logger.warn("File `%s` doesn't exist!", file_path.as_posix())
            
        self.upload_queue.put(file_path)
        while not self.upload_queue.empty():
            next_item = self.upload_queue.get()
            if not next_item.exists():
                continue

            # Guess file-type.
            # (content_type, encoding)
            type_result = self.type_guesser.guess_type(next_item.as_posix())
            file_name = None

            with open(next_item.as_posix(), 'rb') as file_stream_orig:
                file_stream = file_stream_orig
                # Push filename and stream through each processor
                for p in self.processors:
                    (file_stream, file_name, referenced_files) = p.process_file(file_stream, file_path, type_result)
                    if referenced_files and hasattr(referenced_files, "__iter__"):
                        for ref_path in referenced_files:
                            if not isinstance(ref_path, pathlib.PurePath):
                                self.logger.warn("A returned new file item is NOT a PATH object!")
                                continue
                            self.upload_queue.put(ref_path)

                if not file_name:
                    try:
                        # Construct item name relative to the watched path
                        file_name = self.get_cdn_name_exerpt(next_item)
                    except ValueError:
                        self.logger.warn("Found a file `%s` which is not located under the watch directory!", next_item.as_posix())

                # .. and push file to cloud
                self.logger.info("Uploading `%s` to cloud", next_item.as_posix())
                (pub_url, result) = self._upload_file(file_stream, file_name, type_result)
                if result:
                    self.logger.info("File uploaded at %s", pub_url)

    def remove_file(self, file_path):
        if not isinstance(file_path, pathlib.PurePath):
            raise ValueError("Provided parameter is NOT a PATH object")

        # Guess file-type.
        # (content_type, encoding)
        # type_result = self.type_guesser.guess_type(file_path.as_posix())
        file_name = None

        # Processors should be able to construct a cloud filename 
        # because it can be placed somewhere else than the default place.

        if not file_name:
            try:
                # Construct item name relative to the watched path
                file_name = self.get_cdn_name_exerpt(file_path)
            except ValueError:
                self.logger.warn("Found a file `%s` which is not located under the watch directory!", file_path.as_posix())

        self._remove_file(file_name)
        
    def _remove_file(self, file_name):
        blob = storage.Blob(file_name, self.bucket)
        try:
            blob.delete()
            blob.patch()
            self.logger.info("Removed `%s` from cloud", file_name)
        except GoogleCloudError:
            self.logger.error("The file `%s` wasn't found online", file_name)


    def _upload_file(self, file_stream, file_name, type_result):
        try:
            # Build new blob object
            blob = storage.Blob(file_name, self.bucket)            

            # Upload file.  
            # Because of a lack of object versioning policies
            # the blob data will overwrite previous data for existing
            # blobs with the same filename.
            blob.upload_from_file(file_stream)
            
            # Decompile content type etc.
            (content_type, encoding) = type_result
            # Configure file.
            if content_type:
                blob.content_type = content_type
            if encoding:
                blob.content_encoding = encoding
            blob.make_public()
            # Commit changes to the cloud.
            blob.patch()

            # Get resource url, which is a Unicode string.
            url = html.unescape(blob.public_url)
            return (url, True)
        except GoogleCloudError as error:
            self.logger.exception(error)
            return ("", False)
    
