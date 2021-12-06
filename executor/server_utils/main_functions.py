from __future__ import annotations

import json
import subprocess
import traceback
from socketserver import BaseRequestHandler
from typing import Mapping, Callable, Any, List, Dict
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler

from networkx import Graph
from .tools import (
    ServerError,
    ServerResultFormatter,
    ArgumentError,
    ExecutionError,
)
from .. import SERVER_VERSION
from ..settings import DefaultVars


class StringEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        try:
            json.JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)


class ExecutorWSGIServer(WSGIServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_cls: Callable[..., BaseRequestHandler],
        settings: DefaultVars,
        bind_and_activate=True,
    ):
        super().__init__(
            server_address, handler_cls, bind_and_activate=bind_and_activate
        )
        self.settings = settings
        self.set_app(self.application)

    def application(self, environ: Mapping, start_response: Callable) -> List:
        response_code = "200 OK"
        headers = [
            ("Content-Type", "application/json"),
            (
                "Access-Control-Allow-Headers",
                ", ".join(
                    (
                        "accept",
                        "accept-encoding",
                        "content-type",
                        "origin",
                        "user-agent",
                        "x-requested-with",
                    )
                ),
            ),
        ]

        formatter = ServerResultFormatter()

        # origin check
        origin = environ.get("HTTP_ORIGIN", "")
        allow_other_origin: bool = self.settings[self.settings.ACCEPTED_ORIGINS]
        accepted_origin: List = self.settings[self.settings.ACCEPTED_ORIGINS]

        if not allow_other_origin and accepted_origin.count(origin) == 0:
            formatter.add_error(
                message=f"The ORIGIN, {origin}, is not accepted.", traceback=None
            )
        else:
            try:
                formatter.add_info(data=self.application_helper(environ))
            except ExecutionError as e:
                formatter.add_error(
                    message=f"Something wrong happens in you're code. Details: ",
                    traceback=e.traceback,
                )
            except ArgumentError as e:
                formatter.add_error(
                    message=f"Wrong argument is passed. Error: {e}",
                    traceback=None,
                )
            except ServerError as e:
                formatter.add_error(
                    message=f"Something wrong happens to the server. Please contact the website admin. Error: {e}",
                    traceback=traceback.format_exc(),
                )
            except Exception as e:
                formatter.add_error(
                    message=f"An unknown exception occurs in the server. Error: {e}",
                    traceback=traceback.format_exc(),
                )

        headers.append(("Access-Control-Allow-Origin", origin))
        start_response(response_code, headers)
        return [
            json.dumps(formatter.format_server_result(), cls=StringEncoder).encode()
        ]

    def application_helper(self, environ: Mapping) -> Mapping | List[Mapping]:
        method: str = environ.get("REQUEST_METHOD")
        path: str = environ.get("PATH_INFO")

        # info page
        if method == "GET" and path == "/env":
            return environ

        # entry point check
        if method != "POST" or path != "/run":
            raise ArgumentError("Bad Request: Wrong Methods.")

        # get request content
        request_body = environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"]))
        request_json_object: Mapping = json.loads(request_body)

        if (
            code_field_name := self.settings[self.settings.REQUEST_DATA_CODE_NAME]
        ) not in request_json_object:
            raise ArgumentError("No Code Snippets Embedded In The Request.")
        else:
            code = request_json_object.get(code_field_name)

        if (
            graph_field_name := self.settings[self.settings.REQUEST_DATA_GRAPH_NAME]
        ) not in request_json_object:
            raise ArgumentError("No Graph Intel Embedded In The Request.")
        else:
            graph = request_json_object.get(graph_field_name)

        options = request_json_object.get(
            self.settings[self.settings.REQUEST_DATA_OPTIONS_NAME]
        )

        return self.execute(code, graph, options)

    def execute(
        self, code: str, graph_data: str | Dict | Graph, options: Mapping = None
    ) -> List[Mapping]:
        options = options or {}
        # TODO fix this
        proc = subprocess.Popen("graphery_executor")
        try:
            try:
                stdout, stderr = proc.communicate(
                    timeout=self.settings[self.settings.EXEC_TIME_OUT]
                )
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
        except Exception as e:
            raise ServerError(
                f"unknown error happens when communicating with executor. Error: {e}"
            )

        stdout, stderr = stdout.decode(), stderr.decode()

        try:
            res = json.loads(stdout)
        except json.JSONDecodeError:
            raise ExecutionError(stdout.split("\n")[0], f"{stdout}\n{stderr}")
        except Exception as e:
            raise ServerError(
                f"unknown error happens when decoding stdout from executor. Error: {e}"
            )
        else:
            return res


def make_server(
    host: str,
    port: int,
    settings: DefaultVars = DefaultVars,
    server_class=ExecutorWSGIServer,
    handler_class=WSGIRequestHandler,
):
    """Create a new WSGI server listening on `host` and `port` for `app` with `settings`"""
    server = server_class((host, port), handler_class, settings)
    return server


def run_server(settings: DefaultVars = DefaultVars) -> None:
    url = settings[settings.SERVER_URL]
    port = settings[settings.SERVER_PORT]
    with make_server(url, port, settings) as httpd:
        # ========== settings log
        print(f"Server Ver: {SERVER_VERSION}. Press <ctrl+c> to stop the server.")
        print(f"Ready for Python code on {url}:{port} ...")
        print(f"Time out is set to {httpd.settings[httpd.settings.EXEC_TIME_OUT]}s.")
        print(
            f"Memory restriction is set to {httpd.settings[httpd.settings.EXEC_MEM_OUT]}s."
        )
        print(
            f"Allow other origins? `{httpd.settings[httpd.settings.ALLOW_OTHER_ORIGIN]}`."
        )
        print(
            f"Request graph name: `{httpd.settings[httpd.settings.REQUEST_DATA_GRAPH_NAME]}`; \n"
            f"Request code name: `{httpd.settings[httpd.settings.REQUEST_DATA_CODE_NAME]}`; \n"
            f"Request options name: `{httpd.settings[httpd.settings.REQUEST_DATA_OPTIONS_NAME]}`; "
        )
        print("Settings: ")
        for k, v in httpd.settings.vars.items():
            print("{: <27}: {: <10}".format(k, v))
        # ========== settings log end
        httpd.serve_forever()
