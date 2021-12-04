from __future__ import annotations

import json
from typing import Mapping, Callable, Any, List
from wsgiref.simple_server import make_server

from .params import (
    ONLY_ACCEPTED_ORIGIN,
    ACCEPTED_ORIGIN,
    REQUEST_GRAPH_NAME,
    REQUEST_CODE_NAME,
    REQUEST_VERSION_NAME,
)
from .utils import (
    create_error_response,
    create_data_response,
)
from .. import SERVER_VERSION
from ..settings import DefaultVars


class StringEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        try:
            json.JSONEncoder.default(self, obj)
        except TypeError:
            return str(obj)


def run_server(setting: DefaultVars = DefaultVars) -> None:
    url = setting[setting.SERVER_URL]
    port = setting[setting.SERVER_PORT]
    with make_server(url, port, application) as httpd:
        print(f"Server Ver: {SERVER_VERSION}. Press <ctrl+c> to stop the server.")
        print(f"Ready for Python code on {url}:{port} ...")
        print(f"Time out is set to {setting[setting.EXEC_TIME_OUT]}s.")
        print(f"Memory restriction is set to {setting[setting.EXEC_MEM_OUT]}s.")
        print(f"Allow other origins? `{setting[setting.ALLOW_OTHER_ORIGIN]}`.")
        print(
            f"Request graph name: `{setting[setting.REQUEST_DATA_GRAPH_NAME]}`; \n"
            f"Request code name: `{setting[setting.REQUEST_DATA_CODE_NAME]}`; \n"
            f"Request version name: `{setting[setting.REQUEST_DATA_VERSION_NAME]}`; "
        )
        print("Settings: ")
        for k, v in setting.vars.items():
            print("{: <27}: {: <10}".format(k, v))
        httpd.serve_forever()


def application(environ: Mapping, start_response: Callable) -> List:
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

    # origin check
    origin = environ.get("HTTP_ORIGIN", "")
    if ONLY_ACCEPTED_ORIGIN and origin.find(ACCEPTED_ORIGIN) == -1:
        content = create_error_response(
            f"The ORIGIN, {ACCEPTED_ORIGIN}, is not accepted."
        )
    else:
        try:
            content = application_helper(environ)
        except Exception as e:
            content = create_error_response(
                f"An exception occurs in the server. Error: {e}"
            )

    headers.append(("Access-Control-Allow-Origin", origin))
    start_response(response_code, headers)
    return [json.dumps(content, cls=StringEncoder).encode()]


def application_helper(environ: Mapping) -> Mapping:
    method = environ.get("REQUEST_METHOD")
    path = environ.get("PATH_INFO")

    # info page
    if method == "GET" and path == "/env":
        return create_data_response(environ)

    # entry point check
    if method != "POST" or path != "/run":
        return create_error_response("Bad Request: Wrong Methods.")

    # get request content
    request_body = environ["wsgi.input"].read(int(environ["CONTENT_LENGTH"]))
    request_json_object = json.loads(request_body)
    if (
        REQUEST_VERSION_NAME not in request_json_object
        or request_json_object[REQUEST_VERSION_NAME] != SERVER_VERSION
    ):
        return create_error_response(
            "The current version of your local server (%s) does not match version of the web "
            'app ("%s"). Please download the newest version at '
            "https://github.com/FlickerSoul/Graphery/releases."
            % (
                SERVER_VERSION,
                request_json_object.get(REQUEST_VERSION_NAME, "Not Exist"),
            )
        )

    if REQUEST_CODE_NAME not in request_json_object:
        return create_error_response("No Code Snippets Embedded In The Request.")

    if REQUEST_GRAPH_NAME not in request_json_object:
        return create_error_response("No Graph Intel Embedded In The Request.")

    # execute program with timed out
    return None
