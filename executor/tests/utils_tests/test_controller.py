import io
import pathlib
from contextlib import redirect_stdout
from logging import getLogger
from operator import eq
from textwrap import dedent
from typing import Type, Callable, List

import pytest
from platform import platform

from ...settings import DefaultVars, SERVER_VERSION
from ...settings.variables import NX_GRAPH_INJECTION_NAME, GRAPH_INJECTION_NAME
from ...utils.controller import GraphController, ControllerResultAnnouncer
from ...utils.graphology_helper import export_to_graphology

_platform = platform()
_settings = DefaultVars()


def make_test_controller_instance(
    ctrl_cls: Type[GraphController], **kwargs
) -> GraphController:
    ctrl = ctrl_cls(
        target_version=SERVER_VERSION,
        default_settings=_settings,
        **kwargs,
    ).init()
    # set is local when only running main
    ctrl._is_local = True
    return ctrl


class TestGraphController:
    def setup_class(self):
        class _GraphControllerCopy(GraphController):
            pass

        self.controller_cls: Type[GraphController] = _GraphControllerCopy
        self.controller_cls._graph_builder = dict

        import networkx as nx

        self.test_graph = nx.Graph()

        self.graph_node_num = 10

        for i in range(self.graph_node_num):
            self.test_graph.add_node(i, x=i, y=i, size=15)

        for i in range(1, self.graph_node_num - 1):
            self.test_graph.add_edge(i - 1, i + 1, size=10)

    @pytest.mark.skip("not available for now")
    def test_resource_restriction(self):
        # TODO add linux resource test with signal
        pass

    def test_graph_creation(self):
        controller = GraphController(
            code="",
            graph_data=export_to_graphology(self.test_graph),
            target_version=SERVER_VERSION,
            **{
                DefaultVars.IS_LOCAL: True,
            },
        )
        controller._build_graph()
        assert len(self.test_graph.nodes) == len(controller._graph)
        for node, data in self.test_graph.nodes(data=True):
            assert controller._graph.nodes[node] == data

        for *edge, data in self.test_graph.edges(data=True):
            assert data.items() <= controller._graph.edges[edge].items()

    @pytest.mark.parametrize(
        "code, graph_data",
        [
            (f"import {mod}", {})
            for mod in ["os", "sys", "posix", "gc", "multiprocessing"]
        ],
    )
    def test_banning_dangerous_import(self, code, graph_data):
        ctrl = make_test_controller_instance(
            self.controller_cls, code=code, graph_data=graph_data
        )
        with pytest.raises(SystemExit):
            ctrl.main()

    @pytest.mark.parametrize(
        "code",
        [
            dedent(
                """\
                import networkx.generators as gg
                gg.atlas.os
                """
            ),
            dedent(
                """\
                from networkx.generators import atlas
                atlas.os
                """
            ),
        ],
    )
    def test_dangerous_code(self, code):
        ctrl = make_test_controller_instance(
            self.controller_cls, code=code, graph_data={}
        )

        with pytest.raises(SystemExit):
            ctrl.main()

    @pytest.mark.parametrize(
        "code, graph_data",
        [
            (f"import {mod}", {})
            for mod in [
                "math",
                "random",
                "time",
                "functools",
                "itertools",
                "operator",
                "string",
                "collections",
                "re",
                "json",
                "heapq",
                "bisect",
                "copy",
                "hashlib",
            ]
        ],
    )
    def test_allowed_import(self, code, graph_data):
        ctrl = make_test_controller_instance(
            self.controller_cls, code=code, graph_data=graph_data
        )
        result = ctrl.main()
        assert isinstance(result, list)

    def test_out_fd_capture(self):
        intended_result = dedent(
            """\
            this is the capture test
            this is also some test
            """
        )
        code = "\n".join(
            f"print('{line}')" for line in intended_result.split("\n") if line.strip()
        )
        graph_data = {}
        ctrl = make_test_controller_instance(
            self.controller_cls,
            code=code,
            graph_data=graph_data,
            custom_ns={"var1": 1, "var2": 2},
        )
        ctrl.main()
        assert ctrl.stdout.getvalue() == intended_result

    def test_custom_ns_import(self):
        code = dedent(
            """\
            print(var1)
            print(var2)
            """
        )
        graph_data = {}
        ctrl = make_test_controller_instance(
            self.controller_cls,
            code=code,
            graph_data=graph_data,
            custom_ns={"var1": 1, "var2": 2},
        )
        result = ctrl.main()
        assert ctrl.stdout.getvalue() == "1\n2\n"

    def test_err_fd_capture(self):
        intended_result = dedent(
            """\
            this is err test
            this is also err test
            """
        )
        code = "\n".join(
            f"print('{line}', file=err)"
            for line in intended_result.split("\n")
            if line.strip()
        )
        graph_data = {}
        err = io.StringIO()
        ctrl = make_test_controller_instance(
            self.controller_cls,
            code=code,
            graph_data=graph_data,
            stderr=err,
            custom_ns={"err": err},
        )
        result = ctrl.main()
        assert ctrl.stderr.getvalue() == intended_result

    @pytest.mark.parametrize(
        "options, attr_name, cmp_fn",
        [
            (
                {**{n: getLogger("test_logger") for n in ["logger", "_logger"]}},
                "_logger",
                eq,
            ),
            (
                {**{n: True for n in [DefaultVars.IS_LOCAL, "_is_local"]}},
                "_is_local",
                eq,
            ),
            (
                {**{n: {"a": 1, "b": 2} for n in ["custom_ns", "_custom_ns"]}},
                "_custom_ns",
                lambda l, r: all(l[k] == v for k, v in r.items()),
            ),
            (
                {**{n: 200 for n in [DefaultVars.EXEC_MEM_OUT, "_re_mem_size"]}},
                "_re_mem_size",
                lambda l, r: l == r * int(10e6),
            ),
            (
                {**{n: 10 for n in [DefaultVars.EXEC_TIME_OUT, "_re_cpu_time"]}},
                "_re_cpu_time",
                eq,
            ),
            (
                {**{n: 20 for n in [DefaultVars.RAND_SEED, "_rand_seed"]}},
                "_rand_seed",
                eq,
            ),
            (
                {**{n: 10 for n in [DefaultVars.FLOAT_PRECISION, "_float_precision"]}},
                "_float_precision",
                eq,
            ),
            (
                {**{n: v for v in [io.StringIO()] for n in ["stdout", "_stdout"]}},
                "_stdout",
                eq,
            ),
            (
                {**{n: v for v in [io.StringIO()] for n in ["stderr", "_stderr"]}},
                "_stderr",
                eq,
            ),
        ],
    )
    def test_options(self, options: dict, attr_name: str, cmp_fn: Callable):
        code = ""
        graph_data = {}
        ctrl = make_test_controller_instance(
            self.controller_cls, code=code, graph_data=graph_data, options=options
        )
        assert cmp_fn(getattr(ctrl, attr_name), options[attr_name])
        ctrl.main()

        ctrl = make_test_controller_instance(
            self.controller_cls, code=code, graph_data=graph_data, **options
        )
        assert cmp_fn(getattr(ctrl, attr_name), options[attr_name])
        ctrl.main()

    def test_wrong_version(self):
        code = ""
        graph_data = {}
        not_versioned_settings = DefaultVars()
        ctrl = self.controller_cls(
            code=code,
            graph_data=graph_data,
            target_version="wrong_ver",
            default_settings=not_versioned_settings,
        )
        with pytest.raises(SystemExit):
            ctrl.init()

    @pytest.mark.parametrize(
        "code, graph_data",
        [
            (f"{builtin_fn}", {})
            for builtin_fn in [
                "reload('random')",
                "open('temp.file', 'rb')",
                "compile('1 + 1')",
                "eval('1 + 1')",
                "exec('1 + 1')",
                "exit(0)",
                "quit()",
                "help(open)",
                "dir(object)",
                "globals()",
                "locals()",
                "vars()",
                # remove text for better debugging
                "copyright()",
                "credits()",
                "license()",
            ]
        ],
    )
    def test_banning_dangerous_builtin(self, code, graph_data):
        ctrl = make_test_controller_instance(
            self.controller_cls, code=code, graph_data=graph_data
        )
        with pytest.raises(SystemExit):
            ctrl.main()

    @pytest.mark.parametrize(
        "code, input_list, input_stdout_res, err",
        [
            (
                dedent(
                    """\
                    li = [input(i) for i in range(5)]
                    """
                ),
                ["a", "b", "c", "d", "e"],
                "".join(
                    map(
                        lambda x: f"{x[0]}{x[1]}\n",
                        zip(range(5), ["a", "b", "c", "d", "e"]),
                    )
                ),
                False,
            ),
            (
                dedent(
                    """\
                    li = [input(i) for i in range(5)]
                    """
                ),
                ["a", "b", "c", "d"],
                "".join(
                    map(
                        lambda x: f"{x[0]}{x[1]}\n",
                        zip(range(5), ["a", "b", "c", "d"]),
                    )
                ),
                True,
            ),
        ],
    )
    def test_input_list(
        self, code: str, input_list: List[str], input_stdout_res: str, err: bool
    ):
        ctrl = make_test_controller_instance(
            self.controller_cls,
            code=code,
            graph_data={},
            **{DefaultVars.INPUT_LIST: input_list},
        )
        assert ctrl.input_list == input_list

        if err:
            with pytest.raises(SystemExit):
                ctrl.main()
        else:
            ctrl.main()

        assert ctrl.stdout.getvalue() == input_stdout_res

    def test_main_options(self):
        format_val = "format"

        class _SubC(self.controller_cls):
            def format_result(self, result):
                return format_val

        code = "a = 1"
        graph_data = {}
        stream = io.StringIO()
        ctrl = make_test_controller_instance(
            _SubC,
            code=code,
            graph_data=graph_data,
            announcer=ControllerResultAnnouncer(stream),
        )
        with redirect_stdout(stream):
            assert ctrl.main(formats=True) == format_val
            assert not stream.getvalue()

        with redirect_stdout(stream):
            ctrl.main(formats=True, announces=True)
        assert stream.getvalue() == format_val

    @pytest.mark.parametrize(
        "code",
        [
            dedent(
                f"""\
                g = globals()
                {ass}
                """
            )
            for ass in [
                "assert 'nx' in g, f'nx not in globals, {g}'",
                "assert 'networkx' in g, f'networkx not in globals, {g}'",
                f"assert hasattr(nx, '{NX_GRAPH_INJECTION_NAME}'), f'{NX_GRAPH_INJECTION_NAME} not in networkx'",
                f"assert '{NX_GRAPH_INJECTION_NAME}' in g, f'{NX_GRAPH_INJECTION_NAME} not in g'",
                f"assert '{GRAPH_INJECTION_NAME}' in g, f'{GRAPH_INJECTION_NAME} not in g'",
            ]
        ],
    )
    def test_injection(self, code):
        graph_data = {}
        ctrl = make_test_controller_instance(
            self.controller_cls,
            code=code,
            graph_data=graph_data,
            **{DefaultVars.IS_LOCAL: True},
        )
        ctrl.main()

    def test_code_execution(self):
        with open(pathlib.Path(__file__).parent / "../example-code.py") as f:
            code = f.read()

        graph_data = {}
        ctrl = make_test_controller_instance(
            self.controller_cls, code=code, graph_data=graph_data
        )
        ctrl.main()
