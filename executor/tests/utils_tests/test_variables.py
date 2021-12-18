from __future__ import annotations

from copy import deepcopy

import pytest
import os

from ...settings import DefaultVars
from ...utils.logger import shell_debug_logger


class TestVariables:
    @pytest.fixture(scope="class")
    def original_environ(self):
        yield deepcopy(os.environ)

    @pytest.fixture(scope="function")
    def reset_environ(self, original_environ):
        os.environ.clear()
        os.environ.update(original_environ)

    @pytest.mark.parametrize(
        "env_name, env_value, target",
        [
            (DefaultVars.SERVER_URL, "127.0.0.7", "127.0.0.7"),
            (DefaultVars.SERVER_PORT, "7599", 7599),
            (DefaultVars.ALLOW_OTHER_ORIGIN, "False", False),
            (
                DefaultVars.ACCEPTED_ORIGINS,
                '["127.0.0.1", "127.0.0.9"]',
                ["127.0.0.1", "127.0.0.9"],
            ),
            (DefaultVars.LOGGER, "shell_debug", shell_debug_logger),
            (DefaultVars.EXEC_TIME_OUT, "9", 9),
            (DefaultVars.EXEC_MEM_OUT, "200", 200),
            (DefaultVars.IS_LOCAL, "True", True),
            (DefaultVars.RAND_SEED, "10", 10),
            (DefaultVars.RAND_SEED, "None", None),
            (DefaultVars.FLOAT_PRECISION, "8", 8),
            (DefaultVars.REQUEST_DATA_VERSION_NAME, "3.0.0", "3.0.0"),
            (DefaultVars.REQUEST_DATA_CODE_NAME, "codes", "codes"),
            (DefaultVars.REQUEST_DATA_GRAPH_NAME, "graphs", "graphs"),
            (DefaultVars.REQUEST_DATA_OPTIONS_NAME, "option", "option"),
        ],
    )
    def test_read_from_env(self, reset_environ, env_name, env_value, target):
        os.environ[DefaultVars.make_shell_env_name(env_name)] = env_value
        s = DefaultVars()
        res = s[env_name]
        assert (
            res == target
        ), f"result from env ({res}) is different from what's expected {target}"

    def test_read_from_empty_env(self, reset_environ):
        s = DefaultVars()
        s.read_from_env(all_args=True)
        for k, v in s.vars.items():
            target = DefaultVars[k]
            assert (
                v == target
            ), f"result from empty env ({v}) is different from defaults {target}"
