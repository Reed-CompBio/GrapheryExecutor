from __future__ import annotations
from os import getenv
from typing import Type, TypeVar, Protocol, ClassVar, Mapping, Tuple, Dict

__all__ = ["DefaultVars", "SERVER_VERSION", "IDENTIFIER_SEPARATOR"]

_ENV_PREFIX = "GE_"


class VarClass(Protocol):
    vars: ClassVar[Mapping[str, ...]]
    server_shell_var: ClassVar[Dict[str, Tuple[Tuple, Mapping]]]
    local_shell_var: ClassVar[Dict[str, Tuple[Tuple, Mapping]]]

    @classmethod
    def read_from_env(cls, *args, use_default: bool = False) -> None:
        ...


_T = TypeVar("_T", bound=VarClass)


def _add_shell_env(cls: Type[_T]) -> Type[_T]:
    added = {
        f"{_ENV_PREFIX}{k}": f"{_ENV_PREFIX}{v}"
        for k, v in cls.__dict__.items()
        if k.isupper() and not k.startswith(_ENV_PREFIX)
    }

    for k, v in added.items():
        setattr(cls, k, v)
    return cls


# Environment Variables
@_add_shell_env
class DefaultVars(VarClass):
    SERVER_URL = "SERVER_URL"
    SERVER_PORT = "SERVE_PORT"
    ALLOW_ORIGIN = "ALLOWED_ORIGIN"
    EXEC_TIME_OUT = "EXEC_TIME_OUT"
    EXEC_MEM_OUT = "EXEC_MEM_OUT"
    LOG_CMD_OUTPUT = "LOG_CMD_OUTPUT"
    IS_DEV = "IS_DEV"
    DEFAULT_RAND_SEED = "DEFAULT_RAND_SEED"
    DEFAULT_FLOAT_PRECISION = "DEFAULT_FLOAT_PRECISION"
    ALLOW_BUILTIN_FUNCTIONS = "ALLOW_BUILTIN_FUNCTIONS"

    vars = {
        SERVER_URL: "127.0.0.1",
        SERVER_PORT: "7590",
        ALLOW_ORIGIN: False,
        EXEC_TIME_OUT: 5,
        EXEC_MEM_OUT: 100,
        LOG_CMD_OUTPUT: True,
        IS_DEV: False,
        DEFAULT_RAND_SEED: 0,
        DEFAULT_FLOAT_PRECISION: 4,
        ALLOW_BUILTIN_FUNCTIONS: False,
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
    }
    local_shell_var = {}

    @classmethod
    def read_from_env(
        cls, *args, use_default: bool = False, all_arg: bool = False
    ) -> None:
        if all_arg:
            args = cls.vars.keys()

        for env_name in args:
            original = cls.vars[env_name]
            # type conversions from str to the proper type
            og_type = type(original)

            if use_default:
                cls.vars[env_name] = og_type(getenv(env_name, original))
            else:
                cls.vars[env_name] = og_type(getenv(env_name))

    @classmethod
    def __class_getitem__(cls, item):
        return cls.vars[item]


# Custom Variables
SERVER_VERSION = "3.0.0a0"
IDENTIFIER_SEPARATOR = "\u200b@"
