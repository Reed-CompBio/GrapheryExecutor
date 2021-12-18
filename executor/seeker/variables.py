from __future__ import annotations

import itertools
import abc
import logging
from types import FrameType
from typing import Tuple, List, Any

from collections.abc import Mapping, Sequence
from copy import deepcopy

from . import utils


def needs_parentheses(source):
    def code(s):
        return compile(s, "<variable>", "eval").co_code

    return code(f"{source}.x") != code(f"({source}).x")


class BaseVariable(abc.ABC):
    __slots__ = ["source", "unambiguous_source", "exclude", "code"]

    def __init__(self, source, exclude=()):
        self.source = source
        self.exclude = utils.ensure_tuple(exclude)
        self.code = compile(source, "<variable>", "eval")
        if needs_parentheses(source):
            self.unambiguous_source = f"({source})"
        else:
            self.unambiguous_source = source

    def values(self, frame: FrameType):
        """
        evaluate the variable's value in a given frame
        @param frame:
        @return: the value(s) of this variable
        """
        try:
            main_value = eval(self.code, frame.f_globals or {}, frame.f_locals)
        except Exception:
            return ()

        return self._values(main_value)

    @abc.abstractmethod
    def _values(self, main_value: Any) -> List[Tuple[str, Any]]:
        """
        value helper function
        @param main_value: the evaluated value of this variable
        @return: a list of tuple mapping from string to specific evaluated values
        """
        raise NotImplementedError

    @property
    def _fingerprint(self):
        """
        The unique id for this variable
        which is a tuple containing (type, name, exclude_list)
        @return: the unique id
        """
        return type(self), self.source, self.exclude

    def __hash__(self):
        return hash(self._fingerprint)

    def __eq__(self, other):
        return (
            isinstance(other, BaseVariable) and self._fingerprint == other._fingerprint
        )


class CommonVariable(BaseVariable):
    """
    Common variable is the most common variable (?)
    It should be initialized with a string describing the variable,
    for example:

        >>>
            CommonVariable('x')
            CommonVariable("obj['attr']")
            CommonVariable('arr[0]')

    It cannot be further formatted
    """

    __slots__ = ()

    def _values(self, main_value):
        result = [(self.source, main_value)]
        for key in self._safe_keys(main_value):
            try:
                if key in self.exclude:
                    continue
                value = self._get_value(main_value, key)
            except Exception as e:
                value = None
                logging.error(
                    f"Unknown exception occurs during evaluating _values of "
                    f"key={key}, main_value={main_value}. "
                    f"Errors: {e}"
                )
            result.append(
                ("{}{}".format(self.unambiguous_source, self._format_key(key)), value)
            )
        return result

    def _safe_keys(self, main_value):
        try:
            for key in self._keys(main_value):
                yield key
        except Exception as e:
            logging.error(
                f"Unknown exception occurs during acquiring _safe_keys. " f"Errors: {e}"
            )

    def _keys(self, main_value):
        return ()

    def _format_key(self, key):
        raise NotImplementedError

    def _get_value(self, main_value, key):
        raise NotImplementedError


class Attrs(CommonVariable):
    """
    The variable instance that watches the attributes of an object
    """

    __slots__ = ()

    def _keys(self, main_value):
        return itertools.chain(
            getattr(main_value, "__dict__", ()), getattr(main_value, "__slots__", ())
        )

    def _format_key(self, key):
        return "." + key

    def _get_value(self, main_value, key):
        return getattr(main_value, key)


class Keys(CommonVariable):
    """
    The variable instance that watches the keys of a mapping
    """

    __slots__ = ()

    def _keys(self, main_value):
        return main_value.keys()

    def _format_key(self, key):
        return "[{}]".format(utils.get_shortish_repr(key))

    def _get_value(self, main_value, key):
        return main_value[key]


class Indices(Keys):
    """
    The variable instance that watches the indices of an sequence
    """

    __slots__ = ["_slice"]

    _default_slice = slice(None)

    def __init__(self, source, exclude=()):
        super().__init__(source, exclude)
        self._slice = self._default_slice

    def _keys(self, main_value):
        return range(len(main_value))[self._slice]

    def __getitem__(self, item):
        if not isinstance(item, slice):
            raise AssertionError(f"item {item} must be a slice instance")
        result = deepcopy(self)
        result._slice = item
        return result


class Exploding(BaseVariable):
    """
    Dynamic variable
    """

    __slots__ = ()

    def _values(self, main_value):
        if isinstance(main_value, Mapping):
            cls = Keys
        elif isinstance(main_value, Sequence):
            cls = Indices
        else:
            cls = Attrs

        return cls(self.source, self.exclude)._values(main_value)
