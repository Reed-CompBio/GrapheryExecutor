from __future__ import annotations

import argparse
from typing import Mapping, Union, Sequence, Type

from executor.server_utils.main_functions import run_server
from executor.settings import (
    DefaultVars,
    SHELL_PARSER_GROUP_NAME,
    SHELL_SERVER_PARSER_NAME,
    SHELL_LOCAL_PARSER_NAME,
    RUNNER_ERROR_CODE,
    CTRL_ERROR_CODE,
    SERVER_VERSION,
)
from executor.utils.controller import (
    GraphController,
    ErrorResult,
)


def arg_parser(
    settings_cls: Type[DefaultVars] = DefaultVars, args: Sequence[str] = None
) -> Mapping[str, Union[int, str]]:
    parser = argparse.ArgumentParser(
        prog="graphery_executor", description="Graphery Executor Server"
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {SERVER_VERSION}"
    )

    exec_parser_group = parser.add_subparsers(
        required=True, dest=SHELL_PARSER_GROUP_NAME
    )

    # server parser
    server_parser = exec_parser_group.add_parser(SHELL_SERVER_PARSER_NAME)
    for name, (arg, kwargs) in settings_cls.server_shell_var.items():
        server_parser.add_argument(*arg, **kwargs, dest=name)

    # local parser
    _ = exec_parser_group.add_parser(SHELL_LOCAL_PARSER_NAME)

    # options for all
    for name, (arg, kwargs) in settings_cls.general_shell_var.items():
        parser.add_argument(*arg, **kwargs, dest=name)

    args: argparse.Namespace = parser.parse_args(args)
    return vars(args)


def _local_run(settings: DefaultVars) -> None:
    # This iterates over the lines of all files listed in sys.argv[1:], defaulting to sys.stdin if the list
    # is empty. If a filename is '-', it is also replaced by sys.stdin and the optional arguments mode and
    # openhook are ignored.
    logger = settings.v.LOGGER
    logger.debug(f"using logger {logger}")

    import fileinput
    import json

    input_content = fileinput.input("-").readline()
    logger.debug("got input content from stdin: " f"{input_content}")

    request_obj: Mapping = json.loads(input_content)
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
        logger.debug("local run received error result from controller main")
        ctrl.formatter.show_error(
            result.exception,
            trace=result.error_traceback,
            error_code=RUNNER_ERROR_CODE,
        )
    else:
        logger.debug("local run received valid result from controller main")
        try:
            ctrl.formatter.show_result(json.dumps(result))
        except Exception as e:
            ctrl.formatter.show_error(
                ValueError(f"Server error when handling exec result. Error: {e}"),
                error_code=CTRL_ERROR_CODE,
            )


def _server_run(settings: DefaultVars) -> None:
    run_server(settings)


def main(
    setting_cls: Type[DefaultVars] = DefaultVars, args: Sequence[str] = None
) -> None:
    args = arg_parser(setting_cls, args)
    settings = DefaultVars(**args)  # make new settings based on input

    group_name = args[SHELL_PARSER_GROUP_NAME]
    if group_name == SHELL_LOCAL_PARSER_NAME:
        _local_run(settings)
    elif group_name == SHELL_SERVER_PARSER_NAME:
        _server_run(settings)
    else:
        raise ValueError("unknown execution location")
