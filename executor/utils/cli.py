from __future__ import annotations

import argparse
from typing import Mapping, Union

from executor.settings import DefaultVars
from executor.settings.variables import SHELL_PARSER_GROUP_NAME


def arg_parser(settings: DefaultVars = DefaultVars) -> Mapping[str, Union[int, str]]:
    parser = argparse.ArgumentParser(
        prog="graphery_executor", description="Graphery Executor Server"
    )
    exec_parser_group = parser.add_subparsers(
        required=True, dest=SHELL_PARSER_GROUP_NAME
    )

    # server parser
    server_parser = exec_parser_group.add_parser("server")
    for name, (arg, kwargs) in settings.server_shell_var.items():
        server_parser.add_argument(*arg, **kwargs, dest=name)

    # local parser
    _ = exec_parser_group.add_parser("local")

    # options for all
    for name, (arg, kwargs) in settings.general_shell_var.items():
        parser.add_argument(*arg, **kwargs, dest=name)

    args: argparse.Namespace = parser.parse_args()
    return vars(args)


def main() -> None:
    args = arg_parser()
    print(args)
    # TODO cli main
    # use fileinput on WHERE=local
    # fileinput.input
    # This iterates over the lines of all files listed in sys.argv[1:], defaulting to sys.stdin if the list is empty.
    # If a filename is '-', it is also replaced by sys.stdin and the optional arguments mode and openhook are
    # ignored. To specify an alternative list of filenames, pass it as the first argument to input(). A single file
    # name is also allowed.
    #
    # otherwise run server main
