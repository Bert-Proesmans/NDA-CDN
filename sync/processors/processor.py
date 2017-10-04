
class BaseProcessor:
    def process_file(self, file_stream, orig_file_path, type_result):
        raise NotImplementedError