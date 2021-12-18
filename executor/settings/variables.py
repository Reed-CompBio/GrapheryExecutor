from __future__ import annotations

import json
from logging import Logger
from os import getenv as _getenv
from types import NoneType
from typing import TypeVar, Protocol, ClassVar, Mapping, Tuple, Dict, Final, Sequence

__all__ = [
    "VarClass",
    "DefaultVars",
    "PROG_NAME",
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
PROG_NAME: Final[str] = "graphery_executor"
SERVER_VERSION: Final[str] = "3.0.0"
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
    __slots__: Sequence = ()

    _vars: ClassVar[Mapping[str, ...]]
    server_shell_var: ClassVar[Dict[str, Tuple[Tuple, Mapping]]]
    general_shell_var: ClassVar[Dict[str, Tuple[Tuple, Mapping]]]

    _vars: Dict[str, ...]
    v: _VarGetter

    @property
    def vars(self) -> Mapping[str, ...]:
        raise NotImplementedError

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
    __slots__: Sequence = ()

    SERVER_URL: ClassVar[str]
    SERVER_PORT: ClassVar[str]
    ALLOW_OTHER_ORIGIN: ClassVar[str]
    ACCEPTED_ORIGINS: ClassVar[str]

    EXEC_TIME_OUT: ClassVar[str]
    EXEC_MEM_OUT: ClassVar[str]
    IS_LOCAL: ClassVar[str]
    RAND_SEED: ClassVar[str]
    FLOAT_PRECISION: ClassVar[str]
    LOGGER: ClassVar[str]

    REQUEST_DATA_CODE_NAME: ClassVar[str]
    REQUEST_DATA_GRAPH_NAME: ClassVar[str]
    REQUEST_DATA_VERSION_NAME: ClassVar[str]
    REQUEST_DATA_OPTIONS_NAME: ClassVar[str]


class _VarGetter(_DefaultVarsFields):
    __slots__ = ["_storage"]

    def __init__(self, storage: VarClass) -> None:
        self._storage = storage

    def __getattr__(self, item):
        if item not in self._storage.vars:
            raise AttributeError(
                f"'{self._storage.__class__.__name__}' object has no attribute '{item}'"
            )
        return self._storage[item]


class DefaultVars(_DefaultVarsFields, VarClass):
    __slots__ = ["_vars", "v"]

    SERVER_URL = "SERVER_URL"
    SERVER_PORT = "SERVER_PORT"
    ALLOW_OTHER_ORIGIN = "ALLOW_OTHER_ORIGIN"
    ACCEPTED_ORIGINS = "ACCEPTED_ORIGINS"

    EXEC_TIME_OUT = "EXEC_TIME_OUT"
    EXEC_MEM_OUT = "EXEC_MEM_OUT"
    IS_LOCAL = "IS_LOCAL"
    RAND_SEED = "RAND_SEED"
    FLOAT_PRECISION = "FLOAT_PRECISION"
    LOGGER = "LOGGER"

    REQUEST_DATA_CODE_NAME = "REQUEST_DATA_CODE_NAME"
    REQUEST_DATA_GRAPH_NAME = "REQUEST_DATA_GRAPH_NAME"
    REQUEST_DATA_VERSION_NAME = "REQUEST_DATA_VERSION_NAME"
    REQUEST_DATA_OPTIONS_NAME = "REQUEST_DATA_OPTIONS_NAME"

    _default_vars = {
        SERVER_URL: "127.0.0.1",
        SERVER_PORT: 7590,
        ALLOW_OTHER_ORIGIN: True,
        ACCEPTED_ORIGINS: ["127.0.0.1"],
        LOGGER: shell_info_logger,
        #
        EXEC_TIME_OUT: 5,
        EXEC_MEM_OUT: 100,
        IS_LOCAL: False,
        RAND_SEED: 0,
        FLOAT_PRECISION: 4,
        #
        REQUEST_DATA_CODE_NAME: "code",
        REQUEST_DATA_GRAPH_NAME: "graph",
        REQUEST_DATA_VERSION_NAME: "version",
        REQUEST_DATA_OPTIONS_NAME: "options",
    }

    server_shell_var = {
        SERVER_URL: (
            ("-u", "--url"),
            {
                "default": _default_vars[SERVER_URL],
                "type": str,
                "help": "The url the local server will run on",
            },
        ),
        SERVER_PORT: (
            ("-p", "--port"),
            {
                "default": _default_vars[SERVER_PORT],
                "type": int,
                "help": "The port the local server will run on",
            },
        ),
        ALLOW_OTHER_ORIGIN: (
            ("-a", "--allow-origin"),
            {"default": _default_vars[ALLOW_OTHER_ORIGIN], "action": "store_true"},
        ),
        ACCEPTED_ORIGINS: (
            ("-o", "--origin"),
            {
                "default": _default_vars[ACCEPTED_ORIGINS],
                "action": "extend",
                "nargs": "+",
                "type": str,
            },
        ),
    }
    general_shell_var = {
        EXEC_TIME_OUT: (
            ("-t", "--time-out"),
            {
                "default": _default_vars[EXEC_TIME_OUT],
                "type": int,
            },
        ),
        EXEC_MEM_OUT: (
            ("-m", "--mem-out"),
            {
                "default": _default_vars[EXEC_MEM_OUT],
                "type": int,
            },
        ),
        IS_LOCAL: (
            ("-i", "--is-local"),
            {"default": _default_vars[IS_LOCAL], "action": "store_true"},
        ),
        RAND_SEED: (
            ("-r", "--rand-seed"),
            {
                "default": str(_default_vars[RAND_SEED]),
                "type": lambda x: None if x.strip() == "None" else int(x),
            },
        ),
        FLOAT_PRECISION: (
            ("-f", "--float-precision"),
            {
                "default": _default_vars[FLOAT_PRECISION],
                "type": int,
            },
        ),
        LOGGER: (
            ("-l", "--logger"),
            {
                "default": _default_vars[LOGGER],
                "choices": [*AVAILABLE_LOGGERS.values()],
                "type": AVAILABLE_LOGGERS.get,
                "metavar": f"{{{', '.join(AVAILABLE_LOGGERS.keys())}}}",
            },
        ),
    }

    def __init__(self, **kwargs):
        self._vars: Dict = {**self._default_vars, **kwargs}
        self.read_from_env(all_args=True)
        self.v = _VarGetter(self)

    def __getitem__(self, item: str):
        return self._vars[item]

    @classmethod
    def make_shell_env_name(cls, name: str) -> str:
        return f"{_ENV_PREFIX}{name}"

    def read_from_env(self, *args, all_args: bool = False) -> None:
        if all_args:
            args = self._vars.keys()

        for env_name in args:
            shell_env_name = self.make_shell_env_name(env_name)
            original = self._vars[env_name]
            # type conversions from str to the proper type
            og_type = type(original)
            if og_type is list:
                og_type = json.loads
            elif og_type is bool:

                def parse_bool(x: str):
                    x = x.lower()
                    if x == "true" or x == "t":
                        return True
                    elif x == "false" or x == "f":
                        return False
                    else:
                        return bool(x)

                og_type = parse_bool
            elif og_type is int:

                def parse_int(x: str):
                    x = x.lower()
                    if x == "none":
                        return None
                    else:
                        return int(x)

                og_type = parse_int

            elif og_type is Logger:
                og_type = AVAILABLE_LOGGERS.get
            elif og_type == NoneType:
                og_type = str

            from_env = _getenv(shell_env_name, None)
            if from_env is not None:
                self._vars[env_name] = og_type(from_env)

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
        return cls._default_vars[item]

    @property
    def vars(self) -> Mapping[str, ...]:
        return self._vars
