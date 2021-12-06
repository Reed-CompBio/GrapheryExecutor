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
    def __init__(self) -> None:
        self._errors = None
        self._info = None

    def format_server_result(self) -> str:
        return json.dumps({"errors": self._errors, "info": self._info})

    def add_error(self, **kwargs) -> Dict:
        error_msg = {**kwargs}
        if self._errors is None:
            self._errors = []

        if self._error_msg_checker(error_msg):
            raise ValueError("error message malformed")

        self._errors.append(error_msg)
        return error_msg

    def add_info(self, **kwargs) -> Dict:
        info_msg = {**kwargs}
        if self._info is None:
            self._info = []

        if self._info_msg_checker(info_msg):
            raise ValueError("value message malformed")

        self._info.append(info_msg)
        return info_msg

    def _error_msg_checker(self, error_msg: Dict) -> bool:
        return True

    def _info_msg_checker(self, info_msg: Dict) -> bool:
        return True
