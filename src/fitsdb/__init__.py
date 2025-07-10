from importlib.metadata import PackageNotFoundError, version
from main import index_folder as index

try:
    __version__ = version("fitsdb")
except PackageNotFoundError:
    __version__ = "unknown"
