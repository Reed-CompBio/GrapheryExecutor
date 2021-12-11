from __future__ import annotations

from copy import deepcopy
from textwrap import dedent

from .recorder_helper import RecorderEQ
from .test_controller import make_test_controller_instance
from executor.utils.controller import GraphController
from ...utils.recorder import Recorder


def run_main(cls, **kwargs):
    ctrl = make_test_controller_instance(cls, **kwargs)
    ctrl.main()
    return ctrl


class TestRecorder:
    def setup_class(self):
        self.controller = deepcopy(GraphController)
        self.controller._graph_builder = dict

        self.default_graph_data = {}

    def test_color_assignment(self):
        r = Recorder()
        num = 20
        for i in range(num):
            r.register_variable(("", f"{i}"))

        assert (
            len(set(r._color_mapping.values())) == len(r._DEFAULT_COLOR_MAPPING) + num
        ), f"duplicated coloring was generated"

    def test_float_precision(self):
        p = 7
        r = Recorder(float_precision=p)
        res = r._generate_repr(1 / 3)
        assert len(res[res.index(".") + 1 :]) == p

    def test_stdout_capture(self):
        code = dedent(
            """\
            with tracer():
                print('a')
                print('b')
                print('c')
            """
        )
        ctrl = run_main(
            self.controller,
            code=code,
            graph_data=self.default_graph_data,
        )

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
        ctrl = run_main(
            self.controller,
            code=code,
            graph_data=self.default_graph_data,
        )

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
        ctrl = run_main(
            self.controller,
            code=code,
            graph_data=self.default_graph_data,
        )

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

    def test_peek(self):
        code = dedent(
            """\
            @tracer.peek
            def compute(a, b, c):
                a = a ** a
                b = b * a - c
                return a * b + c
            
            with tracer('j', 'k'):
                i = compute(2, 3, 5)
                j = compute(7, 9, 10) * compute(3, 2, -1)
                k = 11 - 7
            """
        )

        ctrl = run_main(
            self.controller,
            code=code,
            graph_data=self.default_graph_data,
        )

        # fmt: off
        target = RecorderEQ()\
            .start_init()\
            .add_record().add_access('i').back()\
            .add_record().add_variable('', 'j').add_access(1).add_access(2).back()\
            .add_record().add_variable('', 'j').add_variable('', 'k').back()\
            .exit_with()
        # fmt: on

        target.check(ctrl.recorder.final_change_list)
