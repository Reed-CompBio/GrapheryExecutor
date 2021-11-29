import logging

__all__ = ["void_logger", "shell_debug_logger"]


def _init_void_logger():
    _logger = logging.getLogger("void")
    _logger.addHandler(logging.NullHandler())
    return _logger


void_logger = _init_void_logger()


def _init_shell_debug_logger():
    _logger = logging.getLogger("executor.shell_debug")
    _logger.setLevel(logging.DEBUG)
    _logger.addHandler(logging.StreamHandler())
    return _logger


shell_debug_logger = _init_shell_debug_logger()
