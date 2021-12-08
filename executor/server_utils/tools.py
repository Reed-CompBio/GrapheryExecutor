from __future__ import annotations

from typing import Dict
import json


class ExecutionError(ValueError):
    def __init__(self, msg: str, traceback: str = None):
        super(ExecutionError, self).__init__(msg)
        self.traceback = traceback


class ArgumentError(ValueError):
    pass


class ServerError(Exception):
    pass


class ServerResultFormatter:
    def __init__(self, logger) -> None:
        self._errors = None
        self._info = None
        self._logger = logger

    def format_server_result(self) -> str:
        return json.dumps({"errors": self._errors, "info": self._info})

    def add_error(self, **kwargs) -> Dict:
        error_msg = {**kwargs}
        if self._errors is None:
            self._errors = []

        if not self._error_msg_valid(error_msg):
            raise ValueError("error message malformed")

        self._logger.info("added error: \n" f"{error_msg}")

        self._errors.append(error_msg)
        return error_msg

    def add_info(self, **kwargs) -> Dict:
        info_msg = {**kwargs}
        if self._info is None:
            self._info = []

        if not self._info_msg_valid(info_msg):
            raise ValueError("value message malformed")

        self._logger.info("added info: \n" f"{info_msg}")

        self._info.append(info_msg)
        return info_msg

    def _error_msg_valid(self, error_msg: Dict) -> bool:
        # TODO err msg validator
        return True

    def _info_msg_valid(self, info_msg: Dict) -> bool:
        # TODO info msg validator
        return True
