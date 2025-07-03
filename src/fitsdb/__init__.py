from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("fitsdb")
except PackageNotFoundError:
    __version__ = "unknown"
