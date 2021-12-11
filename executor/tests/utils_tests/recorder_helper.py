from __future__ import annotations

import sys
from typing import Mapping, List, Set

from executor.utils.recorder import Recorder


class Record:
    def __init__(self, record_eq: RecorderEQ):
        self.record_eq = record_eq
        self.variables = None
        self.access = None
        self.stdout = None

        self._construct_str = None

    def add_variable(self, var: str) -> Record:
        if self.variables is None:
            self.variables = set()
        self.variables.add(var)
        return self

    def add_access(self, var: str) -> Record:
        if self.access is None:
            self.access = set()
        self.variables.add(var)
        return self

    def add_stdout(self, line, end: str = "\n") -> Record:
        if self.stdout is None:
            self.stdout = []
        self.stdout.append(f"{line}{end}")
        return self

    def back(self) -> RecorderEQ:
        return self.record_eq

    def check(self, record: Mapping) -> None | str:
        print(record, file=sys.stderr)
        actual_vars: Mapping | None = record[Recorder._VARIABLE_HEADER]
        if actual_vars is not None:
            actual_vars: Set = set(actual_vars.keys())
            if (a_l := len(actual_vars)) != (t_l := len(self.variables)):
                return (
                    f"actual variable length {a_l} does not match target length {t_l}"
                )
            if actual_vars != self.variables:
                return (
                    f"actual vars differ from target vars, diff: "
                    f"{actual_vars if self.variables is None else actual_vars ^ self.variables}"
                )

        actual_access = record[Recorder._ACCESS_HEADER]
        if actual_access is not None and (a_l := len(actual_access)) != (
            t_l := len(self.access)
        ):
            return f"actual access length {a_l} does not match target length {t_l}"

        actual_std = record[Recorder._STDOUT_HEADER]
        if actual_std != self.stdout:
            return (
                f"actual stdout {actual_std} does not match target stdout {self.stdout}"
            )

        return None

    @property
    def construct_str(self):
        if self._construct_str is None:
            candidates = []
            for v in self.variables or ():
                candidates.append(f"\n.add_variable({v})")
            for a in self.access or ():
                candidates.append(f"\n.add_access({repr(a)})")
            for s in self.stdout or ():
                candidates.append(f"\n.add_stdout({s})")
            self._construct_str = "".join(candidates)

        return self._construct_str

    def __str__(self):
        return self.construct_str

    def __repr__(self):
        return self.__str__()


class RecorderEQ:
    def __init__(self):
        self.check_queue: List[Record] = []

    def add_record(self) -> Record:
        self.check_queue.append(Record(self))
        return self.check_queue[-1]

    def use_with(self) -> RecorderEQ:
        return self.add_record().back()

    def check(self, records: List[Mapping]) -> None:
        # remove init records and don't check that by default, maybe not a good idea?
        records = records[1:]

        record_len = len(records)
        target_len = len(self.check_queue)

        assert (
            record_len == target_len
        ), f"record length {record_len} does not match queue length {target_len}"

        for no, (target, record) in enumerate(zip(self.check_queue, records)):
            if target.check(record) is not None:
                line = record.get(Recorder._LINE_HEADER)
                if res := target.check(record):
                    raise AssertionError(
                        f"the {no}th record at line {line} does not match the expected. Error: \n"
                        f"{res}\n"
                        "expected: \n"
                        f"{target}\n"
                        f"actual: \n"
                        f"{record}"
                    )
