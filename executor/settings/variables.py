from __future__ import annotations

import json
from os import getenv as _getenv
from typing import TypeVar, Protocol, ClassVar, Mapping, Tuple, Dict

__all__ = [
    "VarClass",
    "DefaultVars",
    "SERVER_VERSION",
    "IDENTIFIER_SEPARATOR",
    "RUNNER_ERROR_CODE",
    "CPU_OUT_EXIT_CODE",
    "MEM_OUT_EXIT_CODE",
]

_ENV_PREFIX = "GE_"


# Custom Variables
SERVER_VERSION = "3.0.0a0"
IDENTIFIER_SEPARATOR = "\u200b@"

RUNNER_ERROR_CODE = 13
CPU_OUT_EXIT_CODE = 17
MEM_OUT_EXIT_CODE = 19


# Shell Variables
class VarClass(Protocol):
    vars: ClassVar[Mapping[str, ...]]
    server_shell_var: ClassVar[Dict[str, Tuple[Tuple, Mapping]]]
    general_shell_var: ClassVar[Dict[str, Tuple[Tuple, Mapping]]]

    def read_from_env(self, *args, use_default: bool = False) -> None:
        ...


_T = TypeVar("_T", bound=VarClass)


class DefaultVars(VarClass):
    SERVER_URL = "SERVER_URL"
    SERVER_PORT = "SERVE_PORT"
    ALLOW_OTHER_ORIGIN = "ALLOW_OTHER_ORIGIN"
    ACCEPTED_ORIGINS = "ACCEPTED_ORIGINS"

    EXEC_TIME_OUT = "EXEC_TIME_OUT"
    EXEC_MEM_OUT = "EXEC_MEM_OUT"
    LOG_CMD_OUTPUT = "LOG_CMD_OUTPUT"
    IS_LOCAL = "IS_LOCAL"
    RAND_SEED = "RAND_SEED"
    FLOAT_PRECISION = "FLOAT_PRECISION"
    TARGET_VERSION = "TARGET_VERSION"

    REQUEST_DATA_CODE_NAME = "REQUEST_DATA_CODE_NAME"
    REQUEST_DATA_GRAPH_NAME = "REQUEST_DATA_GRAPH_NAME"
    REQUEST_DATA_OPTIONS_NAME = "REQUEST_DATA_OPTIONS_NAME"

    vars = {
        SERVER_URL: "127.0.0.1",
        SERVER_PORT: 7590,
        ALLOW_OTHER_ORIGIN: True,
        ACCEPTED_ORIGINS: ["127.0.0.1"],
        #
        EXEC_TIME_OUT: 5,
        EXEC_MEM_OUT: 100,
        LOG_CMD_OUTPUT: True,
        IS_LOCAL: False,
        RAND_SEED: 0,
        FLOAT_PRECISION: 4,
        TARGET_VERSION: None,
        #
        REQUEST_DATA_CODE_NAME: "code",
        REQUEST_DATA_GRAPH_NAME: "graph",
        REQUEST_DATA_OPTIONS_NAME: "options",
    }

    server_shell_var = {
        SERVER_URL: (
            ("-u", "--url"),
            {
                "default": vars[SERVER_URL],
                "type": str,
                "help": "The url the local server will run on",
            },
        ),
        SERVER_PORT: (
            ("-p", "--port"),
            {
                "default": vars[SERVER_PORT],
                "type": int,
                "help": "The port the local server will run on",
            },
        ),
        ALLOW_OTHER_ORIGIN: (
            ("--allow-origin",),
            {"default": vars[ALLOW_OTHER_ORIGIN], "action": "store_true"},
        ),
        ACCEPTED_ORIGINS: (
            ("-o", "--origin"),
            {"default": vars[ALLOW_OTHER_ORIGIN], "action": "append"},
        ),
    }
    general_shell_var = {
        LOG_CMD_OUTPUT: (
            ("-l", "--log-out"),
            {"default": vars[LOG_CMD_OUTPUT], "action": "store_true"},
        ),
        EXEC_TIME_OUT: (
            ("-t", "--time-out"),
            {
                "default": vars[EXEC_TIME_OUT],
                "type": int,
            },
        ),
        EXEC_MEM_OUT: (
            ("-m", "--mem-out"),
            {
                "default": vars[EXEC_MEM_OUT],
                "type": int,
            },
        ),
        IS_LOCAL: (
            ("--local",),
            {
                "default": vars[IS_LOCAL],
                "type": bool,
            },
        ),
        RAND_SEED: (
            ("-s", "--rand-seed"),
            {
                "default": str(vars[RAND_SEED]),
                "type": lambda x: None if x.strip() == "None" else int(x),
            },
        ),
        FLOAT_PRECISION: (
            ("--float-precision",),
            {
                "default": vars[FLOAT_PRECISION],
                "type": int,
            },
        ),
        TARGET_VERSION: (
            ("-v", "--target-version"),
            {"default": vars[TARGET_VERSION], "type": str},
        ),
    }

    def __init__(self, **kwargs):
        self.vars = {**self.vars, **kwargs}
        self.read_from_env()

    def __getitem__(self, item):
        return self.vars[item]

    def read_from_env(self, *args, all_arg: bool = False) -> None:
        if all_arg:
            args = self.vars.keys()

        for env_name in args:
            shell_env_name = f"{_ENV_PREFIX}{env_name}"
            original = self.vars[env_name]
            # type conversions from str to the proper type
            og_type = type(original)
            if og_type is list:
                og_type = json.loads

            self.vars[env_name] = og_type(_getenv(shell_env_name, original))

    @classmethod
    def __class_getitem__(cls, item):
        return cls.vars[item]
