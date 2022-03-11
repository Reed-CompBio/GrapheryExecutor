import io
from contextlib import redirect_stdout
from copy import deepcopy
from logging import getLogger
from operator import eq
from textwrap import dedent
from typing import Type, Callable

import pytest
from platform import platform

from ...settings import DefaultVars, SERVER_VERSION
from ...settings.variables import NX_GRAPH_INJECTION_NAME, GRAPH_INJECTION_NAME
from ...utils.controller import GraphController, ControllerResultAnnouncer

_platform = platform()
_settings = DefaultVars()


def make_test_controller_instance(ctrl_cls: Type[GraphController], **kwargs):
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
        self.controller: Type[GraphController] = deepcopy(GraphController)
        self.controller._graph_builder = dict

    @pytest.mark.skip("not available for now")
    def test_resource_restriction(self):
        # TODO add linux resource test with signal
        pass

    @pytest.mark.skip("not available for now")
    def test_graph_creation(self):
        # TODO link with cyjs test
        pass

    @pytest.mark.parametrize(
        "code, graph_data",
        [
            (f"import {mod}", {})
            for mod in ["os", "sys", "posix", "gc", "multiprocessing"]
        ],
    )
    def test_banning_dangerous_import(self, code, graph_data):
        ctrl = make_test_controller_instance(
            self.controller, code=code, graph_data=graph_data
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
        ctrl = make_test_controller_instance(self.controller, code=code, graph_data={})

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
            self.controller, code=code, graph_data=graph_data
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
            self.controller,
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
            self.controller,
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
            self.controller,
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
            self.controller, code=code, graph_data=graph_data, options=options
        )
        assert cmp_fn(getattr(ctrl, attr_name), options[attr_name])
        ctrl.main()

        ctrl = make_test_controller_instance(
            self.controller, code=code, graph_data=graph_data, **options
        )
        assert cmp_fn(getattr(ctrl, attr_name), options[attr_name])
        ctrl.main()

    def test_wrong_version(self):
        code = ""
        graph_data = {}
        not_versioned_settings = DefaultVars()
        ctrl = self.controller(
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
            self.controller, code=code, graph_data=graph_data
        )
        with pytest.raises(SystemExit):
            ctrl.main()

    def test_main_options(self):
        format_val = "format"

        class _SubC(self.controller):
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
            self.controller,
            code=code,
            graph_data=graph_data,
            **{DefaultVars.IS_LOCAL: True},
        )
        ctrl.main()
