from __future__ import annotations

import json
import sys
from io import BytesIO
from types import TracebackType
from typing import Dict, Mapping, NoReturn, Type, Callable, Any, List
from wsgiref.headers import Headers
from wsgiref.simple_server import WSGIRequestHandler

import pytest

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
        "options, slug, err",
        [
            ({}, "/env", ArgumentError),
            ({DefaultVars.IS_LOCAL: True}, "/env", None),
            ({}, "/everything-else", ArgumentError),
        ],
    )
    def test_get(self, options: Mapping, slug: str, err: Type[Exception]):
        mock_env = {**self.mock_env, "PATH_INFO": slug}

        server = ExecutorWSGIServer(
            server_address=self.addr,
            handler_cls=self.handler,
            settings=DefaultVars(**options),
            bind_and_activate=self.bind,
        )
        if err:
            with pytest.raises(err):
                server.do_get(mock_env)
        else:
            server.do_get(mock_env)

    @pytest.mark.parametrize(
        "slug, err",
        [
            ("/run", None),
            ("/everything-else", ArgumentError),
        ],
    )
    def test_post(self, slug: str, err: Type[Exception]):
        class _Server(ExecutorWSGIServer):
            def execute(self, config_str: bytes) -> List[Mapping]:
                return [{}]

        mock_env = {**self.mock_env, "PATH_INFO": slug}
        self.add_content(mock_env, "")

        server = _Server(
            server_address=self.addr,
            handler_cls=self.handler,
            settings=DefaultVars(),
            bind_and_activate=self.bind,
        )
        if err:
            with pytest.raises(err):
                server.do_post(mock_env)
        else:
            server.do_post(mock_env)


class TestResultFormatter:
    pass
