from __future__ import annotations

from typing import Mapping, Any, Tuple, Iterable, List

from executor.utils.controller import GraphController


class ExecutionServerException(Exception):
    pass


class ExecutionException(Exception):
    def __init__(self, message, tbs: Iterable[Tuple[int, str, str]] = ()):
        super(ExecutionException, self).__init__(message)
        self.related_exec_info = list(tbs)

    @property
    def empty(self) -> bool:
        return len(self.related_exec_info) == 0


def create_error_response(message: str) -> dict:
    return {"errors": [{"message": message}]}


def create_data_response(data: Any) -> dict:
    return {"data": data if isinstance(data, Mapping) else {"info": data}}


def execute(code: str, graph_json: str, options: Mapping = None) -> List[Mapping]:
    options = options or {}
    ctrl = GraphController(code=code, graph_data=graph_json, options=options).init()
    return ctrl.main()
