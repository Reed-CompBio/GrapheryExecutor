from __future__ import annotations

from typing import List, Any

from ...utils.cli import arg_parser
from ...settings import DefaultVars, SHELL_SERVER_PARSER_NAME, SHELL_LOCAL_PARSER_NAME
import pytest

from ...utils.logger import shell_debug_logger


class TestArgparse:
    def setup_class(self):
        self.settings = DefaultVars()

    @pytest.mark.skip("not applicable for now")
    def test_settings(self):
        pass

    @pytest.mark.parametrize(
        "server_setting, var, expected",
        [
            (k, v, h)
            for k, v, h in (
                (
                    DefaultVars.SERVER_URL,
                    "127.0.0.4",
                    "127.0.0.4",
                ),
                (
                    DefaultVars.SERVER_PORT,
                    8868,
                    8868,
                ),
                (DefaultVars.ALLOW_OTHER_ORIGIN, None, True),
                (
                    DefaultVars.ACCEPTED_ORIGINS,
                    ["127.0.0.4", "127.0.0.5"],
                    DefaultVars[DefaultVars.ACCEPTED_ORIGINS]
                    + ["127.0.0.4", "127.0.0.5"],
                ),
            )
        ],
    )
    def test_server_args(self, server_setting: str, var: Any, expected: Any):
        # ehhhh, ugly
        args = [SHELL_SERVER_PARSER_NAME]
        arg_name = self.settings.get_var_arg_name(server_setting)

        if isinstance(var, List):
            for v in var:
                args.append(arg_name)
                args.append(str(v))
        else:
            args.append(arg_name)
            if var is not None:
                args.append(str(var))

        parsed_args = arg_parser(args=args)
        assert parsed_args[server_setting] == expected

    @pytest.mark.parametrize(
        "local_settings, var, expected",
        [
            (h, k, v)
            for h, k, v in (
                (DefaultVars.EXEC_TIME_OUT, 10, 10),
                (DefaultVars.EXEC_MEM_OUT, 200, 200),
                (DefaultVars.IS_LOCAL, None, True),
                (DefaultVars.RAND_SEED, "None", None),
                (DefaultVars.RAND_SEED, "10", 10),
                (DefaultVars.FLOAT_PRECISION, "5", 5),
                (DefaultVars.TARGET_VERSION, "3.0.0", "3.0.0"),
                (DefaultVars.LOGGER, "shell_debug", shell_debug_logger),
            )
        ],
    )
    def test_optional_args(self, local_settings: str, var: Any, expected: Any):
        for tp in [SHELL_SERVER_PARSER_NAME, SHELL_LOCAL_PARSER_NAME]:
            arg_name = self.settings.get_var_arg_name(local_settings)
            args = [arg_name]

            if var is not None:
                args.append(str(var))

            args.append(tp)
            parsed_args = arg_parser(args=args)
            assert parsed_args[local_settings] == expected


class TestCLIMain:
    pass
