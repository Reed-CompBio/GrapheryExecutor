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
            .add_record().add_stdout('a').back()\
            .add_record().add_stdout('b').back()\
            .add_record().add_stdout('c').back()\
            .use_with()  # to handle with exit
        # fmt: on

        target.check(ctrl.recorder.final_change_list)
