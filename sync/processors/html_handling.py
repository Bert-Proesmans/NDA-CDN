import io
import tempfile
import pathlib
from urllib.parse import urlparse, urlunparse
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
                self.reference_paths.append(parse_result)


class HTMLHandler(BaseProcessor):
    """
    """
    def __init__(self, logger, watch_path):
        self.logger = logger.getChild("HTMLHandler")
        self.watch_path = watch_path

    def link_within_watchdir(self, abs_item_path):
        try:
            abs_item_path.relative_to(self.watch_path)
            return True
        except ValueError:
            return False

    def process_file(self, file_stream, orig_file_path, type_result):
        (content_type, _) = type_result
        if "html" not in content_type:
            self.logger.debug("Skipping non-HTML data")
            return (file_stream, None, None)

        # Wrap file stream into text stream.
        reader = io.BufferedReader(file_stream)
        wrapper = io.TextIOWrapper(reader)

        # Build temporary file which contains replaced data
        # temp_file = tempfile.TemporaryFile('w+b')

        # Reset all streams before operations
        wrapper.seek(0)

        # Parse all links from the html
        parser = LinkParser()        
        next_line = wrapper.readline()
        while next_line: # String is not empty
            parser.feed(next_line)
            next_line = wrapper.readline()
        
        # Process all links relative to the original path
        links = parser.reference_paths
        original_containing_path = orig_file_path.parent
        referenced_items = []
        for link in links:
            self.logger.debug("Found link `%s`", urlunparse(link))
            self.logger.debug("%s", link)
            if not link.scheme or link.scheme == "file":
                path_str = link.path.strip().lstrip('/')
                path = pathlib.Path(path_str)
                if not path.is_absolute():
                    path = pathlib.Path(original_containing_path, path)

                if not path.exists():
                    self.logger.warn("No resource found at referenced location `%s`!", path.as_posix())
                    continue

                # Path MUST be an absolute version!
                if not self.link_within_watchdir(path):
                    warn_str = "Link outside watchdir: `%s` \nMove the resource inside the watchdir!"
                    self.logger.warn(warn_str, path.as_posix())
                    continue
                    
                # Store the path object as a referenced item which must be uploaded as well.
                referenced_items.append(path)
        
        # Make sure the stream is not closed after destruction of the reader
        reader.detach()
        # Reset stream to initial position
        file_stream.seek(0)
        return (file_stream, None, referenced_items)
    
