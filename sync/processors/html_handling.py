import io
import tempfile
import pathlib
from urllib.parse import urlparse
from html.parser import HTMLParser

from .processor import BaseProcessor

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reference_paths = []

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)

        for attr in attrs:
            (tag, value) = attr
            if tag in ['href', 'src', 'src']:
                parse_result = urlparse(value)
                self.reference_paths.append(parse_result.path)


class HTMLHandler(BaseProcessor):
    """
    """
    def __init__(self, logger):
        self.logger = logger.getChild("HTMLHandler")

    def process_file(self, file_stream, orig_file_path, type_result):
        (content_type, encoding) = type_result
        if "html" not in content_type:
            self.logger.debug("Skipping non-HTML data")
            return (file_stream, orig_file_path, [])

        # Wrap file stream into text stream.
        reader = io.BufferedReader(file_stream)
        wrapper = io.TextIOWrapper(reader)
        encoding = wrapper.encoding

        # Build temporary file which contains replaced data
        temp_file = tempfile.TemporaryFile('w+b')

        # Reset all streams before operations
        wrapper.seek(0)
        temp_file.seek(0)

        # Parse all links from the html
        parser = LinkParser()        
        next_line = wrapper.readline()
        while next_line: # String is not empty
            parser.feed(next_line)
            temp_file.write(next_line.encode(encoding))
            next_line = wrapper.readline()
        
        # Process all links relative to the original path
        ref_links = []
        links = parser.reference_paths
        original_containing_path = orig_file_path.parent
        for link in links:
            self.logger.debug("Found link `%s`", link)
            path = pathlib.Path(link)
            if path.is_absolute():
                ref_links.append( (link, path) )
            else:
                resolved = pathlib.Path(original_containing_path, link)
                resolved = resolved.resolve()
                ref_links.append( (link, resolved) )
        
        # Replace all links in the temporary file
        # TODO

        # Return all processed data
        temp_file.seek(0)
        return (temp_file, None, [])
    