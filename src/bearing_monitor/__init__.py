"""Bearing health monitoring on the NASA/IMS run-to-failure vibration dataset."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("bearing-monitor")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0"

__all__ = ["__version__"]
