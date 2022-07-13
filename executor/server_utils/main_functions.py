from __future__ import annotations

import json
import subprocess
import time
import traceback
from socketserver import BaseRequestHandler
from typing import Mapping, Callable, List
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler
from shutil import which

from .tools import (
    ServerError,
    ServerResultFormatter,
    ArgumentError,
    ExecutionError,
)
from .. import SERVER_VERSION
from ..settings import DefaultVars, SHELL_LOCAL_PARSER_NAME, PROG_NAME


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
        self.logger = settings.v.LOGGER
        self.set_app(self.application)

        self.default_response_code = "200 OK"
        self.base_response_header = [
            ("Content-Type", "application/json"),
            (
                "Access-Control-Allow-Headers",
                ", ".join(
                    (
                        "Accept",
                        "Accept-Encoding",
                        "Content-Type",
                        "Origin",
                        "User-Agent",
                        "X-Requested-With",
                    )
                ),
            ),
        ]

        self.logger.debug("initialized logger WSGI Server")

    def application(self, environ: Mapping, start_response: Callable) -> List[bytes]:
        formatter = ServerResultFormatter(self.logger)

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
                formatter.add_info(result=self.application_helper(environ))
            except ExecutionError as e:
                formatter.add_error(
                    message=f"Something wrong happens in you're code. Details: {e}",
                    traceback=e.traceback,
                )
            except ArgumentError as e:
                formatter.add_error(
                    message=f"Wrong argument is passed. Error: {e}",
                    traceback=traceback.format_exc(),
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

        headers = [*self.base_response_header, ("Access-Control-Allow-Origin", origin)]
        start_response(self.default_response_code, headers)
        return [formatter.format_server_result().encode()]

    def application_helper(self, environ: Mapping) -> Mapping | List[Mapping]:
        method: str = environ.get("REQUEST_METHOD")

        match method:
            case "GET":
                return self.do_get(environ)
            case "POST":
                return self.do_post(environ)
            case _:
                raise ArgumentError(f"Bad Request: Unsupported Method {method}.")

    def do_get(self, environ: Mapping):
        slug = environ.get("PATH_INFO")
        match slug:
            case "/env":
                if self.settings.v.IS_LOCAL:
                    return environ
                else:
                    raise ArgumentError("Bad Request: Cannot access ENV")
            case _:
                raise ArgumentError(
                    f"Bad Request: Cannot access {slug} with method GET"
                )

    def do_post(self, environ: Mapping):
        slug = environ.get("PATH_INFO")
        match slug:
            case "/run":
                request_body: bytes = environ["wsgi.input"].read(
                    int(environ["CONTENT_LENGTH"])
                )
                return self.execute(request_body)
            case _:
                raise ArgumentError(
                    f"Bad Request: Cannot access {slug} with method POST"
                )

    @property
    def _subprocess_command(self) -> List[str]:
        proc_name = which(PROG_NAME)
        if proc_name is None:
            raise ServerError("Cannot find executor program in system path")

        args = [proc_name]
        for k in self.settings.general_shell_var.keys():
            arg_name = self.settings.get_var_arg_name(k)
            args.append(arg_name)
            if self.settings.var_arg_has_value(k):
                args.append(str(self.settings[k]))
            if k == self.settings.LOGGER:
                args.append("shell_debug")

        args.append(SHELL_LOCAL_PARSER_NAME)
        return args

    def execute(self, config_bytes: bytes) -> List[Mapping]:
        command = self._subprocess_command
        start_time = time.process_time()
        self.logger.debug(f"opening subprocess with command {command}")
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = proc.communicate(
                config_bytes,
                timeout=self.settings[self.settings.EXEC_TIME_OUT],
            )
            self.logger.info(f"finished running {command} successfully")
        except Exception as e:
            self.logger.warning(f"running failed: {command}")
            stdout, stderr = proc.communicate()
            proc.kill()
            raise ExecutionError(
                f"Error happened during execution subprocess. Error: {e}\n"
                f"stdout: \n",
                f"{stdout}\n" f"stderr: \n" f"{stderr}\n",
            )
        finally:
            end_time = time.process_time()
            self.logger.info(f"execution uses {end_time - start_time} seconds")

        if not stdout:
            self.logger.warning(f"got empty running result: {command}")
            raise ExecutionError(
                "Empty execution result. Error might have occurred in the execution.",
                stderr.decode() if stderr else "Empty stderr output",
            )

        stdout, stderr = stdout.decode(), stderr.decode()

        try:
            res = json.loads(stdout)
        except json.JSONDecodeError:
            raise ExecutionError(
                f"Cannot unload execution subprocess result. Error might have occurred in the execution: {stdout}",
                stderr,
            )

        return res


def run_server(settings: DefaultVars) -> None:
    host = settings.v.SERVER_URL
    port = settings.v.SERVER_PORT
    logger = settings.v.LOGGER

    with ExecutorWSGIServer(
        server_address=(host, port), handler_cls=WSGIRequestHandler, settings=settings
    ) as httpd:
        # ========== settings log
        logger.info(f"Server Ver: {SERVER_VERSION}. Press <ctrl+c> to stop the server.")
        logger.info(f"Ready for Python code on {host}:{port} ...")
        logger.info("Settings: ")
        for k, v in httpd.settings.vars.items():
            logger.info("{: <27}: {: <10}".format(k, str(v)))
        # ========== settings log end
        logger.info("Starting server...")
        httpd.serve_forever()
