from __future__ import annotations

import enum
import json
from logging import Logger
from os import getenv as _getenv
from types import NoneType
from typing import (
    TypeVar,
    Protocol,
    ClassVar,
    Mapping,
    Tuple,
    Dict,
    Final,
    Sequence,
    List,
)

__all__ = [
    "VarClass",
    "DefaultVars",
    "PROG_NAME",
    "SERVER_VERSION",
    "IDENTIFIER_SEPARATOR",
    "GRAPH_INJECTION_NAME",
    "NX_GRAPH_INJECTION_NAME",
    "ErrorCode",
    "ControllerOptionNames",
    "SHELL_PARSER_GROUP_NAME",
    "SHELL_SERVER_PARSER_NAME",
    "SHELL_LOCAL_PARSER_NAME",
]

from executor.utils.logger import AVAILABLE_LOGGERS, shell_info_logger

_ENV_PREFIX: Final[str] = "GE_"


# Custom Variables
PROG_NAME: Final[str] = "graphery_executor"
SERVER_VERSION: Final[str] = "3.2.4"
IDENTIFIER_SEPARATOR: Final[str] = "\u200b@"
GRAPH_INJECTION_NAME = "graph"
NX_GRAPH_INJECTION_NAME = "g_graph"


class ErrorCode(enum.Enum):
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


class ControllerOptionNames:
    LOGGER: Final[str] = "logger"
    CUSTOM_NAMESPACE: Final[str] = "custom_ns"
    STDOUT: Final[str] = "stdout"
    STDERR: Final[str] = "stderr"
    ANNOUNCER: Final[str] = "announcer"


class _DefaultVarsFields(Protocol):
    """
    To be used in intelli scenes
    """

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
    INPUT_LIST: ClassVar[str]
    LOGGER: ClassVar[str]

    REQUEST_DATA_CODE_NAME: ClassVar[str]
    REQUEST_DATA_GRAPH_NAME: ClassVar[str]
    REQUEST_DATA_VERSION_NAME: ClassVar[str]
    REQUEST_DATA_OPTIONS_NAME: ClassVar[str]


class _VarGetter(_DefaultVarsFields):
    """
    This is a proxy of getting Vars from Var Settings
    """

    __slots__ = ["_storage"]

    def __init__(self, storage: VarClass) -> None:
        """
        :param storage: the Var Settings to be proxied
        """
        self._storage = storage

    def __getattr__(self, var_name):
        """
        Gets element of Var Settings by name
        :param var_name:
        :return:
        """
        if var_name not in self._storage.vars:
            raise AttributeError(
                f"'{self._storage.__class__.__name__}' object has no attribute '{var_name}'"
            )
        return self._storage[var_name]


def _parse_str_list(string: str) -> List[str]:
    """
    Parse a list of string from string like "['a', 'b', 'c']" or those separated by \n
    :param string: string like "['a', 'b', 'c']" or those separated by \n
    :return: a list of string
    """
    try:
        res = json.loads(string)
        if not isinstance(res, list):
            raise TypeError
        return res
    except (TypeError, json.JSONDecodeError):
        return string.split("\n")


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
    INPUT_LIST = "INPUT_LIST"
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
        INPUT_LIST: [],
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
                "default": _default_vars[RAND_SEED],
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
        INPUT_LIST: (
            ("-s", "--input-list"),
            {
                "default": _default_vars[INPUT_LIST],
                "type": _parse_str_list,
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

        # the proxy object to enable "settings.v.LOGGER"
        self.v: _VarGetter = _VarGetter(self)

    def __getitem__(self, item: str):
        return self._vars[item]

    @classmethod
    def make_shell_env_name(cls, name: str) -> str:
        """
        Makes shell variable name with variable name by adding prefix _ENV_PREFIX
        :param name: the variable name
        :return: prefixed shell variable name
        """
        return f"{_ENV_PREFIX}{name}"

    def read_from_env(self, *args, all_args: bool = False) -> None:
        """
        Reads the shell environment variables and updates the internal variables.

        :param args: The names of the variables to read.
        :param all_args: If True, all shell environment variables will be read. This will override the args parameter.
        :return: None
        """
        if all_args:
            args = self._vars.keys()

        for env_name in args:
            shell_env_name = self.make_shell_env_name(env_name)
            original = self._vars[env_name]
            # type conversions from str to the proper type
            og_type = type(original)
            if og_type is list:
                # if the type of the original is list, use json loads to parse
                og_type = _parse_str_list
            elif og_type is bool:
                # if the type of the original is bool, use custom bool parser
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
                # if the type of the original is int, then parse the string as int unless it's "none"
                def parse_int(x: str):
                    x = x.lower()
                    if x == "none":
                        return None
                    else:
                        return int(x)

                og_type = parse_int

            elif og_type is Logger:
                # if the type of the original is Logger, get the logger from the string
                og_type = AVAILABLE_LOGGERS.get
            elif og_type == NoneType:
                # if the type of the original is None, use string to parse it
                og_type = str
            # otherwise, use the original type parser to parse it (e.g. str)

            from_env = _getenv(shell_env_name, None)
            if from_env is not None:
                self._vars[env_name] = og_type(from_env)

    @classmethod
    def get_var_arg_name(cls, var_field: str) -> str:
        """
        Gets the argument name for a variable. (e.g. -s for input_list)
        :param var_field: the variable field name
        :return: the argument name
        """
        if var_field in cls.server_shell_var:
            # use the server shell var if the var is in the server shell var list
            store = cls.server_shell_var
        elif var_field in cls.general_shell_var:
            # use the general shell var if the var is in the general shell var list
            store = cls.general_shell_var
        else:
            raise ValueError(f"unknown arg name {var_field}")
        # get the arg name from the store
        return store[var_field][0][0]

    @classmethod
    def var_arg_has_value(cls, var_field: str) -> bool:
        """
        Checks if the variable has a value. (e.g. -l for --logger doesn't have a value)
        :param var_field: the variable field name
        :return: indicates if the variable has a value
        """
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
        """
        Gets the default value of a variable name.
        :param item: the variable name (e.g. cls.INPUT_LIST)
        :return: the default value for that variable
        """
        return cls._default_vars[item]

    @property
    def vars(self) -> Mapping[str, ...]:
        """
        Get the variable storage dictionary
        :return:
        """
        return self._vars
