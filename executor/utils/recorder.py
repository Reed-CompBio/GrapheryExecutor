from __future__ import annotations

import json
import random
from copy import copy, deepcopy
from io import StringIO
from logging import Logger
from numbers import Number
from typing import (
    Sequence,
    List,
    Tuple,
    Deque,
    Set,
    Counter,
    Mapping,
    MutableMapping,
    Any,
    Dict,
    Union,
)

from networkx import (
    Node,
    is_node,
    Edge,
    is_edge,
    DataEdge,
    is_data_edge,
    MultiEdge,
    is_multi_edge,
    DataMultiEdge,
    is_data_multi_edge,
    Graph,
)
from .cytoscape_helper import get_cytoscape_id
from .logger import void_logger
from ..settings import IDENTIFIER_SEPARATOR


__all__ = ["Recorder", "identifier_to_string"]


def identifier_to_string(identifier: Sequence[str]) -> str:
    return IDENTIFIER_SEPARATOR.join(identifier)


# used to fix color generation
_color_r = random.Random(0)


def generate_hex() -> str:
    random_number = _color_r.randint(0, 0xFFFFFF)
    hex_number = str(hex(random_number))
    return "#" + hex_number[2:]


class Recorder:
    """check out RFC for more detail"""

    _DEFAULT_COLOR_PALETTE = [
        "#828282",
        "#B15928",
        "#A6CEE3",
        "#1F78B4",
        "#B2DF8A",
        "#33A02C",
        "#FB9A99",
        "#E31A1C",
        "#FDBF6F",
        "#FF7F00",
        "#CAB2D6",
        "#6A3D9A",
        "#FFFF99",
    ]

    _ACCESSED_IDENTIFIER = ("global", "accessed var")
    _ACCESSED_IDENTIFIER_STRING = identifier_to_string(_ACCESSED_IDENTIFIER)

    _INNER_IDENTIFIER = ("", "\u200b{}".format("inner"))
    _INNER_IDENTIFIER_STRING = identifier_to_string(_INNER_IDENTIFIER)

    _DEFAULT_COLOR_MAPPING = {
        _INNER_IDENTIFIER_STRING: _DEFAULT_COLOR_PALETTE[0],
        _ACCESSED_IDENTIFIER_STRING: _DEFAULT_COLOR_PALETTE[1],
    }

    _GRAPH_OBJECT_MAPPING = {
        is_node: Node.graphery_type_flag,
        is_edge: Edge.graphery_type_flag,
        is_data_edge: DataEdge.graphery_type_flag,
        is_multi_edge: MultiEdge.graphery_type_flag,
        is_data_multi_edge: DataMultiEdge.graphery_type_flag,
    }

    _SINGULAR_MAPPING = {
        Number: "Number",
        str: "String",
        type(None): "None",
    }

    _LINEAR_CONTAINER_MAPPING = {
        List: "List",
        Tuple: "Tuple",
        Deque: "Deque",
        Set: "Set",  # which includes Set, set, KeyView(dict_keys), ValueView(dict_values), ItemView(dict_items),
        # frozenset, MutableSet
        # ElementSet: 'ElementSet', # removed in new api
        Sequence: "Sequence",  # which includes tuple, str, range, memoryview, MutableSequence, list, bytearray
    }

    _PAIR_CONTAINER_MAPPING = {
        Counter: "Counter",
        Mapping: "Mapping",  # which includes mappingproxy (not sure what that is), MutableMapping, dict
    }

    _OBJECT_TYPE_STRING = "Object"

    _TYPE_MAPPING = {
        # simple individuals
        **_SINGULAR_MAPPING,
        # simple linear containers
        **_LINEAR_CONTAINER_MAPPING,
        # simple pair containers
        **_PAIR_CONTAINER_MAPPING,
        # wildcard
        object: _OBJECT_TYPE_STRING,
    }

    INIT_TYPE_STRING = "init"
    REFERENCE_TYPE_STRING = "reference"

    _GRAPH_OBJECT_TYPES = set(_GRAPH_OBJECT_MAPPING.values())
    _SINGULAR_TYPES = set(_SINGULAR_MAPPING.values())
    _LINEAR_CONTAINER_TYPES = set(_LINEAR_CONTAINER_MAPPING.values())
    _PAIR_CONTAINER_TYPES = set(_PAIR_CONTAINER_MAPPING.values())

    TYPE_HEADER = "type"
    COLOR_HEADER = "color"
    REPR_HEADER = "repr"
    GRAPH_ID_HEADER = "id"
    GRAPH_PROPERTY_HEADER = "properties"
    PYTHON_ID_HEADER = "python_id"

    LINE_HEADER = "line"
    VARIABLE_HEADER = "variables"
    ACCESS_HEADER = "accesses"
    STDOUT_HEADER = "stdout"
    PAIR_KEY_HEADER = "key"
    PAIR_VALUE_HEADER = "value"

    _BAD_REPR_STRING = "BAD REPR FUNCTION"

    def __init__(
        self,
        *,
        graph: Graph = None,
        stdout: StringIO = None,
        float_precision: int = 10,
        logger: Logger = void_logger,
    ):
        self._changes: List[MutableMapping] = []
        self._final_changes: List[MutableMapping] | None = None
        self._color_mapping: MutableMapping = {**self._DEFAULT_COLOR_MAPPING}
        self._logger = logger

        # since node and edges don't carry data anymore
        self._graph = graph
        self._stdout = stdout
        self._stdout_cache = []
        self._float_precision = float_precision

    def assign_and_get_color(self, identifier_string: str) -> None:
        """
        assign color to identifier some string
        :param identifier_string: the identifier string
        :return: the color
        """
        if identifier_string not in self._color_mapping:
            if len(self._color_mapping) < len(self._DEFAULT_COLOR_PALETTE):
                color = self._DEFAULT_COLOR_PALETTE[len(self._color_mapping)]
            else:
                color = generate_hex()
                while color in self._color_mapping.values():
                    color = generate_hex()
            self._logger.debug(f"assigned color {color} for {identifier_string}")
            self._color_mapping[identifier_string] = color

        return self._color_mapping[identifier_string]

    def register_variable(self, identifier: Sequence[str]) -> str:
        """
        a variable is identified by a identifier, which is
        a tuple of two strings. The first strings is the
        name of the place, ie functions etc., in which the
        variable is created. The second string is the variable
        name.
        :param identifier:
        :return:
        """
        identifier_string = identifier_to_string(identifier)
        self.assign_and_get_color(identifier_string)
        return identifier_string

    def add_record(self, line_no: int = -1) -> None:
        """
        add a record to the change list
        :param line_no: the line number
        :return:
        """
        self._changes.append(
            {
                self.LINE_HEADER: line_no,
                self.VARIABLE_HEADER: None,
                self.ACCESS_HEADER: None,
                self.STDOUT_HEADER: None,
            }
        )

    def get_last_record(self) -> MutableMapping:
        """
        get the last record
        :return: a record mapping
        """
        return self._changes[-1]

    def get_last_record_line_number(self) -> int:
        """
        get the line number of the last record
        :return: a line number
        """
        return self.get_last_record()[self.LINE_HEADER]

    def get_second_to_last_record(self) -> MutableMapping:
        """
        ok this get the second to last record
        :return: a record mapping
        """

        # this should not be a problem in official use, since the first line in the main function
        # ie. `def main()`: has no variables.
        return self._changes[-2] if len(self._changes) > 1 else self._changes[-1]

    def get_second_to_last_record_line_number(self) -> int:
        """
        get the line number of the second to last record
        :return: a line number
        """
        return self.get_second_to_last_record()[self.LINE_HEADER]

    def get_last_variable_change(self) -> MutableMapping:
        """
        get the last variable change dict
        :return: variable dict in the last record
        """

        last_variable_change = self.get_last_record()[self.VARIABLE_HEADER]
        if last_variable_change is None:
            last_variable_change = self.get_last_record()[self.VARIABLE_HEADER] = {}

        return last_variable_change

    def get_second_to_last_variable_change(self) -> MutableMapping:
        """Get the second last dict in the record list"""
        previous_variable_change = self.get_second_to_last_record()[
            self.VARIABLE_HEADER
        ]
        if previous_variable_change is None:
            previous_variable_change = self.get_second_to_last_record()[
                self.VARIABLE_HEADER
            ] = {}

        return previous_variable_change

    def get_last_variable_access(self) -> List:
        """
        get the access list from the last record
        :return: access list in the last record
        """
        if self.get_last_record()["accesses"] is None:
            self.get_last_record()["accesses"] = []

        return self.get_last_record()["accesses"]

    def _generate_repr(self, variable_state: Any) -> str:
        try:
            if isinstance(variable_state, float):
                repr_result = f"{variable_state:.{self._float_precision}f}"
            else:
                repr_result = repr(variable_state)
        except Exception:
            repr_result = self._BAD_REPR_STRING

        return repr_result

    def _generate_singular_repr(self, variable_state: Any) -> str:
        return self._generate_repr(variable_state)

    # ========== repr for different entities
    def _generate_linear_container_repr(
        self, variable_state: Sequence, memory_trace: Set
    ) -> List:
        temp = []
        for element in variable_state:
            temp.append(
                self.process_variable_state(
                    self._INNER_IDENTIFIER_STRING, element, copy(memory_trace)
                )
            )
        return temp

    def _generate_pair_container_repr(
        self, variable_state: Mapping, memory_trace: Set
    ) -> List[Dict[str, MutableMapping]]:
        temp = []
        for key, value in variable_state.items():
            temp.append(
                {
                    self.PAIR_KEY_HEADER: self.process_variable_state(
                        self._INNER_IDENTIFIER_STRING, key, copy(memory_trace)
                    ),
                    self.PAIR_VALUE_HEADER: self.process_variable_state(
                        self._INNER_IDENTIFIER_STRING, value, copy(memory_trace)
                    ),
                }
            )
        return temp

    def custom_repr(
        self, variable_state: Any, variable_type: str, memory_trace: Set
    ) -> Any:
        if variable_type == self.REFERENCE_TYPE_STRING:
            # which should always be None
            repr_result = None
        elif variable_type in self._GRAPH_OBJECT_TYPES:
            # TODO use custom graph repr generator
            repr_result = self._generate_singular_repr(variable_state)
        elif (
            variable_type in self._SINGULAR_TYPES
            or variable_type == self._OBJECT_TYPE_STRING
        ):
            repr_result = self._generate_singular_repr(variable_state)
        elif variable_type in self._LINEAR_CONTAINER_TYPES:
            repr_result = self._generate_linear_container_repr(
                variable_state, memory_trace
            )
        elif variable_type in self._PAIR_CONTAINER_TYPES:
            repr_result = self._generate_pair_container_repr(
                variable_state, memory_trace
            )
        else:
            # the wild card
            repr_result = self._generate_repr(variable_state)
        return repr_result

    # ==========  repr end

    def _search_type_string(self, variable_state: Any) -> str:
        """
        takes in an entity and returns the corresponding type label
        :param variable_state:
        :return:
        """
        for type_validator, type_string in self._GRAPH_OBJECT_MAPPING.items():
            if type_validator(variable_state):
                return type_string

        for type_candidate, type_string in self._TYPE_MAPPING.items():
            if isinstance(variable_state, type_candidate):
                return type_string

    def process_variable_state(
        self, var_ident_str: str, variable_state: Any, memory_trace: Set = None
    ) -> MutableMapping:
        """
        takes in an identity label, the corresponding entity, and previous memory trace
        returns
        :param var_ident_str:
        :param variable_state:
        :param memory_trace:
        :return:
        """
        # TODO this is problematic
        if memory_trace is None:
            memory_trace = set()
        var_id = id(variable_state)

        if var_id in memory_trace:
            # leave a note on the object and then trace back
            variable_type: str = self.REFERENCE_TYPE_STRING
        else:
            variable_type: str = self._search_type_string(variable_state)
            memory_trace.add(var_id)

        state_mapping: MutableMapping = {
            self.TYPE_HEADER: variable_type,
            self.PYTHON_ID_HEADER: var_id,
            self.COLOR_HEADER: self._color_mapping[var_ident_str],
        }

        state_mapping[self.REPR_HEADER] = self.custom_repr(
            variable_state, state_mapping[self.TYPE_HEADER], memory_trace
        )

        if state_mapping[self.TYPE_HEADER] in self._GRAPH_OBJECT_TYPES:
            variable_state: Union[Node, Edge]
            state_mapping[self.GRAPH_ID_HEADER] = get_cytoscape_id(
                self._graph, variable_state, self.GRAPH_ID_HEADER
            )
            state_mapping[self.GRAPH_PROPERTY_HEADER] = deepcopy(
                self._graph.nodes.get(variable_state, {})
            )

        return state_mapping

    def read_from_io(self) -> List[str] | None:
        """
        read from given stdout stream
        :return:
        """
        if not self._stdout:
            return None
        self._stdout.seek(0)
        result = self._stdout.readlines()
        if result != self._stdout_cache:
            # egh, black handles slices poorly
            # TODO how about performance?
            diff = result[len(self._stdout_cache) :]
            self._stdout_cache = result
            return diff
        return None

    def add_stdout_change(self) -> None:
        """
        add last current output into record
        :return: None
        """
        self.get_second_to_last_record()[self.STDOUT_HEADER] = self.read_from_io()

    def add_variable_change_to_last_record(
        self, var_ident_str: str, variable_state: Any
    ) -> None:
        """
        add a variable change to the last record
        @param var_ident_str: (name_space, variable_name)
        @param variable_state: the variable state
        @return: None
        """
        # if isinstance(variable_change, Tuple):
        self.get_last_variable_change()[var_ident_str] = self.process_variable_state(
            var_ident_str, variable_state
        )

    def add_variable_change_to_second_to_last_record(
        self, var_ident_str: str, variable_state: Any
    ) -> None:
        """Add variable change to previous (second last if possible) record.

        When the variable is created/changed in line a,
        the tracer evaluate it in line a+1. So, this function
        is created to deal with this offset
        @param var_ident_str:
        @param variable_state:
        @return:
        """
        # if isinstance(variable_change, Tuple) and len(self.changes) > 1:
        self.get_second_to_last_variable_change()[
            var_ident_str
        ] = self.process_variable_state(var_ident_str, variable_state)

    def add_variable_access_to_last_record(self, access_change: Any) -> None:
        """
        add an access change to the last record
        @param access_change: what's accessed
        @return: None
        """
        self.get_last_variable_access().append(
            self.process_variable_state(self._ACCESSED_IDENTIFIER_STRING, access_change)
        )

    @property
    def _init_result_object(self) -> MutableMapping:
        """
        default init records that will be placed at the beginning of the record array
        :return: an init record
        """
        return {
            self.LINE_HEADER: 0,
            self.VARIABLE_HEADER: (
                {
                    key: {
                        self.TYPE_HEADER: self.INIT_TYPE_STRING,
                        self.COLOR_HEADER: value,
                        self.REPR_HEADER: None,
                    }
                    for key, value in self._color_mapping.items()
                    if not (
                        key == self._INNER_IDENTIFIER_STRING
                        or key == self._ACCESSED_IDENTIFIER_STRING
                    )
                }
            )
            if len(self._color_mapping) > len(self._DEFAULT_COLOR_MAPPING)
            else None,
            self.ACCESS_HEADER: None,
            self.STDOUT_HEADER: None,
        }

    def _process_change_list(self) -> List[Dict]:
        if self._final_changes is None:
            init_object = self._init_result_object

            temp_container = [init_object]

            previous_variables = init_object[self.VARIABLE_HEADER]

            for change in self._changes:
                variables_field = change[self.VARIABLE_HEADER]

                temp_object = {**change}

                if variables_field is None:
                    temp_object[self.VARIABLE_HEADER] = None
                else:
                    current_current_variables = deepcopy(previous_variables)
                    for changed_var_key, changed_var_value in variables_field.items():
                        current_current_variables[changed_var_key] = changed_var_value
                    temp_object[self.VARIABLE_HEADER] = current_current_variables
                    previous_variables = current_current_variables

                temp_container.append(temp_object)

            self._final_changes = temp_container

        return self._final_changes

    def get_change_list(self) -> List[MutableMapping]:
        return self._changes

    @property
    def change_list(self):
        return self._changes

    @property
    def final_change_list(self) -> List[Dict]:
        return self._process_change_list()

    @property
    def final_change_list_json(self) -> str:
        return json.dumps(self.final_change_list)
