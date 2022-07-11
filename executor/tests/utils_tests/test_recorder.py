from __future__ import annotations

from copy import deepcopy
from textwrap import dedent

import networkx as nx
from networkx import Edge

from .recorder_helper import RecorderEQ, Checker
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

        target = (
            RecorderEQ()
            .start_init()
            .add_record_and_back(stdout="a")
            .add_record_and_back(stdout="b")
            .add_record_and_back(stdout="c")
            .exit_with()
        )  # to handle with exit

        target.check(ctrl.recorder.final_change_list)

    def test_stdout_loop_capture(self):
        line_content = 1
        num = 5

        code = dedent(
            f"""\
            with tracer():
                for _ in range({num}):
                    print({line_content})
                for _ in range({num}):
                    print({line_content})
            """
        )
        ctrl = run_main(
            self.controller,
            code=code,
            graph_data=self.default_graph_data,
        )

        target = RecorderEQ().start_init()  # to handle with exit

        for _ in range(num):
            target.add_record_and_back(line=2).add_record(
                line=3, stdout=f"{line_content}"
            )
        target.add_record_and_back(line=2)

        for _ in range(num):
            target.add_record_and_back().add_record(stdout=f"{line_content}")
        target.add_record_and_back()

        target.exit_with()

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
            .return_from()
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
                    print(node)
                for edge in graph.edges:
                    print(edge)

            if __name__ == "__main__":
                main()
            """
        )
        g = nx.Graph()
        node_num = 3
        g.add_nodes_from(range(node_num))

        ctrl = run_main(self.controller, code=code, graph_data=g)

        target = RecorderEQ().start_init()
        target.add_record()

        for i in range(node_num):
            (
                target.add_record()
                .add_variable(
                    "main",
                    "node",
                    type="Node",
                    repr=str(i),
                    attributes=Checker(contains=("key",)),
                )
                .back()
                .add_record_and_back()
                .add_record_and_back(stdout=f"{i}")
            )

        target.add_record(line=3)

        for j in range(node_num):
            (
                target.add_record()
                .add_variable(
                    "main",
                    "node",
                    type="Node",
                    repr=str(node_num - 1),
                    attributes=Checker(contains=("key",)),
                )
                .add_variable(
                    "main",
                    "edge",
                    type="Edge",
                    repr=f"{Edge.wraps((j, j))}",
                )
                .back()
                .add_record_and_back(stdout=str(Edge.wraps((j, j))))
            )

        target.add_record_and_back().return_from()

        target.check(ctrl.recorder.final_change_list)
