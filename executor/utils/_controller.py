from __future__ import annotations

from copy import deepcopy, copy

import sys as _sys
import types
from io import StringIO
from logging import Logger
from typing import (
    Sequence,
    Type,
    Callable,
    TypeAlias,
    TypeVar,
    Generic,
    Mapping,
    List,
    Generator,
    Any,
    ParamSpec,
    MutableMapping,
    Final,
    Dict,
)
from contextlib import redirect_stdout, redirect_stderr

from .logger import void_logger
from ._recorder import Recorder as _recorder_cls
from ..seeker import tracer as _tracer_cls
from ..settings import DefaultVars, DefaultENVVars

import networkx as nx
from traceback import format_exc

try:
    import resource

    resource_module_loaded = True
except ImportError:
    resource = None
    resource_module_loaded = False

__all__ = ["Controller", "GraphController"]

LAYER_TYPE: TypeAlias = "Callable[[Controller], None]"

_T = TypeVar("_T")
_P = ParamSpec("_P")


_DEFAULT_MODULE_NAME: Final[str] = "__main__"
_DEFAULT_FILE_NAME: Final[str] = "<graphery_main>"


def _builtins_getter(name: str) -> Any:
    """
    get builtin fns by name
    :param name: name of builtin fn
    :return: the fn
    :raise: AttributeError if the name is not found
    """
    if isinstance(__builtins__, Mapping):
        # noinspection PyUnresolvedReferences
        return __builtins__[name]
    elif isinstance(__builtins__, types.ModuleType):
        return getattr(__builtins__, name)
    else:
        raise TypeError(f"Unknown __builtins__ type {type(__builtins__)}")


def _builtins_iterator() -> Generator[tuple[str, Any], Any, None]:
    """
    get an iterator for builtins
    :return: A generator of (str, Any) type
    """
    if isinstance(__builtins__, Mapping):
        # noinspection PyUnresolvedReferences
        for k, v in __builtins__.items():
            yield k, v
    elif isinstance(__builtins__, types.ModuleType):
        for k in dir(__builtins__):
            yield k, _builtins_getter(k)
    else:
        raise TypeError(f"Unknown __builtins__ type {type(__builtins__)}")


# system stdout and stderr
_ORIGINAL_STDOUT = _sys.stdout
_ORIGINAL_STDERR = _sys.stderr


