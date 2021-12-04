from __future__ import annotations

import argparse
from typing import Mapping, Union

from executor.settings import DefaultVars


def arg_parser(settings: DefaultVars = DefaultVars) -> Mapping[str, Union[int, str]]:
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


def main() -> None:
    args = arg_parser()
    print(args)
