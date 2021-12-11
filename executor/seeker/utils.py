from __future__ import annotations

import abc
import datetime
import os
import re

from typing import Any, Callable, Iterable, Tuple, Type


def _check_methods(C, *methods):
    mro = C.__mro__
    for method in methods:
        for B in mro:
            if method in B.__dict__:
                if B.__dict__[method] is None:
                    return NotImplemented
                break
        else:
            return NotImplemented
    return True


class WritableStream(abc.ABC):
    @abc.abstractmethod
    def write(self, s):
        pass

    @classmethod
    def __subclasshook__(cls, C):
        if cls is WritableStream:
            return _check_methods(C, "write")
        return NotImplemented


file_reading_errors = (IOError, OSError, ValueError)  # IronPython weirdness.


def get_repr_function(
    item: Any, custom_repr: Iterable[Tuple[Type, Callable]]
) -> Callable:
    """
    get default representation function `repr` or custom representation function
    @param item: the item
    @param custom_repr: custom representation function mappings
    @return: representation function for the item
    """
    for condition, action in custom_repr:
        if isinstance(condition, type):
            t = condition

            def condition(x):
                return isinstance(x, t)

        if condition(item):
            return action
    return repr


DEFAULT_REPR_RE = re.compile(r" at 0x[a-f0-9A-F]{4,}")


def normalize_repr(item_repr):
    """
    Remove memory address (0x...) from a default python repr
    @param item_repr: the representation string of an item
    @return: normalized representation string of the item
    @deprecated: since the beginning
    """
    return DEFAULT_REPR_RE.sub("", item_repr)


def get_shortish_repr(
    item: Any,
    custom_repr: Iterable[Tuple[Type, Callable]] = (),
    max_length: int = None,
):

    repr_function: Callable = get_repr_function(item, custom_repr)
    try:
        r: str = repr_function(item)
    except Exception:
        r = "REPR FAILED"
    r = r.replace("\r", "").replace("\n", "")
    if max_length:
        r = truncate(r, max_length)
    return r


def truncate(string, max_length):
    if (max_length is None) or (len(string) <= max_length):
        return string
    else:
        left = (max_length - 3) // 2
        right = max_length - 3 - left
        return "{}...{}".format(string[:left], string[-right:])


def ensure_tuple(x):
    if isinstance(x, Iterable) and not isinstance(x, str):
        return tuple(x)
    else:
        return (x,)


def timedelta_format(timedelta):
    time = (datetime.datetime.min + timedelta).time()
    return datetime.time.isoformat(time, timespec="microseconds")


def timedelta_parse(s):
    hours, minutes, seconds, microseconds = map(int, s.replace(".", ":").split(":"))
    return datetime.timedelta(
        hours=hours, minutes=minutes, seconds=seconds, microseconds=microseconds
    )


PathLike = os.PathLike
text_type = str
