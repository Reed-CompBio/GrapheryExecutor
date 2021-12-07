from __future__ import annotations

import json
import subprocess
import traceback
from socketserver import BaseRequestHandler
from typing import Mapping, Callable, Any, List
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler
from shutil import which

from .tools import (
    ServerError,
    ServerResultFormatter,
    ArgumentError,
    ExecutionError,
)
from .. import SERVER_VERSION
from ..settings import DefaultVars, SHELL_LOCAL_PARSER_NAME


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
                    message=f"Something wrong happens in you're code. Details: {e}",
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

        # TODO restrict info page
        # info page
        if method == "GET" and path == "/env":
            return environ

        # entry point check
        if method != "POST" or path != "/run":
            raise ArgumentError("Bad Request: Wrong Methods.")

        # get request content
        request_body = environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"]))

        return self.execute(request_body)

    @property
    def _subprocess_command(self) -> str:
        # TODO fix this; don't use str literal

        proc_name = which("graphery_executor")
        if proc_name is None:
            raise ServerError("Cannot find executor program in system path")

        args = [proc_name]
        for k in self.settings.general_shell_var.keys():
            arg_name = self.settings.get_var_arg_name(k)
            args.append(arg_name)
            if self.settings.var_arg_has_value(k):
                args.append(str(self.settings[k]))

        args.append(SHELL_LOCAL_PARSER_NAME)
        return " ".join(args)

    def execute(self, config_str: str) -> List[Mapping]:
        proc = subprocess.Popen(
            self._subprocess_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        try:
            stdout, stderr = proc.communicate(
                config_str.encode(),
                timeout=self.settings[self.settings.EXEC_TIME_OUT],
            )
        except subprocess.TimeoutExpired:
            proc.kill()
            raise ExecutionError("Execution Timed out.")
        else:
            stdout, stderr = stdout.decode(), stderr.decode()
            try:
                res = json.loads(stdout)
            except json.JSONDecodeError:
                raise ExecutionError(
                    stdout[: stdout.index("\n")], f"{stdout}\n{stderr}"
                )

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
        print("Settings: ")
        for k, v in httpd.settings.vars.items():
            print("{: <27}: {: <10}".format(k, str(v)))
        # ========== settings log end
        print("Starting server...")
        httpd.serve_forever()
