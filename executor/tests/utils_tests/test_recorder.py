from __future__ import annotations

from copy import deepcopy
from textwrap import dedent

import networkx as nx
from networkx import Edge

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
            .add_record().add_variable('i', type="Number", repr='10').back()\
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

        target = (
            RecorderEQ()
            .start_init()
            .add_record_and_back()
            .add_record()
            .add_variable("test", "a", type="Number", repr="5")
            .add_variable("test", "b", type="Number", repr="7")
            .back()
            .add_record()
            .add_variable("test", "a", type="Number", repr="77")
            .add_variable("test", "b", type="Number", repr="7")
            .back()
            .add_record()
            .add_variable("test", "a", type="Number", repr="77")
            .add_variable("test", "b", type="Number", repr="847")
            .back()
            .add_record_and_back()
            .add_record()
            .add_variable("test", "a", type="Number", repr="77")
            .add_variable("test", "b", type="Number", repr="847")
            .add_variable("", "i", type="Number", repr="77")
            .add_variable("", "j", type="Number", repr="847")
            .back()
            .add_record_and_back()
            .exit_with()
        )  # to handle with exit

        target.check(ctrl.recorder.final_change_list)

    def test_peek(self):
        codes = [
            dedent(
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
            ),
            dedent(
                """
                @peek
                def compute(a, b, c):
                    a = a ** a
                    b = b * a - c
                    return a * b + c

                with tracer('j', 'k'):
                    i = compute(2, 3, 5)
                    j = compute(7, 9, 10) * compute(3, 2, -1)
                    k = 11 - 7
                """
            ),
        ]

        for code in codes:

            ctrl = run_main(
                self.controller,
                code=code,
                graph_data=self.default_graph_data,
            )

            target = (
                RecorderEQ()
                .start_init()
                .add_record()
                .add_variable("i", type="Number", repr="33")
                .add_access(type="Number", repr="33")
                .back()
                .add_record()
                .add_variable("", "j", type="Number", repr=f"{6103999420221 * 1484}")
                .add_access(repr="6103999420221")
                .add_access(repr="1484")
                .back()
                .add_record()
                .add_variable("", "j")
                .add_variable("", "k", type="Number", repr="4")
                .back()
                .exit_with()
            )

            target.check(ctrl.recorder.final_change_list)

    def test_graph(self):
        code = dedent(
            """\
            @tracer('node', 'edge')
            def main() -> None:
                for node in graph.nodes:
                    graph.add_edge(node, node)
                for edge in graph.edges:
                    print(edge)

            if __name__ == "__main__":
                main()
            """
        )
        g = nx.Graph()
        node_num = 5
        g.add_nodes_from(range(5))

        ctrl = run_main(self.controller, code=code, graph_data=g)

        target = RecorderEQ().start_init()
        target.add_record()

        for i in range(node_num):
            # fmt: off
            target.add_record()\
                .add_variable("node", type="Node", repr=str(i))\
                .back()\
                .add_record_and_back()
            # fmt: on

        target.add_record(line=3)

        for i in range(node_num):
            # fmt: off
            target.add_record()\
                .add_variable('edge', type="Edge", repr=str(i))\
                .back()\
                .add_record()\
                .add_stdout(Edge.wraps((1, 1)))
            # fmt: on

        target.add_record(line=5)

        print(ctrl.recorder.final_change_list_json)
