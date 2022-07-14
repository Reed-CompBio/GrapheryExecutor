from __future__ import annotations

import argparse
from typing import Mapping, Union, Sequence, Type, Any, Dict

from executor.server_utils.main_functions import run_server
from executor.settings import (
    DefaultVars,
    SHELL_PARSER_GROUP_NAME,
    SHELL_SERVER_PARSER_NAME,
    SHELL_LOCAL_PARSER_NAME,
    SERVER_VERSION,
    PROG_NAME,
)
from executor.utils.controller import GraphController


def arg_parser(
    settings_cls: Type[DefaultVars] = DefaultVars, args: Sequence[str] = None
) -> Mapping[str, Union[int, str]]:
    parser = argparse.ArgumentParser(
        prog=PROG_NAME, description="Graphery Executor Server"
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

    if input_content:
        request_obj: Mapping = json.loads(input_content)
    else:
        raise ValueError(
            "got empty input content from cli reading; please check your input data"
        )

    code: str = request_obj[settings.v.REQUEST_DATA_CODE_NAME]
    logger.debug(f"parsed code {code}")

    graph: Dict = request_obj[settings.v.REQUEST_DATA_GRAPH_NAME]
    logger.debug(f"parsed graph {graph}")

    target_version: str = request_obj.get(settings.v.REQUEST_DATA_VERSION_NAME, "null")
    logger.debug(f"parsed version {target_version}")

    options: Dict[str, Any] = (
        request_obj.get(settings.v.REQUEST_DATA_OPTIONS_NAME, {}) or {}
    )
    logger.debug(f"parsed options {options}")

    options = {k.upper(): v for k, v in options.items()}
    logger.debug(f"capitalized options {options}")

    ctrl = GraphController(
        code=code,
        graph_data=graph,
        target_version=target_version,
        default_settings=settings,
        options=options,
    ).init()

    ctrl.main(formats=True, announces=True)
    logger.debug("local run received valid result from controller main")


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
