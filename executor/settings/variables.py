from __future__ import annotations
from os import getenv
from typing import Type, TypeVar, Protocol, ClassVar, Mapping

__all__ = ["DefaultVars", "SERVER_VERSION"]

_ENV_PREFIX = "GE_"


class VarClass(Protocol):
    vars: ClassVar[Mapping[str, ...]]

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
    LOG_CMD_OUTPUT = "LOG_CMD_OUTPUT"
    IS_DEV = "IS_DEV"
    DEFAULT_RAND_SEED = "DEFAULT_RAND_SEED"
    DEFAULT_FLOAT_PRECISION = "DEFAULT_FLOAT_PRECISION"
    IMPORT_WHITE_LIST = "IMPORT_WHITE_LIST"
    ALLOW_BUILTIN_FUNCTIONS = "ALLOW_BUILTIN_FUNCTIONS"

    vars = {
        SERVER_URL: "127.0.0.1",
        SERVER_PORT: "7590",
        ALLOW_ORIGIN: None,
        EXEC_TIME_OUT: 5,
        LOG_CMD_OUTPUT: True,
        IS_DEV: False,
        DEFAULT_RAND_SEED: 0,
        DEFAULT_FLOAT_PRECISION: 4,
        IMPORT_WHITE_LIST: [],
        ALLOW_BUILTIN_FUNCTIONS: False,
    }

    @classmethod
    def read_from_env(cls, *args, use_default: bool = False) -> None:
        for env_name in args:
            if use_default:
                setattr(cls, env_name, getenv(env_name, cls.var[env_name]))
            else:
                setattr(cls, env_name, getenv(env_name))


# Custom Variables
SERVER_VERSION = "3.0.0a0"
