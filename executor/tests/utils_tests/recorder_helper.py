from __future__ import annotations

from typing import Mapping, List, Any, Set, Sequence

from executor.utils.recorder import Recorder, identifier_to_string
import pprint


class _NotSet:
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "not set"


not_set = _NotSet()

del _NotSet


def is_not_set(value: Any) -> bool:
    return value is not_set


class STDOUTAdder:
    def __init__(self, *args):
        self._stdout = [*args]

    @property
    def stdout(self):
        if self._stdout:
            return "\n".join(self._stdout) + "\n"
        return None

    def add_stdout(self, *args):
        if all(isinstance(arg, str) for arg in args):
            self._stdout.extend(args)

    def add_line(self, line):
        self._stdout.append(line)

    def __str__(self):
        return self.stdout

    def __repr__(self):
        return self.__str__()


class Checker:
    def __init__(
        self,
        equals: Any = not_set,
        contains: Sequence[Any] = not_set,
        contains_any: Sequence[Any] = not_set,
        contains_equal: Mapping[Any, Any] = not_set,
    ):
        self.check_list = {
            "equals": equals,
            "contains": contains,
            "contains_any": contains_any,
            "contains_equal": contains_equal,
        }

    def check(self, other):
        for name, value in self.check_list.items():
            if is_not_set(value):
                continue

            if not getattr(self, f"_{name}")(other):
                return False
        return True

    def _equals(self, other):
        return other == self.check_list["equals"]

    def _contains(self, other):
        return all(contained in other for contained in self.check_list["contains"])

    def _contains_any(self, other):
        return any(contained in other for contained in self.check_list["contains_any"])

    def _contains_equal(self, other):
        for contained_name, contained_value in self.check_list[
            "contains_equal"
        ].items():
            if contained_name not in other:
                return False
            try:
                real_value = other[contained_name]

            except (KeyError, TypeError):
                try:
                    real_value = getattr(other, contained_name)
                except AttributeError:
                    return False

            if contained_value != real_value:
                return False
        return True


class Variable:
    headers_to_compare = [
        Recorder.TYPE_HEADER,
        Recorder.REPR_HEADER,
        Recorder.GRAPH_PROPERTY_HEADER,
        Recorder.COLOR_HEADER,
    ]

    def __init__(self, is_access: bool = False, **kwargs):
        self.is_access = is_access
        self.identifier = kwargs.pop("identifier") if not self.is_access else not_set

        for header in self.headers_to_compare:
            setattr(self, header, kwargs.pop(header, not_set))

    def check(self, other: Variable | Mapping, **kwargs) -> bool:
        if is_not_set(other):
            return False

        if isinstance(other, Mapping):
            other = Variable(**other, **kwargs)

        if other.is_access ^ self.is_access:
            return False

        for header in self.headers_to_compare:
            header_value = getattr(self, header)
            if is_not_set(header_value):
                continue

            other_value = getattr(other, header)
            if isinstance(header_value, Checker):
                if not header_value.check(other_value):
                    return False
            else:
                if header_value != other_value:
                    return False

        return True

    def __eq__(self, other):
        if isinstance(other, Variable):
            return other.identifier == self.identifier
        elif isinstance(other, str):
            return other == self.identifier
        else:
            return False

    def __hash__(self):
        return hash(self.identifier)

    def __str__(self):
        return (
            f"{self.identifier} -> "
            f"{{{' - '.join(str(getattr(self, header)) for header in self.headers_to_compare)}}}"
        )

    def __repr__(self):
        return str(self)


class _NotSet:
    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "not set"


not_set = _NotSet()

del _NotSet


def is_not_set(value: Any) -> bool:
    return value is not_set


