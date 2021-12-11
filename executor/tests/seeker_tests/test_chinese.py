# -*- coding: utf-8 -*-
# Copyright 2019 Ram Rachum and collaborators.
# This program is distributed under the MIT license.

from executor import seeker
from .utils import (
    assert_output,
    VariableEntry,
    CallEntry,
    LineEntry,
    ReturnEntry,
    ReturnValueEntry,
    SourcePathEntry,
    ElapsedTimeEntry,
)
from . import mini_toolbox


def test_chinese():
    with mini_toolbox.create_temp_folder(prefix="seeker") as folder:
        path = folder / "foo.log"

        @seeker.tracer(output=path, only_watch=False)
        def foo():
            a = 1
            x = "失败"
            return 7

        foo()
        with path.open(encoding="utf-8") as file:
            output = file.read()
        assert_output(
            output,
            (
                SourcePathEntry(),
                CallEntry(),
                LineEntry(),
                VariableEntry("a"),
                LineEntry('x = "失败"'),
                VariableEntry("x", ("'失败'")),
                LineEntry(),
                ReturnEntry(),
                ReturnValueEntry("7"),
                ElapsedTimeEntry(),
            ),
        )
