from __future__ import annotations
import logging

__all__ = [
    "AVAILABLE_LOGGERS",
    "void_logger",
    "shell_debug_logger",
    "shell_info_logger",
]

from typing import Final, Dict

_LOGGER_ROOT_NAME: Final[str] = "executor"
_ROOT_LOGGER: Final[logging.Logger] = logging.getLogger(_LOGGER_ROOT_NAME)

_stream_handler: logging.StreamHandler = logging.StreamHandler()
_full_formatter: logging.Formatter = logging.Formatter(
    "%(asctime)s - %(filename)s - %(levelname)s - %(message)s"
)
_stream_handler.setFormatter(_full_formatter)

AVAILABLE_LOGGERS: Final[Dict] = {}


def _get_logger(name: str) -> logging.Logger:
    AVAILABLE_LOGGERS[name] = logging.getLogger(f"{_LOGGER_ROOT_NAME}.{name}")
    return AVAILABLE_LOGGERS[name]


def _init_void_logger() -> logging.Logger:
    _logger = _get_logger("void")
    _logger.addHandler(logging.NullHandler())
    return _logger


void_logger = _init_void_logger()


def _init_shell_debug_logger() -> logging.Logger:
    _logger = _get_logger("shell_debug")
    _logger.setLevel(logging.DEBUG)
    _logger.addHandler(_stream_handler)
    return _logger


shell_debug_logger = _init_shell_debug_logger()


def _init_shell_info_logger() -> logging.Logger:
    _logger = _get_logger("shell_info")
    _logger.setLevel(logging.INFO)
    _logger.addHandler(_stream_handler)
    return _logger


shell_info_logger = _init_shell_info_logger()