class Variable:
    headers_to_compare = [
        Recorder.TYPE_HEADER,
        Recorder.REPR_HEADER,
        Recorder.GRAPH_PROPERTY_HEADER,
        Recorder.COLOR_HEADER,
    ]

    def __init__(self, is_access: bool = False, **kwargs):
        self.is_access = is_access
        self.identifier = kwargs.pop("identifier") if not self.is_access else not_set

        for header in self.headers_to_compare:
            setattr(self, header, kwargs.pop(header, not_set))

    def check(self, other: Variable | Mapping, **kwargs) -> bool:
        if is_not_set(other):
            return False

        if isinstance(other, Mapping):
            other = Variable(**other, **kwargs)

        if other.is_access ^ self.is_access:
            return False

        for header in self.headers_to_compare:
            header_value = getattr(self, header)
            if is_not_set(header_value):
                continue

            if header_value != getattr(other, header):
                return False

        return True

    def __eq__(self, other):
        if isinstance(other, Variable):
            return other.identifier == self.identifier
        elif isinstance(other, str):
            return other == self.identifier
        else:
            return False

    def __hash__(self):
        return hash(self.identifier)

    def __str__(self):
        return (
            f"{self.identifier} -> "
            f"{{{' - '.join(str(getattr(self, header)) for header in self.headers_to_compare)}}}\n"
        )

    def __repr__(self):
        return str(self)


class Record:
    def __init__(
        self, record_eq: RecorderEQ, line: int = None, is_init: bool = False, **kwargs
    ):
        self.record_eq = record_eq
        self.line = line
        self.variables: Set[Variable] | None = None
        self.accesses: List[Variable] | None = None
        self.stdout: str | None = None
        self.is_init = is_init

        self._construct_str = None

    def add_variable(self, *args, **kwargs) -> Record:
        if self.variables is None:
            self.variables = set()
        self.variables.add(
            Variable(
                identifier=identifier_to_string(args),
                **kwargs,
            )
        )
        return self

    def add_access(self, **kwargs) -> Record:
        if self.accesses is None:
            self.accesses = []
        self.accesses.append(Variable(is_access=True, **kwargs))
        return self

    def write_stdout(self, content: str | None) -> Record:
        self.stdout = content
        return self

    def back(self) -> RecorderEQ:
        return self.record_eq

    def check(self, record: Mapping) -> None | str:
        if self.line is not None:
            if self.line != (actual_line := record[Recorder.LINE_HEADER]):
                return f"expected line number {self.line} does not match actual line {actual_line}"

        # if the record is the init record, we make sure all variables have the correct types
        # and the record doesn't have any accesses nor stdout
        # otherwise, we make sure the record has the correct variables and accesses
        # variables are registered at the end so that RecorderEQ can keep track of
        # the variable records
        if self.is_init:
            if self.accesses is not None:
                return "accesses were recorded in init but they should not be"
            if self.stdout is not None:
                return "stdout was recorded in init but they should not be"

            if record[Recorder.VARIABLE_HEADER] is None:
                return "init record does not have any initial variables"

            if any(
                variable_info.get(Recorder.TYPE_HEADER) != Recorder.INIT_TYPE_STRING
                for variable_info in record[Recorder.VARIABLE_HEADER].values()
            ):
                return 'all variables in init should be of type "init"'

            try:
                self.record_eq.register_variables(
                    *record[Recorder.VARIABLE_HEADER].keys()
                )
            except ValueError as e:
                return str(e)

            return

        actual_vars: Mapping | None = record[Recorder.VARIABLE_HEADER]
        # if it is None, it means that the variable was not changed at this line
        # if not, it's going to be a dict with the variable identifier as key
        # and the variable info as value
        if actual_vars is not None:
            actual_vars: Mapping
            if len(actual_vars) != len(self.variables):
                if len(
                    [
                        var
                        for var in actual_vars.values()
                        if var[Recorder.TYPE_HEADER] == "Init"
                    ]
                ) != len(self.variables):
                    return f"expected {len(self.variables)} variables but got {len(actual_vars)}"

            for variable in self.variables:
                if not variable.check(
                    actual_vars.get(variable.identifier, not_set),
                    identifier=variable.identifier,
                ):
                    return f"variable {variable} does not match with {actual_vars[variable.identifier]}"

        actual_accesses = record[Recorder.ACCESS_HEADER]
        if actual_accesses is not None and self.accesses is not None:
            if (a_l := len(actual_accesses)) != (t_l := len(self.accesses)):
                return f"actual access length {a_l} ({actual_accesses}) does not match target length {t_l} ({self.accesses})"

            for access in self.accesses:
                if all(
                    not access.check(actual_access, is_access=True)
                    for actual_access in actual_accesses
                ):
                    return f"access {access} does not match with {actual_accesses}"
        elif actual_accesses is not None:
            return "accesses were recorded but they should not be"
        elif self.accesses is not None:
            return "accesses were not recorded but they should be"

        actual_std = record[Recorder.STDOUT_HEADER]
        if actual_std != self.stdout:
            return (
                f"actual stdout\n"
                f"{actual_std}\n"
                f"does not match target stdout\n"
                f"{self.stdout}"
            )

        return None

    @property
    def construct_str(self):
        if self._construct_str is None:
            candidates = []
            for v in self.variables or ():
                candidates.append(f".add_variable({repr(v)})")
            for a in self.accesses or ():
                candidates.append(f".add_access({repr(a)})")

            candidates.append(f".write_stdout({self.stdout})")
            self._construct_str = "\n".join(candidates)

        return self._construct_str

    def __str__(self):
        return self.construct_str

    def __repr__(self):
        return self.__str__()