class Controller(Generic[_T]):
    """
    Controller class that controls the execution of some `runner` function
    """

    _tracer = _tracer_cls

    def __init__(
        self,
        *,
        runner: Callable[_P, _T],
        default_settings: DefaultVars = DefaultENVVars,
        options: Mapping = None,
        **kwargs,
    ) -> None:
        options = {**(options or {}), **kwargs}

        # register logger
        self._logger: Logger = options.get("logger", void_logger)

        # register control layers
        self._init_layers: List[LAYER_TYPE] = [*self._make_init_layers()]
        self._logger.debug(f"registered init layers: {self._init_layers}")
        self._prep_layers: List[LAYER_TYPE] = [*self._make_prep_layers()]
        self._logger.debug(f"registered prep layers: {self._prep_layers}")
        self._post_layers: List[LAYER_TYPE] = [*self._make_post_layers()]
        self._logger.debug(f"registered post layers: {self._post_layers}")

        # register runner
        self._runner: Callable[_P, _T] = runner
        self._logger.debug(f"registered runner")

        # context on flag
        self._in_context: bool = False

        # local flag
        self._is_local: bool = options.get("is_local", False)

        self._custom_ns: Dict[str, types.ModuleType] = options.get("custom_ns", {})

        # sandbox
        self._default_settings = default_settings
        self._user_globals: Dict[str, Any] = {"__name__": _DEFAULT_MODULE_NAME}
        self._re_mem_size = options.get(
            "re_mem_size",
            self._default_settings[self._default_settings.EXEC_MEM_OUT],
        ) * int(
            10e6
        )  # convert mb to bytes
        self._re_cpu_time = options.get(
            "re_cpu_time", self._default_settings[self._default_settings.EXEC_TIME_OUT]
        )

        self._use_pool = options.get("use_pool", False)

        # std
        self._stdout = options.get("stdout", StringIO())
        self._stderr = options.get("stderr", StringIO())

        # args
        self._BUILTIN_IMPORT: Final = _builtins_getter("__import__")
        self._ALLOWED_STDLIB_MODULE_IMPORTS: Final = (
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
        )

        self._DEL_MODULES: Final = ("os", "sys", "posix", "gc")
        self._BANNED_BUILTINS: Final = [
            "reload",
            "open",
            "compile",
            "file",
            "eval",
            "exec",
            "execfile",
            "exit",
            "quit",
            "help",
            "dir",
            "globals",
            "locals",
            "vars",
            # remove text for better debugging
            "copyright",
            "credits",
            "license",
        ]

    # ===== global helpers =====
    def _create_restrict_import(self) -> Callable:
        """
        make a restricted version of __import__ that only imports whitelisted modules
        :return: the customized __import__ wrapper
        """

        def __restricted_import__(*args):
            # Restrict imports to a whitelist
            # filter args to ONLY take in real strings so that someone can't
            # subclass str and bypass the 'in' test on the next line
            args = [e for e in args if type(e) is str]

            whitelisted_imports = self._ALLOWED_STDLIB_MODULE_IMPORTS

            importing_name = args[0]

            if importing_name in self._custom_ns:
                return self._custom_ns[importing_name]
            elif importing_name in whitelisted_imports:
                imported_mod = self._BUILTIN_IMPORT(*args)

                # somewhat weak protection against imported modules that contain one
                # of these troublesome builtins. again, NOTHING is foolproof ...
                # just more defense in depth :)
                for mod in self._DEL_MODULES:
                    if hasattr(imported_mod, mod):
                        delattr(imported_mod, mod)

                return imported_mod
            else:
                raise ImportError(f"{importing_name} not supported.")

        return __restricted_import__

    @staticmethod
    def _create_banned_builtins(fn: Callable | str) -> Callable:
        """
        make a banned builtin function
        :param fn: The function to be wrapped
        :return: a banned function wrapper
        """

        def _err_fn(*_, **__):
            raise Exception(
                f"'{fn}' is not supported by Executor. \n"
                f"If you're using a local instance, please try to turn on is_local_flag \n"
            )

        return _err_fn

    def _create_raw_input(self) -> Callable:
        """
        make a `input` function wrapper. Currently the input function is banned.
        :return: the input wrapper
        """
        # def _input(prompt = ""):
        #     if input_string_queue:
        #         input_str = input_string_queue.pop(0)
        #
        #         # write the prompt and user input to stdout, to emulate what happens
        #         # at the terminal
        #         sys.stdout.write(str(prompt))  # always convert prompt into a string
        #         sys.stdout.write(input_str + "\n")  # newline to simulate the user hitting Enter
        #         return input_str
        #     raise RawInputException(str(prompt))  # always convert prompt into a string
        return self._create_banned_builtins("input")

    @staticmethod
    def _create_open() -> Callable:
        def _open(*_, **__):
            raise Exception(
                "open() is not supported by Executor. \n"
                "Instead use io.StringIO() to simulate a file. \n"
                "Here is an example: https://goo.gl/uNvBGl \n"
                "If you're using a local instance, please try to turn on is_local_flag \n"
            )

        return _open

    def _channel_fd(self) -> None:
        """
        set how the default file descriptors like stdout are channeled
        :return: None
        """
        pass

    def _use_original_fd(self) -> None:
        """
        restore the default file descriptors
        :return: None
        """
        pass

    # ===== global helpers end =====

    # ===== collect basic attrs =====

    def _collect_builtins(self) -> None:
        """
        create a custom builtins dictionary for later execution and append it to the global dict
        :return: None
        """
        _user_builtins = {}
        for k, v in _builtins_iterator():
            if k == "open" and not self._is_local:
                _user_builtins[k] = self._create_open()
            elif k in self._BANNED_BUILTINS and not self._is_local:
                _user_builtins[k] = self._create_banned_builtins(k)
            elif k == "__import__" and not self._is_local:
                _user_builtins[k] = self._create_restrict_import()
            else:
                if k == "raw_input":
                    _user_builtins[k] = self._create_raw_input
                elif k == "input":
                    _user_builtins[k] = self._create_raw_input
                else:
                    _user_builtins[k] = v
        self._user_globals["__builtins__"] = _user_builtins

    def _collect_globals(self) -> None:
        """
        collect other specified namespace
        :return: None
        """
        self._user_globals.update(copy(self._custom_ns))
        self._logger.debug(f"updated global with custom_ns {self._custom_ns}")

    def _update_globals(self, name: str, val: Any) -> None:
        """
        update globals namespace with name and val
        :param name: the name
        :param val: the value
        :return: None
        """
        self._user_globals[name] = val
        self._logger.debug(f"updated global attr {name} with {val} ")

    # ===== collect basic attrs end =====

    # ===== custom modules =====
    @staticmethod
    def _make_custom_module(
        module_name: str,
        module_attrs: Mapping[str, Any],
    ) -> types.ModuleType:
        _mod = types.ModuleType(module_name)
        for k, v in module_attrs.items():
            setattr(_mod, k, v)
        return _mod

    def _add_custom_module(self, module: types.ModuleType, *aliases: str) -> None:
        if len(aliases) < 1:
            raise ValueError("module should have at least a name")
        for alias in aliases:
            self._custom_ns[alias] = module

    # ===== custom modules end =====

    # ===== restrict sandbox =====
    def _restrict_resources(self) -> None:
        """
        use resource library to restrict cpu and memory usage when the platform is Linux
        :return: None
        """
        from platform import system

        if system() == "Linux":
            assert resource is not None
            resource.setrlimit(
                resource.RLIMIT_AS, (self._re_mem_size, self._re_cpu_time)
            )
            resource.setrlimit(
                resource.RLIMIT_CPU, (self._re_cpu_time, self._re_cpu_time)
            )
        #
        # # protect against unauthorized filesystem accesses ...
        # resource.setrlimit(
        #     resource.RLIMIT_NOFILE, (0, 0)
        # )  # no opened files allowed

        # VERY WEIRD. If you activate this resource limitation, it
        # ends up generating an EMPTY trace for the following program:
        #   "x = 0\nfor i in range(10):\n  x += 1\n   print x\n  x += 1\n"
        # (at least on my Webfaction hosting with Python 2.7)
        # resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))  # (redundancy for paranoia)

    def _restrict_sandbox(self):
        """
        sandbox the execution environment by removing posix, os, os.path, sys
        and use resources lib to restrict resource usages if possible
        :return:
        """
        if resource_module_loaded and (not self._is_local):
            self._restrict_resources()

            # The posix module is a built-in and has a ton of OS access
            # facilities ... if you delete those functions from
            # sys.modules['posix'], it seems like they're gone EVEN IF
            # someone else imports posix in a roundabout way. Of course,
            # I don't know how foolproof this scheme is, though.
            # (It's not sufficient to just "del sys.modules['posix']";
            #  it can just be reimported without accessing an external
            #  file and tripping RLIMIT_NOFILE, since the posix module
            #  is baked into the python executable, ergh. Actually DON'T
            #  "del sys.modules['posix']", since re-importing it will
            #  refresh all of the attributes. ergh^2)
            for a in dir(_sys.modules["posix"]):
                delattr(_sys.modules["posix"], a)
            del _sys.modules["posix"]

            # do the same with os
            for a in dir(_sys.modules["os"]):
                # 'path' is needed for __restricted_import__ to work
                # and 'stat' is needed for some errors to be reported properly
                # and 'fspath' is needed for logging
                if a not in ("path", "fspath", "stat", "PathLike", "_check_methods"):
                    delattr(_sys.modules["os"], a)
            # ppl can dig up trashed objects with gc.get_objects()
            # noinspection PyUnresolvedReferences
            import gc

            for a in dir(_sys.modules["gc"]):
                delattr(_sys.modules["gc"], a)
            del _sys.modules["gc"]

            # sys.modules contains an in-memory cache of already-loaded
            # modules, so if you delete modules from here, they will
            # need to be re-loaded from the filesystem.
            #
            # Thus, as an extra precaution, remove these modules so that
            # they can't be re-imported without opening a new file,
            # which is disallowed by resource.RLIMIT_NOFILE
            #
            # Of course, this isn't a foolproof solution by any means,
            # and it might lead to UNEXPECTED FAILURES later in execution.
            del _sys.modules["os"]
            del _sys.modules["os.path"]
            del _sys.modules["platform"]
            # TODO remove Pool maybe?
            del _sys.modules["sys"]

    # ===== restrict sandbox end =====

    # ===== layer makers  =====

    @classmethod
    def _make_init_layers(cls) -> Sequence[LAYER_TYPE]:
        """
        init layer maker, should be overwritten by subclasses if necessary
        :return: sequence of layer functions
        """
        return ()

    @classmethod
    def _make_prep_layers(cls) -> Sequence[LAYER_TYPE]:
        """
        prep layer maker, should be overwritten by subclasses if necessary
        :return: sequence of layer functions
        """
        return (
            cls._collect_builtins,
            cls._collect_globals,
            cls._channel_fd,
        )

    @classmethod
    def _make_post_layers(cls) -> Sequence[LAYER_TYPE]:
        """
        post layer maker, should be overwritten by subclasses if necessary
        :return: sequence of layer functions
        """
        return (cls._use_original_fd,)

    # ===== layer makers end =====

    # ===== processes =====
    def _init_process(self) -> None:
        """
        run init layers
        :return: None
        """
        for init_fn in self._init_layers:
            init_fn(self)

        self._logger.debug("finished executing init process")

    def _prep_process(self) -> None:
        """
        run prep layers
        :return: None
        """
        for pre_fn in self._prep_layers:
            pre_fn(self)
        self._logger.debug("finished executing prep process")

    def _post_process(self) -> None:
        """
        run post layers
        :return: None
        """
        for post_fn in self._post_layers:
            post_fn(self)

        self._logger.debug("finished executing post process")

    # ===== processes end =====

    # ===== enter context flag switches =====
    def _enter_context(self) -> None:
        """
        enter context flag switch
        :return: None
        """
        self._in_context = True
        self._logger.debug("entered context")

    def _exit_context(self) -> None:
        """
        exit context flag switch
        :return:
        """
        self._in_context = False
        self._logger.debug("exited context")

    # ===== enter context flag switches =====

    # ===== basic structures =====

    def __call__(self, *args, **kwargs) -> Controller[_T]:
        """
        init process caller
        intended to usage: `controller_instance().main()`
        :param args:
        :param kwargs:
        :return: self
        """
        self._init_process()
        return self

    def __enter__(self) -> Controller[_T]:
        """
        context helper
        :return: None
        """
        self._enter_context()
        self._prep_process()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        context helper
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return: None
        """
        self._exit_context()
        self._post_process()

    def _run(self, *args: _P.args, **kwargs: _P.kwargs) -> _T | None:
        """
        run the internal runner
        :param args: runner args
        :param kwargs: runner kwargs
        :return: whatever the runner returns
        """
        self._logger.debug(
            "start runner with\n" f"args: {args}\n" f"and kwargs: {kwargs}\n"
        )
        if self._use_pool:
            from multiprocessing import Pool

            with Pool(processes=1) as pool:
                try:
                    promise = pool.apply_async(self._runner, args=args, kwds=kwargs)
                    self._logger.debug("applied run async in main")
                    result: _T = promise.get(timeout=self._re_cpu_time)
                    self._logger.debug(
                        f"got async result in {self._re_cpu_time}s. Executed successfully? {promise.successful()}"
                    )
                except TimeoutError:
                    self._logger.debug("timeout error occurs in execution")
                    result = None
                except Exception:
                    self._logger.debug("unknown exception occurs in execution")
                    self._logger.error(format_exc())
                    result = None
        else:
            try:
                result = self._runner(*args, **kwargs)
            except Exception:
                self._logger.debug("unknown exception occurs in execution")
                self._logger.error(format_exc())
                result = None

        self._logger.debug("finished runner")
        return result

    # ===== basic end structures =====

    # ===== main fn =====
    def init(self, *args, **kwargs) -> Controller[_T]:
        """
        same as `__call__`, but probably looks nicer
        intended usage: `controller_instance.init().main()`
        :param args:
        :param kwargs:
        :return: self
        """
        return self(*args, **kwargs)

    def main(self, *args: _P.args, **kwargs: _P.kwargs) -> _T | None:
        """
        The main function to be called
        :param args:
        :param kwargs:
        :return: whatever the runner returns
        """
        self._logger.debug(
            "started main with \n" f"args: {args}\n" f"kwargs: {kwargs}\n"
        )
        with self as ctrl:
            return ctrl._run(*args, **kwargs)

    # ===== main fn end =====


class GraphController(Controller):
    """
    Graph controller for Graphery Executor
    """

    _recorder_cls: Type = _recorder_cls
    _tracer_cls: Type = _tracer_cls

    _graph_builder = nx.cytoscape_graph

    def __init__(
        self,
        *,
        code: str,
        graph_data: dict,
        exec_options: Mapping = None,
        graph: nx.Graph = None,
        logger: Logger = void_logger,
        options: Mapping = None,
    ) -> None:
        super().__init__(runner=self._graph_runner, logger=logger, options=options)

        # collect basic data
        self._code = code
        self._graph_data = graph_data
        self._graph = graph or self._graph_builder(graph_data)
        self._exec_options = exec_options or {}

        # collect recorder and tracer
        self._recorder = _recorder_cls(graph=self._graph, logger=logger)
        self._logger.debug("made new recorder")

        self._tracer = deepcopy(_tracer_cls)
        self._tracer.set_new_recorder(self._recorder)
        self._logger.debug("made new tracer and attached a recorder")
        self._tracer.set_additional_source(
            (_DEFAULT_MODULE_NAME, _DEFAULT_FILE_NAME),
            (_DEFAULT_FILE_NAME, self._code.splitlines()),
        )

    def _collect_globals(self) -> None:
        self._add_custom_module(nx, "nx", "networkx")

        # place trace
        self._update_globals("tracer", self._tracer)
        self._logger.debug("collected `tracer` class")

        # TODO make new module for sigh

        self._update_globals("graph", self._graph)
        self._logger.debug(f"updated graph in user globals with {self._graph}")

        super(GraphController, self)._collect_globals()

    # TODO add option setter such as rand seed

    def _graph_runner(self) -> list[MutableMapping]:
        """
        Graphery graph runner
        :return: a list of execution records but None for now
        """
        cmd = compile(self._code, _DEFAULT_FILE_NAME, "exec")

        with redirect_stdout(self._stdout), redirect_stderr(self._stderr):
            self._restrict_sandbox()
            exec(cmd, self._user_globals, self._user_globals)

        self._logger.debug(
            "executed successfully on \n"
            "```python\n"
            f"{self._code}\n"
            "```\n"
            "with globals \n"
            f"{self._user_globals}\n"
        )

        result = self._recorder.final_change_list
        self._logger.debug("final change list: \n" f"{result}\n")

        return result
