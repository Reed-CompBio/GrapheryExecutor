from __future__ import annotations

import argparse
from typing import Mapping, Any, Union, Tuple, Iterable, List

from networkx import Graph
from ..settings import VarClass, DefaultVars


class ExecutionServerException(Exception):
    pass


class ExecutionException(Exception):
    def __init__(self, message, tbs: Iterable[Tuple[int, str, str]] = ()):
        super(ExecutionException, self).__init__(message)
        self.related_exec_info = list(tbs)

    @property
    def empty(self) -> bool:
        return len(self.related_exec_info) == 0


def arg_parser(settings: VarClass = DefaultVars) -> Mapping[str, Union[int, str]]:
    parser = argparse.ArgumentParser(
        prog="graphery_executor", description="Graphery Executor Server"
    )
    exec_parser_group = parser.add_subparsers(required=True)

    # server parser
    server_parser = exec_parser_group.add_parser("server")
    for arg, kwargs in settings.server_shell_var.values():
        server_parser.add_argument(*arg, **kwargs)

    # local parser
    local_parser = exec_parser_group.add_parser("local")
    local_parser.add_argument("code")
    local_parser.add_argument("graph")

    # options for all
    for arg, kwargs in settings.general_shell_var.values():
        parser.add_argument(*arg, **kwargs)

    args: argparse.Namespace = parser.parse_args()
    return vars(args)


def create_error_response(message: str) -> dict:
    return {"errors": [{"message": message}]}


def create_data_response(data: Any) -> dict:
    return {"data": data if isinstance(data, Mapping) else {"info": data}}


def execute(
    code: str, graph_json: Union[str, Mapping], auto_delete_cache: bool = False
) -> Tuple[str, List[Mapping]]:
    pass