class RecorderEQ:
    def __init__(self):
        self.check_queue: List[Record] = []
        self.total_variables: Set[str] | None = None
        self.std_adder = STDOUTAdder()

    def register_variables(self, *args):
        if self.total_variables is None:
            self.total_variables = set(args)
        else:
            raise ValueError("variables are already registered")

    def add_record(self, line: int = None, **kwargs) -> Record:
        record = Record(self, line, **kwargs)

        if stdout := kwargs.get("stdout", None):
            if isinstance(stdout, str):
                self.std_adder.add_stdout(stdout)
            elif isinstance(stdout, Sequence) and all(
                isinstance(s, str) for s in stdout
            ):
                self.std_adder.add_stdout(*stdout)
            record.write_stdout(self.std_adder.stdout)

        self.check_queue.append(record)
        return record

    def add_record_and_back(self, line: int = None, **kwargs) -> RecorderEQ:
        return self.add_record(line, **kwargs).back()

    def add_record_and_back(self, line: int = None) -> RecorderEQ:
        return self.add_record(line).back()

    def exit_with(self) -> RecorderEQ:
        return self.add_record().back()

    def return_from(self) -> RecorderEQ:
        return self.add_record().back()

    def start_init(self) -> RecorderEQ:
        return self.add_record(0, is_init=True).back()

    def check(self, records: List[Mapping]) -> None:
        # remove init records and don't check that by default, maybe not a good idea?
        record_len = len(records)
        target_len = len(self.check_queue)

        try:
            assert (
                record_len == target_len
            ), f"record length {record_len} does not match target length {target_len}"

            for no, (target, record) in enumerate(zip(self.check_queue, records)):
                if (res := target.check(record)) is not None:
                    raise AssertionError(
                        f"the {no}th record at line {record.get(Recorder.LINE_HEADER)} "
                        f"does not match the expected. Error: \n"
                        f"{res}\n"
                        "expecting:\n"
                        f"{target}\n"
                        f"actual: \n"
                        f"{record}\n"
                        f"whole list: \n"
                        f"{pprint.pformat(records)}"
                    )
        except Exception as e:
            raise AssertionError(
                "error while checking the records.\n"
                f"{e}\n"
                "whole list: \n"
                f"{pprint.pformat(records)}"
            )
