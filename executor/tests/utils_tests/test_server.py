from __future__ import annotations

import json
import sys
from io import BytesIO
from types import TracebackType
from typing import Dict, Mapping, NoReturn, Type, Callable, Any, List
from wsgiref.headers import Headers
from wsgiref.simple_server import WSGIRequestHandler

import pytest

from executor import SERVER_VERSION
from executor.server_utils.main_functions import ExecutorWSGIServer
from executor.server_utils.tools import ExecutionError, ArgumentError, ServerError
from executor.settings import DefaultVars


class _ResponseObj:
    def __init__(self) -> None:
        self.status = None
        self.headers = None
        self.exc_info = None

    def set(self, status, headers, exc_info=None):
        self.status = status
        self.headers = Headers(headers)
        self.exc_info = exc_info


class _ResponseFn(Callable[..., Any]):
    response: _ResponseObj


class TestServer:
    def setup_class(self):
        self.addr = ("127.0.0.1", 9999)
        self.handler = WSGIRequestHandler
        self.default_settings = DefaultVars()
        self.bind = False

        self.mock_env = {
            "SERVER_NAME": "1.0.0.127.in-addr.arpa",
            "GATEWAY_INTERFACE": "CGI/1.1",
            "SERVER_PORT": "29092",
            "REMOTE_HOST": "",
            "CONTENT_LENGTH": "",
            "SCRIPT_NAME": "",
            "SERVER_PROTOCOL": "HTTP/1.1",
            "SERVER_SOFTWARE": "WSGIServer/0.2",
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/env",
            "QUERY_STRING": "",
            "REMOTE_ADDR": "127.0.0.1",
            "CONTENT_TYPE": "text/plain",
            "HTTP_HOST": "127.0.0.1:9999",
            "HTTP_CONNECTION": "close",
            "HTTP_USER_AGENT": "Paw/3.3.2 (Macintosh; OS X/12.0.1) GCDHTTPRequest",
            "wsgi.input": None,
            "wsgi.errors": sys.stderr,
            "wsgi.version": [1, 0],
            "wsgi.run_once": False,
            "wsgi.url_scheme": "http",
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.file_wrapper": "<class 'wsgiref.util.FileWrapper'>",
        }

    @staticmethod
    def add_content(env: Dict, content: str):
        inputs = BytesIO()
        env["wsgi.input"] = inputs
        if isinstance(content, str):
            content = content.encode()
        elif isinstance(content, bytes):
            pass
        else:
            raise ValueError("Cannot write content other than str or bytes")
        env["CONTENT_LENGTH"] = len(content)
        inputs.write(content)

    @pytest.fixture(scope="function")
    def start_response(self) -> _ResponseFn:
        res = _ResponseObj()

        def _response_fn(
            status: str,
            headers: list[tuple[str, str]],
            exc_info: tuple[
                Type[BaseException] | None, BaseException | None, TracebackType | None
            ] = None,
        ):
            res.set(status, headers, exc_info)

        _response_fn.response = res

        yield _response_fn

    @pytest.mark.parametrize(
        "error, expected_msg",
        [
            (
                ExecutionError,
                "Something wrong happens in you're code. Details: test error",
            ),
            (
                ArgumentError,
                "Wrong argument is passed. Error: test error",
            ),
            (
                ServerError,
                "Something wrong happens to the server. Please contact the website admin. Error: test error",
            ),
            (
                ValueError,
                "An unknown exception occurs in the server. Error: test error",
            ),
        ],
    )
    def test_application_error_catching(self, start_response, error, expected_msg):
        class _Server(ExecutorWSGIServer):
            def application_helper(self, environ: Mapping) -> NoReturn:
                raise error("test error")

        server = _Server(
            server_address=self.addr,
            handler_cls=self.handler,
            settings=self.default_settings,
            bind_and_activate=self.bind,
        )
        res: bytes = server.application(self.mock_env, start_response)[0]
        res_obj = json.loads(res.decode())
        assert (errors := res_obj["errors"]) is not None, "errors shouldn't be None"
        error_obj = errors[0]
        assert (
            error_msg := error_obj["message"]
        ) is not None, "error message shouldn't be None"
        assert (
            error_msg == expected_msg
        ), f"unexpected error message: {error_msg}, expecting {expected_msg}"
        assert start_response.response.status == server.default_response_code

    @pytest.mark.parametrize("info, target_info", [("test info", "test info")])
    def test_application_info(self, start_response, info, target_info):
        class _Server(ExecutorWSGIServer):
            def application_helper(self, environ: Mapping) -> str:
                return info

        server = _Server(
            server_address=self.addr,
            handler_cls=self.handler,
            settings=self.default_settings,
            bind_and_activate=self.bind,
        )

        res: bytes = server.application(self.mock_env, start_response)[0]
        res_obj = json.loads(res.decode())

        assert (errors := res_obj["errors"]) is None, f"errors happened: {errors}"
        assert (info := res_obj["info"]) is not None, "info shouldn't be None"
        info_obj = info[0]
        assert (
            info_msg := info_obj["data"]
        ) is not None, "error message shouldn't be None"
        assert (
            info_msg == target_info
        ), f"unexpected error message: {info_msg}, expecting {target_info}"
        assert start_response.response.status == server.default_response_code

    @pytest.mark.parametrize(
        "method, target_result, error",
        [
            ("GET", "get", None),
            ("POST", "post", None),
            (
                "PATCH",
                "patch",
                {
                    "expected_exception": ArgumentError,
                    "match": r"Bad Request: Unsupported Method .*",
                },
            ),
        ],
    )
    def test_application_helper(
        self, method: str, target_result: str, error: Mapping | None
    ):
        class _Server(ExecutorWSGIServer):
            def do_get(self, environ: Mapping):
                return "get"

            def do_post(self, environ: Mapping):
                return "post"

        server = _Server(
            server_address=self.addr,
            handler_cls=self.handler,
            settings=self.default_settings,
            bind_and_activate=self.bind,
        )
        mock_env = {**self.mock_env, "REQUEST_METHOD": method}

        if error:
            with pytest.raises(**error):
                server.application_helper(mock_env)
        else:
            res = server.application_helper(mock_env)
            assert res == target_result

    @pytest.mark.parametrize(
        "options, slug, target_checker, error",
        [
            (
                {},
                "/env",
                None,
                {
                    "expected_exception": ArgumentError,
                    "match": "Bad Request: Cannot access ENV",
                },
            ),
            (
                {DefaultVars.IS_LOCAL: True},
                "/env",
                lambda x: isinstance(x, Mapping),
                None,
            ),
            (
                {},
                "/everything-else",
                None,
                {
                    "expected_exception": ArgumentError,
                    "match": r"Bad Request: Cannot access [\S]+ with method GET",
                },
            ),
        ],
    )
    def test_get(
        self,
        options: Mapping,
        slug: str,
        target_checker: Callable | None,
        error: Mapping | None,
    ):
        mock_env = {**self.mock_env, "PATH_INFO": slug}

        server = ExecutorWSGIServer(
            server_address=self.addr,
            handler_cls=self.handler,
            settings=DefaultVars(**options),
            bind_and_activate=self.bind,
        )
        if error:
            with pytest.raises(**error):
                server.do_get(mock_env)
        else:
            assert target_checker(server.do_get(mock_env))

    @pytest.mark.parametrize(
        "slug, target_checker, error",
        [
            ("/run", lambda x: x == [{}], None),
            (
                "/everything-else",
                None,
                {
                    "expected_exception": ArgumentError,
                    "match": r"Bad Request: Cannot access [\S]+ with method POST",
                },
            ),
        ],
    )
    def test_post(
        self, slug: str, target_checker: Callable | None, error: Mapping | None
    ):
        class _Server(ExecutorWSGIServer):
            def execute(self, config_bytes: bytes) -> List[Mapping]:
                return [{}]

        mock_env = {**self.mock_env, "PATH_INFO": slug}
        self.add_content(mock_env, "")

        server = _Server(
            server_address=self.addr,
            handler_cls=self.handler,
            settings=DefaultVars(),
            bind_and_activate=self.bind,
        )
        if error:
            with pytest.raises(**error):
                server.do_post(mock_env)
        else:
            assert target_checker(server.do_post(mock_env))

    @pytest.mark.parametrize(
        "settings, target_command",
        [
            (
                DefaultVars(),
                [
                    "-t",
                    "5",
                    "-m",
                    "100",
                    "-i",
                    "-r",
                    "0",
                    "-f",
                    "4",
                    "-l",
                    "shell_debug",
                    "local",
                ],
            ),
        ],
    )
    def test_subprocess_command(self, settings: DefaultVars, target_command: List[str]):
        server = ExecutorWSGIServer(
            server_address=self.addr,
            handler_cls=self.handler,
            settings=settings,
            bind_and_activate=self.bind,
        )
        command = server._subprocess_command[1:]
        # we don't want to test the executable path
        assert command == target_command

    @pytest.mark.parametrize(
        "config_bytes, error",
        [
            # correct execution
            (
                json.dumps(
                    {
                        "code": "@tracer('a', 'b')\ndef test(a, b, c):\n    a = a * c\n    b = b * c\n    c = c * c\n    return a + b * c\n\ntest(7, 9, 11)",
                        "graph": '{"data":[],"directed":false,"multigraph":false,"elements":{"nodes":[{"data":{"id":"1","value":1,"name":"1"}},{"data":{"id":"2","value":2,"name":"2"}},{"data":{"id":"3","value":3,"name":"3"}},{"data":{"id":"4","value":4,"name":"4"}},{"data":{"id":"7","value":7,"name":"7"}},{"data":{"id":"5","value":5,"name":"5"}},{"data":{"id":"6","value":6,"name":"6"}}],"edges":[{"data":{"source":1,"target":2}},{"data":{"source":1,"target":3}},{"data":{"source":3,"target":4}},{"data":{"source":4,"target":5}},{"data":{"source":7,"target":5}},{"data":{"source":5,"target":5}}]}}',
                        "version": SERVER_VERSION,
                    }
                ).encode(),
                None,
            ),
            # error execution in code
            (
                json.dumps(
                    {
                        "code": "@tracers('a', 'b')\ndef test(a, b, c):\n    a = a * c\n    b = b * c\n    c = c * c\n    return a + b * c\n\ntest(7, 9, 11)",
                        "graph": '{"data":[],"directed":false,"multigraph":false,"elements":{"nodes":[{"data":{"id":"1","value":1,"name":"1"}},{"data":{"id":"2","value":2,"name":"2"}},{"data":{"id":"3","value":3,"name":"3"}},{"data":{"id":"4","value":4,"name":"4"}},{"data":{"id":"7","value":7,"name":"7"}},{"data":{"id":"5","value":5,"name":"5"}},{"data":{"id":"6","value":6,"name":"6"}}],"edges":[{"data":{"source":1,"target":2}},{"data":{"source":1,"target":3}},{"data":{"source":3,"target":4}},{"data":{"source":4,"target":5}},{"data":{"source":7,"target":5}},{"data":{"source":5,"target":5}}]}}',
                        "version": SERVER_VERSION,
                    }
                ).encode(),
                {
                    "expected_exception": ExecutionError,
                    "match": r"Cannot unload execution subprocess result. Error might have occurred in the execution: .*",
                },
            ),
            (
                json.dumps(
                    {
                        "code": "@tracers('a', 'b')\ndef test(a, b, c):\n    a = a * c\n    b = b * c\n    c = c * c\n    return a + b * c\n\ntest(7, 9, 11)",
                        "graph": '{"data":[],"directed":false,"multigraph":false,"elements":{"nodes":[{"data":{"id":"1","value":1,"name":"1"}},{"data":{"id":"2","value":2,"name":"2"}},{"data":{"id":"3","value":3,"name":"3"}},{"data":{"id":"4","value":4,"name":"4"}},{"data":{"id":"7","value":7,"name":"7"}},{"data":{"id":"5","value":5,"name":"5"}},{"data":{"id":"6","value":6,"name":"6"}}],"edges":[{"data":{"source":1,"target":2}},{"data":{"source":1,"target":3}},{"data":{"source":3,"target":4}},{"data":{"source":4,"target":5}},{"data":{"source":7,"target":5}},{"data":{"source":5,"target":5}}]}}',
                        "version": "wrong_ver",
                    }
                ).encode(),
                {
                    "expected_exception": ExecutionError,
                    "match": fr"Cannot unload execution subprocess result\. Error might have occurred in the execution: An error occurs with exit code 5 \(INIT_ERROR_CODE\)\. Error: Request Version 'wrong_ver' does not match Server Version '{SERVER_VERSION}'",
                },
            ),
            (
                "\n".encode(),
                {
                    "expected_exception": ExecutionError,
                    "match": r"Empty execution result. Error might have occurred in the execution.",
                },
            ),
        ],
    )
    def test_execute(self, config_bytes: bytes, error: Mapping | None):
        server = ExecutorWSGIServer(
            server_address=self.addr,
            handler_cls=self.handler,
            settings=self.default_settings,
            bind_and_activate=self.bind,
        )
        if error:
            with pytest.raises(**error):
                server.execute(config_bytes)
        else:
            server.execute(config_bytes)


class TestResultFormatter:
    pass
