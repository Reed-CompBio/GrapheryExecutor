from __future__ import annotations

import argparse
from typing import Mapping, Union

from executor.server_utils.main_functions import run_server
from executor.settings import DefaultVars
from executor.settings.variables import SHELL_PARSER_GROUP_NAME
from executor.utils.controller import GraphController


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
    settings = DefaultVars(**args)  # make new settings based on input

    match args[SHELL_PARSER_GROUP_NAME]:
        case 'local':
            # This iterates over the lines of all files listed in sys.argv[1:], defaulting to sys.stdin if the list
            # is empty. If a filename is '-', it is also replaced by sys.stdin and the optional arguments mode and
            # openhook are ignored.
            import fileinput
            import json
            request_obj: Mapping = json.loads(fileinput.input('-').readline())
            code = request_obj[settings.v.REQUEST_DATA_CODE_NAME]
            graph = request_obj[settings.v.REQUEST_DATA_GRAPH_NAME]
            options = request_obj.get(settings.v.REQUEST_DATA_OPTIONS_NAME, {})

            ctrl = GraphController(code=code, graph_data=graph, default_settings=settings, options=options,)

            # TODO error handling for init, main, and required args above
            try:
                ctrl.init()
            except ValueError:
                pass

            ctrl.main()

        case 'server':
            run_server(settings)
        case _:
            raise ValueError('unknown execution location')
