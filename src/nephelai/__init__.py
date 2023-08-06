from importlib.metadata import version  # pragma: no cover

from .api import chunked_upload, create_nc_folders, download, upload

__version__ = version(__package__)
