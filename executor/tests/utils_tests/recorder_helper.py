from __future__ import annotations

from typing import Mapping, List

from executor.utils.recorder import Recorder, identifier_to_string


class Record:
    def __init__(self, record_eq: RecorderEQ, line: int = None):
        self.record_eq = record_eq
        self.line = line
        self.variables = None
        self.access = None
        self.stdout = None

        self._construct_str = None

    def add_variable(self, *args) -> Record:
        if self.variables is None:
            self.variables = set()
        self.variables.add(identifier_to_string(args))
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
        if self.line is not None:
            if self.line != (actual_line := record[Recorder.LINE_HEADER]):
                return f"expected line number {self.line} does not match actual line {actual_line}"

        actual_vars: Mapping | None = record[Recorder.VARIABLE_HEADER]
        if actual_vars is not None:
            for k, v in actual_vars.items():
                if (
                    v.get(Recorder.TYPE_HEADER) != Recorder.INIT_TYPE_STRING
                    and k not in self.variables
                ):
                    return f"unexpected variable {repr(k)} shows"

            for k in self.variables or ():
                if (
                    actual_vars.get(k).get(Recorder.TYPE_HEADER)
                    == Recorder.INIT_TYPE_STRING
                ):
                    return f"expected value {repr(k)} is not in actual result {actual_vars.keys()}"

        actual_access = record[Recorder.ACCESS_HEADER]
        if actual_access is not None and (a_l := len(actual_access)) != (
            t_l := len(self.access)
        ):
            return f"actual access length {a_l} does not match target length {t_l}"

        actual_std = record[Recorder.STDOUT_HEADER]
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
                candidates.append(f"\n.add_variable({repr(v)})")
            for a in self.access or ():
                candidates.append(f"\n.add_access({repr(a)})")
            for s in self.stdout or ():
                candidates.append(f"\n.add_stdout({repr(s)})")
            self._construct_str = "".join(candidates)

        return self._construct_str

    def __str__(self):
        return self.construct_str

    def __repr__(self):
        return self.__str__()


class RecorderEQ:
    def __init__(self):
        self.check_queue: List[Record] = []

    def add_record(self, line: int = None) -> Record:
        self.check_queue.append(Record(self, line))
        return self.check_queue[-1]

    def exit_with(self) -> RecorderEQ:
        return self.add_record().back()

    def start_init(self) -> RecorderEQ:
        return self.add_record(0).back()

    def check(self, records: List[Mapping]) -> None:
        # remove init records and don't check that by default, maybe not a good idea?
        record_len = len(records)
        target_len = len(self.check_queue)

        assert (
            record_len == target_len
        ), f"record length {record_len} does not match queue length {target_len}"

        for no, (target, record) in enumerate(zip(self.check_queue, records)):
            if target.check(record) is not None:
                line = record.get(Recorder.LINE_HEADER)
                if res := target.check(record):
                    raise AssertionError(
                        f"the {no}th record at line {line} does not match the expected. Error: \n"
                        f"{res}\n"
                        "expected: \n"
                        f"{target}\n"
                        f"actual: \n"
                        f"{record}"
                    )
