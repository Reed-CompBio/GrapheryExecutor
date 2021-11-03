from __future__ import annotations

import logging
import pathlib
from logging.handlers import TimedRotatingFileHandler
from os import getenv
from typing import Union, List, Mapping

from .recorder import Recorder
from .cache_file_helpers import CacheFolder, USER_DOCS_PATH
from ..seeker import tracer

_CACHE_FOLDER_AUTO_DELETE_ENV_NAME = "CONTROLLER_CACHE_AUTO_DELETE"
is_auto_delete = bool(int(getenv(_CACHE_FOLDER_AUTO_DELETE_ENV_NAME, False)))

_CACHE_PATH_ENV_NAME = "CONTROLLER_CACHE_PATH"
controller_cache_path = pathlib.Path(getenv(_CACHE_PATH_ENV_NAME, USER_DOCS_PATH))


class _Controller:
    _LOG_FILE_NAME = f"graphery_controller_execution.log"

    def __init__(
        self, cache_path=controller_cache_path, auto_delete: bool = is_auto_delete
    ):
        self.main_cache_folder = CacheFolder(cache_path, auto_delete=auto_delete)
        self.log_folder = CacheFolder(cache_path / "log", auto_delete=auto_delete)
        # TODO think about this, and the log file location in the sight class
        self.log_folder.mkdir(parents=True, exist_ok=True)
        self.tracer_cls = tracer
        self.recorder = Recorder()
        self.controller_logger = self._init_logger()

        self.main_cache_folder.__enter__()

        self.tracer_cls.set_new_recorder(self.recorder)

    def _init_logger(self) -> logging.Logger:
        log_file_path = self.log_folder.cache_folder_path / self._LOG_FILE_NAME
        logger = logging.getLogger("controller.tracer")
        logger.setLevel(logging.DEBUG)
        log_file_handler = TimedRotatingFileHandler(
            log_file_path, when="midnight", backupCount=30
        )
        log_file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)-15s::%(levelname)s::%(message)s")
        log_file_handler.setFormatter(formatter)
        logger.addHandler(log_file_handler)
        return logger

    def get_recorded_content(self) -> List[Mapping]:
        return self.recorder.get_change_list()

    def get_processed_result(self) -> List[Mapping]:
        return self.recorder.get_processed_change_list()

    def get_processed_result_json(self) -> str:
        return self.recorder.get_change_list_json()

    def purge_records(self) -> None:
        self.recorder.purge()

    def __call__(
        self,
        dir_name: Union[str, pathlib.Path] = None,
        mode: int = 0o777,
        auto_delete: bool = False,
        *args,
        **kwargs,
    ) -> CacheFolder:
        if dir_name:
            return self.main_cache_folder.add_cache_folder(dir_name, mode, auto_delete)
        else:
            return self.main_cache_folder

    def __enter__(self) -> _Controller:
        self.tracer_cls.set_logger(self.controller_logger)
        # TODO give a prompt that the current session is under this time stamp
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.tracer_cls.set_logger(None)

    def __del__(self) -> None:
        self.main_cache_folder.__exit__(None, None, None)


controller = _Controller()
