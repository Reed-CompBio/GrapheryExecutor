from __future__ import annotations

import json
from os import getenv as _getenv
from typing import TypeVar, Protocol, ClassVar, Mapping, Tuple, Dict, Final

__all__ = [
    "VarClass",
    "DefaultVars",
    "SERVER_VERSION",
    "IDENTIFIER_SEPARATOR",
    "CTRL_ERROR_CODE",
    "INIT_ERROR_CODE",
    "PREP_ERROR_CODE",
    "POST_ERROR_CODE",
    "RUNNER_ERROR_CODE",
    "CPU_OUT_EXIT_CODE",
    "MEM_OUT_EXIT_CODE",
    "SHELL_PARSER_GROUP_NAME",
    "SHELL_SERVER_PARSER_NAME",
    "SHELL_LOCAL_PARSER_NAME",
]

from executor.utils.logger import AVAILABLE_LOGGERS, shell_info_logger

_ENV_PREFIX: Final[str] = "GE_"


# Custom Variables
SERVER_VERSION: Final[str] = "3.0.0a0"
IDENTIFIER_SEPARATOR: Final[str] = "\u200b@"

CTRL_ERROR_CODE: Final[int] = 3
INIT_ERROR_CODE: Final[int] = 5
PREP_ERROR_CODE: Final[int] = 7
POST_ERROR_CODE: Final[int] = 11
RUNNER_ERROR_CODE: Final[int] = 13
CPU_OUT_EXIT_CODE: Final[int] = 17
MEM_OUT_EXIT_CODE: Final[int] = 19

SHELL_PARSER_GROUP_NAME: Final[str] = "WHERE"
SHELL_SERVER_PARSER_NAME: Final[str] = "server"
SHELL_LOCAL_PARSER_NAME: Final[str] = "local"


# Shell Variables
class VarClass(Protocol):
    vars: ClassVar[Mapping[str, ...]]
    server_shell_var: ClassVar[Dict[str, Tuple[Tuple, Mapping]]]
    general_shell_var: ClassVar[Dict[str, Tuple[Tuple, Mapping]]]

    def __getitem__(self, item: str):
        ...

    def read_from_env(self, *args, use_default: bool = False) -> None:
        ...

    @classmethod
    def get_var_arg_name(cls, var_field: str) -> str:
        ...

    @classmethod
    def __class_getitem__(cls, item):
        ...


_T = TypeVar("_T", bound=VarClass)


class _DefaultVarsFields(Protocol):
    SERVER_URL: ClassVar[str]
    SERVER_PORT: ClassVar[str]
    ALLOW_OTHER_ORIGIN: ClassVar[str]
    ACCEPTED_ORIGINS: ClassVar[str]

    EXEC_TIME_OUT: ClassVar[str]
    EXEC_MEM_OUT: ClassVar[str]
    LOG_CMD_OUTPUT: ClassVar[str]
    IS_LOCAL: ClassVar[str]
    RAND_SEED: ClassVar[str]
    FLOAT_PRECISION: ClassVar[str]
    TARGET_VERSION: ClassVar[str]
    LOGGER: ClassVar[str]

    REQUEST_DATA_CODE_NAME: ClassVar[str]
    REQUEST_DATA_GRAPH_NAME: ClassVar[str]
    REQUEST_DATA_OPTIONS_NAME: ClassVar[str]


class _VarGetter(_DefaultVarsFields):
    def __init__(self, storage: VarClass) -> None:
        self._storage = storage

    def __getattr__(self, item):
        if item not in self._storage.vars:
            print(self._storage.vars)
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{item}'"
            )
        return self._storage[item]


class DefaultVars(_DefaultVarsFields, VarClass):
    SERVER_URL = "SERVER_URL"
    SERVER_PORT = "SERVER_PORT"
    ALLOW_OTHER_ORIGIN = "ALLOW_OTHER_ORIGIN"
    ACCEPTED_ORIGINS = "ACCEPTED_ORIGINS"

    EXEC_TIME_OUT = "EXEC_TIME_OUT"
    EXEC_MEM_OUT = "EXEC_MEM_OUT"
    LOG_CMD_OUTPUT = "LOG_CMD_OUTPUT"
    IS_LOCAL = "IS_LOCAL"
    RAND_SEED = "RAND_SEED"
    FLOAT_PRECISION = "FLOAT_PRECISION"
    TARGET_VERSION = "TARGET_VERSION"
    LOGGER = "LOGGER"

    REQUEST_DATA_CODE_NAME = "REQUEST_DATA_CODE_NAME"
    REQUEST_DATA_GRAPH_NAME = "REQUEST_DATA_GRAPH_NAME"
    REQUEST_DATA_OPTIONS_NAME = "REQUEST_DATA_OPTIONS_NAME"

    vars = {
        SERVER_URL: "127.0.0.1",
        SERVER_PORT: 7590,
        ALLOW_OTHER_ORIGIN: True,
        ACCEPTED_ORIGINS: ["127.0.0.1"],
        LOGGER: shell_info_logger,
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
            {"default": vars[ACCEPTED_ORIGINS], "action": "append"},
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
            {"default": vars[IS_LOCAL], "action": "store_true"},
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
        LOGGER: (
            ("-g", "--logger"),
            {
                "default": vars[LOGGER],
                "choices": [*AVAILABLE_LOGGERS.values()],
                "type": AVAILABLE_LOGGERS.get,
                "metavar": f"{{{', '.join(AVAILABLE_LOGGERS.keys())}}}",
            },
        ),
    }

    def __init__(self, **kwargs):
        self.vars = {**self.vars, **kwargs}
        self.read_from_env()
        self.v = _VarGetter(self)

    def __getitem__(self, item: str):
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
    def get_var_arg_name(cls, var_field: str) -> str:
        if var_field in cls.server_shell_var:
            store = cls.server_shell_var
        elif var_field in cls.general_shell_var:
            store = cls.general_shell_var
        else:
            raise ValueError(f"unknown arg name {var_field}")
        return store[var_field][0][0]

    @classmethod
    def var_arg_has_value(cls, var_field: str) -> bool:
        if var_field == cls.LOGGER:
            return False
        if var_field == cls.TARGET_VERSION:
            return False

        if var_field in cls.server_shell_var:
            store = cls.server_shell_var
        elif var_field in cls.general_shell_var:
            store = cls.general_shell_var
        else:
            raise ValueError(f"unknown arg name {var_field}")

        arg_options: Mapping = store[var_field][1]

        if arg_options.get("action", None) == "store_true":
            return False

        return True

    @classmethod
    def __class_getitem__(cls, item):
        return cls.vars[item]
