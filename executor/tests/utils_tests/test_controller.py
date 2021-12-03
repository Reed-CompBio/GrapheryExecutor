import io
import sys
from copy import deepcopy
from textwrap import dedent
from typing import Type

import pytest
from platform import platform

from ...utils.controller import GraphController, ErrorResult

_platform = platform()


def make_test_controller_instance(ctrl_cls, **kwargs):
    ctrl = ctrl_cls(**kwargs).init()
    ctrl._is_local = True
    return ctrl


def assert_no_error(res):
    if isinstance(res, ErrorResult):
        raise ValueError(res.error_traceback)
    return True


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
        result = ctrl.main()
        assert isinstance(result, ErrorResult)

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
        assert assert_no_error(result) and isinstance(result, list)

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
        result = ctrl.main()
        assert_no_error(result)
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
        assert_no_error(result)
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
        assert_no_error(result)
        assert ctrl.stderr.getvalue() == intended_result

    def test_options(self):
        pass

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
        result = ctrl.main()
        assert isinstance(result, ErrorResult) and (
            "is not supported by Executor" in result.error_traceback
            or "is not defined" in result.error_traceback
        )
