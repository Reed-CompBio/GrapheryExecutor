from __future__ import annotations

from copy import deepcopy
from textwrap import dedent

import pytest

from .recorder_helper import RecorderEQ
from .test_controller import make_test_controller_instance
from executor.utils.controller import GraphController


class TestRecorder:
    def setup_class(self):
        self.controller = deepcopy(GraphController)
        self.controller._graph_builder = dict

        self.default_graph_data = {}

    def test_stdout_capture(self):
        code = dedent(
            """\
            with tracer():
                print('a')
                print('b')
                print('c')
            """
        )
        ctrl = make_test_controller_instance(
            self.controller,
            code=code,
            graph_data=self.default_graph_data,
        )
        ctrl.main()

        # fmt: off
        target = RecorderEQ()\
            .start_init()\
            .add_record().add_stdout('a').back()\
            .add_record().add_stdout('b').back()\
            .add_record().add_stdout('c').back()\
            .exit_with()  # to handle with exit
        # fmt: on

        target.check(ctrl.recorder.final_change_list)

    def test_simple_variable(self):
        code = dedent(
            """\
            with tracer():
                i = 10
            """
        )
        ctrl = make_test_controller_instance(
            self.controller,
            code=code,
            graph_data=self.default_graph_data,
        )
        ctrl.main()

        # fmt: off
        target = RecorderEQ()\
            .start_init()\
            .add_record().add_variable('i').back()\
            .exit_with()
        # fmt: on

        target.check(ctrl.recorder.final_change_list)

    def test_variable_record(self):
        code = dedent(
            """\
            @tracer('a', 'b')
            def test(a, b, c):
                a = b * c
                b = c * a 
                c = a * b
                return a, b
            
            with tracer('i', 'j'):
                i, j = test(5, 7, 11)
                k = i ** 0.5
            """
        )
        ctrl = make_test_controller_instance(
            self.controller,
            code=code,
            graph_data=self.default_graph_data,
        )
        ctrl.main()

        # fmt: off
        target = RecorderEQ() \
            .start_init()\
            .add_record().back() \
            .add_record().add_variable('test', 'a').add_variable('test', 'b').back() \
            .add_record().add_variable('test', 'a').add_variable('test', 'b').back() \
            .add_record().add_variable('test', 'a').add_variable('test', 'b').back() \
            .add_record().back() \
            .add_record()\
                .add_variable('test', 'a')\
                .add_variable('test', 'b')\
                .add_variable('', 'i')\
                .add_variable('', 'j')\
                .back()\
            .add_record().back() \
            .exit_with()  # to handle with exit
        # fmt: on

        target.check(ctrl.recorder.final_change_list)
