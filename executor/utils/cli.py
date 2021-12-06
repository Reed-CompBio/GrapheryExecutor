from __future__ import annotations

import argparse
from typing import Mapping, Union

from executor.server_utils.main_functions import run_server
from executor.settings import DefaultVars
from executor.settings.variables import (
    SHELL_PARSER_GROUP_NAME,
    SHELL_SERVER_PARSER_NAME,
    SHELL_LOCAL_PARSER_NAME,
    RUNNER_ERROR_CODE,
    CTRL_ERROR_CODE,
)
from executor.utils.controller import (
    GraphController,
    ControllerResultFormatter,
    ErrorResult,
)


def arg_parser(settings: DefaultVars = DefaultVars) -> Mapping[str, Union[int, str]]:
    parser = argparse.ArgumentParser(
        prog="graphery_executor", description="Graphery Executor Server"
    )
    exec_parser_group = parser.add_subparsers(
        required=True, dest=SHELL_PARSER_GROUP_NAME
    )

    # server parser
    server_parser = exec_parser_group.add_parser(SHELL_SERVER_PARSER_NAME)
    for name, (arg, kwargs) in settings.server_shell_var.items():
        server_parser.add_argument(*arg, **kwargs, dest=name)

    # local parser
    _ = exec_parser_group.add_parser(SHELL_LOCAL_PARSER_NAME)

    # options for all
    for name, (arg, kwargs) in settings.general_shell_var.items():
        parser.add_argument(*arg, **kwargs, dest=name)

    args: argparse.Namespace = parser.parse_args()
    return vars(args)


def main() -> None:
    args = arg_parser()
    settings = DefaultVars(**args)  # make new settings based on input

    group_name = args[SHELL_PARSER_GROUP_NAME]
    if group_name == SHELL_LOCAL_PARSER_NAME:
        # This iterates over the lines of all files listed in sys.argv[1:], defaulting to sys.stdin if the list
        # is empty. If a filename is '-', it is also replaced by sys.stdin and the optional arguments mode and
        # openhook are ignored.
        import fileinput
        import json

        request_obj: Mapping = json.loads(fileinput.input("-").readline())
        code = request_obj[settings.v.REQUEST_DATA_CODE_NAME]
        graph = request_obj[settings.v.REQUEST_DATA_GRAPH_NAME]
        options = request_obj.get(settings.v.REQUEST_DATA_OPTIONS_NAME, {})

        ctrl = GraphController(
            code=code,
            graph_data=graph,
            default_settings=settings,
            options=options,
        ).init()

        result = ctrl.main()

        if isinstance(result, ErrorResult):
            # Ehhh ugly
            ControllerResultFormatter.show_error(
                result.exception,
                trace=result.error_traceback,
                error_code=RUNNER_ERROR_CODE,
            )

        try:
            ControllerResultFormatter.show_result(json.dumps(result))
        except Exception as e:
            ControllerResultFormatter.show_error(
                ValueError(f"Server error when handling exec result. Error: {e}"),
                error_code=CTRL_ERROR_CODE,
            )

    elif group_name == SHELL_SERVER_PARSER_NAME:
        run_server(settings)
    else:
        raise ValueError("unknown execution location")
