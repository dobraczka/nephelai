from importlib.metadata import version  # pragma: no cover
from .api import create_nc_folders, chunked_upload, download, upload

__version__ = version(__package__)
