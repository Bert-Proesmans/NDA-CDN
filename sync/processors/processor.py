
class BaseProcessor:
    def process_file(self, file_stream, orig_file_path, type_result):
        """
        Takes a bunch of parameters and processes them.

        This method returns the following tuple:  (file_stream, file_name, referenced_files)

        file_stream: The (new) file_stream for the given data. MUST not be None! Return the
        file_stream parameter if contents didn't change.

        file_name: The (new) file name for the given data. Can be None, which will instruct the
        upload handler to generate a proper filename.

        referenced_files: Iterable of pathlib.PurePath objects pointing to items which accompany
        the provided data and must be uploaded to the cloud as well. Can be None.
        """
        raise NotImplementedError