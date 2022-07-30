from __future__ import annotations

__all__ = ["VarClass", "VarDict", "VarFieldNames"]

from logging import Logger
from typing import (
    TypedDict,
    List,
    TypeVar,
    Dict,
    Protocol,
    Sequence,
    ClassVar,
    Tuple,
    Mapping,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    # noinspection PyProtectedMember
    from .variables import _VarGetter


class VarDict(TypedDict):
    # TODO: wait for 3.11 https://peps.python.org/pep-0655/
    SERVER_URL: str
    SERVER_PORT: int
    ALLOW_OTHER_ORIGIN: bool
    ACCEPTED_ORIGINS: List[str]

    EXEC_TIME_OUT: int
    EXEC_MEM_OUT: int
    IS_LOCAL: bool
    RAND_SEED: int
    FLOAT_PRECISION: int
    INPUT_LIST: List[str]
    LOGGER: Logger

    REQUEST_DATA_CODE_NAME: str
    REQUEST_DATA_GRAPH_NAME: str
    REQUEST_DATA_VERSION_NAME: str
    REQUEST_DATA_OPTIONS_NAME: str


_VarProtocol = TypeVar("_VarProtocol", bound=Dict)


class VarFieldNames(Protocol[_VarProtocol]):
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


# Shell Variables
class VarClass(Protocol[_VarProtocol]):
    __slots__: Sequence = ()

    _vars: _VarProtocol
    _default_vars: ClassVar[_VarProtocol]
    server_shell_var: ClassVar[Dict[str, Tuple[Tuple, Mapping]]]
    general_shell_var: ClassVar[Dict[str, Tuple[Tuple, Mapping]]]

    v: "_VarGetter"

    @property
    def vars(self) -> _VarProtocol:
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
