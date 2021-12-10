from __future__ import annotations

import abc
import contextlib
import json
import random
import signal
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
    NoReturn,
)
from contextlib import redirect_stdout, redirect_stderr

from .recorder import Recorder as _recorder_cls
from ..seeker import tracer as _tracer_cls

import networkx as nx

from ..settings import (
    DefaultVars,
    INIT_ERROR_CODE,
    CPU_OUT_EXIT_CODE,
    MEM_OUT_EXIT_CODE,
    SERVER_VERSION,
    POST_ERROR_CODE,
    PREP_ERROR_CODE,
    RUNNER_ERROR_CODE,
    CTRL_ERROR_CODE,
)

try:
    import resource
except ImportError:
    resource = None

from platform import platform

_PLATFORM_STR = platform()

__all__ = [
    "Controller",
    "GraphController",
    "RunnerError",
    "LayerContext",
    "ControllerResultAnnouncer",
]

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


class LayerContext(contextlib.AbstractContextManager):
    def __init__(self, controller: Controller):
        self._ctrl = controller

    @abc.abstractmethod
    def enter(self) -> None:
        ...

    @abc.abstractmethod
    def exit(self) -> None:
        ...

    def __enter__(self):
        self.enter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()


class _FDRedirectLayer(LayerContext):
    def enter(self):
        self._ctrl.stdout_redirector.__enter__()
        # self._ctrl.stderr_redirector.__enter__()
        self._ctrl.logger.debug("redirected stdout and stderr")

    def exit(self) -> None:
        self._ctrl.stdout_redirector.__exit__(None, None, None)
        # self._ctrl.stderr_redirector.__exit__(None, None, None)
        self._ctrl.logger.debug("unredirected stdout and stderr")


class _ModuleRestrict(LayerContext):
    def enter(self) -> None:
        if not self._ctrl.is_local:
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
            del _sys.modules["sys"]

            self._ctrl.logger.debug("deleted dangerous modules")

    def exit(self) -> None:
        pass


class ControllerResultAnnouncer:
    def __init__(self, output=_sys.stdout):
        self._out = output

    def write(self, s: str) -> None:
        self._out.write(s)

    def show_error(
        self, exception: Exception, trace: str = None, error_code: int = 1
    ) -> NoReturn:
        from traceback import format_exc

        e = SystemExit(
            f"An error occurs with exit code {error_code}. Error: {exception}\n"
            f"trace: \n"
            f"{trace if trace else format_exc()}"
        )
        self.write(str(e))

        raise e

    def show_result(self, result: str) -> None:
        self.write(result)


class _ResourceRestrict(LayerContext):
    def _cpu_time_out_helper(self, sig_num, __):
        self._ctrl.announcer.show_error(
            ValueError(f"Allocated CPU time exhausted. Signal num: {sig_num}"),
            error_code=CPU_OUT_EXIT_CODE,
        )

    def _mem_consumed_helper(self, sig_num, __):
        self._ctrl.announcer.show_error(
            ValueError(f"Allocated MEM size exhausted. Signal num: {sig_num}"),
            error_code=MEM_OUT_EXIT_CODE,
        )

    def enter(self) -> None:
        if _PLATFORM_STR == "Linux" and resource is not None:
            signal.signal(signal.SIGXCPU, self._cpu_time_out_helper)
            resource.setrlimit(
                resource.RLIMIT_CPU, (self._ctrl.re_cpu_time, resource.RLIM_INFINITY)
            )
            self._ctrl.logger.debug(
                f"set cpu limit to {self._ctrl.re_cpu_time} seconds"
            )

            signal.signal(signal.SIGSEGV, self._mem_consumed_helper)
            resource.setrlimit(
                resource.RLIMIT_AS, (self._ctrl.re_mem_size, resource.RLIM_INFINITY)
            )
            self._ctrl.logger.debug(
                f"set memory limit to {self._ctrl.re_mem_size} bytes"
            )
            # https://man7.org/linux/man-pages/man2/getrlimit.2.html

    def exit(self) -> None:
        if _PLATFORM_STR == "Linux" and resource is not None:
            resource.setrlimit(
                resource.RLIMIT_CPU, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
            )
            self._ctrl.logger.debug(f"reset cpu limit")


class _RandomContext(LayerContext):
    def enter(self) -> None:
        random.seed(self._ctrl.rand_seed)
        self._ctrl.logger.debug(f"set random seed to {self._ctrl.rand_seed}")

    def exit(self) -> None:
        random.seed()
        self._ctrl.logger.debug("reset random seed")


class RunnerError(Exception):
    def __init__(self, msg):
        super(RunnerError, self).__init__(msg)


class Controller(Generic[_T]):
    """
    Controller class that controls the execution of some `runner` function
    """

    _DEFAULT_CONTEXT_LAYERS = [
        _RandomContext,
        _FDRedirectLayer,
        _ModuleRestrict,
        _ResourceRestrict,
    ]

    def __init__(
        self,
        *,
        runner: Callable[_P, _T],
        context_layers: Sequence[Type[LayerContext]] = (),
        default_settings: DefaultVars = DefaultVars(),
        options: Mapping = None,
        **kwargs,
    ) -> None:
        """
        initializer of a controller
        each controller is designed to be single use
        :param runner:
        :param default_settings:
        :param options:
        :param logger:
        :param custom_ns:
        :param controller:
        :param stdout:
        :param stderr:
        :param kwargs:
        """
        options = {**default_settings.vars, **(options or {}), **kwargs}
        self._default_settings = default_settings

        # register logger
        self._logger: Logger = options.get(
            "logger", options.get(default_settings.LOGGER)
        )

        # register control layers
        self._init_layers: List[LAYER_TYPE] = [*self._make_init_layers()]
        self._logger.debug(f"registered init layers: {self._init_layers}")

        self._context_layers: List[LayerContext] = [
            *(layer(self) for layer in context_layers),
            *(layer(self) for layer in self._DEFAULT_CONTEXT_LAYERS),
        ]
        self._logger.debug(f"registered context layers: {self._context_layers}")

        # register runner
        self._runner: Callable[_P, _T] = runner
        self._logger.debug(f"registered runner")

        # context on flag
        self._in_context: bool = False

        # local flag
        self._is_local: bool = options.get(default_settings.IS_LOCAL)

        self._custom_ns: Dict[str, types.ModuleType] = options.get("custom_ns", {})

        # sandbox
        self._user_globals: Dict[str, Any] = {}

        self._logger.debug(f"controller uses settings {default_settings}")

        self._re_mem_size = options.get(default_settings.EXEC_MEM_OUT,) * int(
            10e6
        )  # convert mb to bytes
        self._logger.debug(f"restricted memory size to {self._re_mem_size} bytes")

        self._re_cpu_time = options.get(default_settings.EXEC_TIME_OUT)
        self._logger.debug(f"restricted CPU time to {self._re_cpu_time} seconds")

        self._rand_seed = options.get(default_settings.RAND_SEED)
        self._logger.debug(f"rand seed will be {self._rand_seed} in execution")

        self._float_precision = options.get(default_settings.FLOAT_PRECISION)
        self._logger.debug(
            f"float precision will be {self._float_precision} in execution"
        )

        # std
        self._stdout = options.get("stdout", StringIO())
        self._stderr = options.get("stderr", StringIO())
        self._stdout_redirector = redirect_stdout(self._stdout)
        self._stderr_redirector = redirect_stderr(self._stderr)

        # formatter
        self._announcer = options.get("formatter", ControllerResultAnnouncer())

        # args
        self._BUILTIN_IMPORT: Final = _builtins_getter("__import__")

        self._ALLOWED_STDLIB_MODULE_IMPORTS: Final = [
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
        ]
        self._DEL_MODULES: Final = ["os", "sys", "posix", "gc", "_sys", "_os"]
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

            if importing_name in self._custom_ns and isinstance(
                result := self._custom_ns[importing_name], types.ModuleType
            ):
                return result
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
                f"If you're using a local instance, please try to turn on is_local_flag"
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
                "If you're using a local instance, please try to turn on is_local_flag"
            )

        return _open

    def _update_globals(self, name: str, val: Any) -> None:
        """
        update globals namespace with name and val
        :param name: the name
        :param val: the value
        :return: None
        """
        self._user_globals[name] = val
        self._logger.debug(f"updated global attr '{name}' with {val} ")

    # ===== global helpers end =====

    # ===== init section=====
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
        self._update_globals("__builtins__", _user_builtins)

    def _collect_globals(self) -> None:
        """
        collect other specified namespace
        :return: None
        """
        self._update_globals("__name__", _DEFAULT_MODULE_NAME)
        self._user_globals.update(copy(self._custom_ns))
        self._logger.debug(f"updated global with custom_ns {self._custom_ns}")

    # ===== init end end =====

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

    # ===== layer makers  =====

    @classmethod
    def _make_init_layers(cls) -> Sequence[LAYER_TYPE]:
        """
        init layer maker, should be overwritten by subclasses if necessary
        :return: sequence of layer functions
        """
        return (cls._collect_builtins, cls._collect_globals)

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
        for layer in self._context_layers:
            layer.enter()
        self._logger.debug("finished executing prep process")

    def _post_process(self) -> None:
        """
        run post layers
        :return: None
        """
        for layer in self._context_layers:
            layer.exit()
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
        try:
            self._init_process()
        except Exception as e:
            self._announcer.show_error(e, error_code=INIT_ERROR_CODE)

        return self

    def __enter__(self) -> Controller[_T]:
        """
        context helper
        :return: None
        """
        self._enter_context()
        try:
            self._prep_process()
        except Exception as e:
            self._announcer.show_error(e, error_code=PREP_ERROR_CODE)
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
        try:
            self._post_process()
        except Exception as e:
            self._announcer.show_error(e, error_code=POST_ERROR_CODE)

    def _run(self, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        """
        run the internal runner
        :param args: runner args
        :param kwargs: runner kwargs
        :return: whatever the runner returns
        """
        self._logger.debug(
            "start runner with\n" f"args: {args}\n" f"and kwargs: {kwargs}"
        )
        try:
            result = self._runner(*args, **kwargs)
        except Exception as e:
            # but this is going to mess up the tests
            from traceback import format_exc

            self._logger.debug("exception occurs in runner execution")
            self._announcer.show_error(
                RunnerError(e), trace=format_exc(), error_code=RUNNER_ERROR_CODE
            )
            return

        self._logger.debug("finished runner successfully")
        # surprised https://youtrack.jetbrains.com/issue/PY-24273
        return result

    def format_result(self, result):
        return result

    # ===== basic structures end =====

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

    def main(
        self,
        *args: _P.args,
        formats: bool = False,
        announces: bool = False,
        **kwargs: _P.kwargs,
    ) -> _T:
        """
        The main function to be called
        :param announces:
        :param formats:
        :param args:
        :param kwargs:
        :return: whatever the runner returns
        """
        self._logger.debug("started main with \n" f"args: {args}\n" f"kwargs: {kwargs}")
        with self as ctrl:
            result = ctrl._run(*args, **kwargs)

        if formats:
            self._logger.debug("formatting result from main")
            try:
                result = self.format_result(result)
            except Exception as e:
                self._announcer.show_error(e, error_code=CTRL_ERROR_CODE)

        if announces:
            self._logger.debug("announcing result from main")
            self._announcer.show_result(result)

        return result

    # ===== main fn end =====
    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    @property
    def stdout_redirector(self):
        return self._stdout_redirector

    @property
    def stderr_redirector(self):
        return self._stderr_redirector

    @property
    def logger(self):
        return self._logger

    @property
    def re_mem_size(self):
        return self._re_mem_size

    @property
    def re_cpu_time(self):
        return self._re_cpu_time

    @property
    def is_local(self):
        return self._is_local

    @property
    def rand_seed(self):
        return self._rand_seed

    @property
    def announcer(self):
        return self._announcer


class GraphController(Controller[List[MutableMapping]]):
    """
    Graph controller for Graphery Executor
    """

    _graph_builder = nx.cytoscape_graph

    def __init__(
        self,
        *,
        code: str,
        graph_data: dict | str,
        context_layers: Sequence[Type[LayerContext]] = (),
        default_settings: DefaultVars = DefaultVars(),
        options: Mapping = None,
        **kwargs,
    ) -> None:
        super().__init__(
            runner=self._graph_runner,
            context_layers=context_layers,
            default_settings=default_settings,
            options=options,
            **kwargs,
        )

        # collect basic data
        self._code = code
        self._graph_data = graph_data
        self._target_version = default_settings.v.TARGET_VERSION
        self._graph: nx.Graph | None = None  # placeholder

        # collect recorder and tracer
        self._recorder: _recorder_cls | None = None  # placeholder
        self._tracer: _tracer_cls | None = None  # placeholder
        self._logger.debug(
            "created controller with code \n"
            "```python\n"
            f"{self._code}\n"
            "```\n"
            "and graph data \n"
            f"{self._graph_data}"
        )

    def _build_graph(self) -> None:
        if isinstance(self._graph_data, str):
            self._logger.debug("treat graph data as json string")
            self._graph_data = json.loads(self._graph_data)
        elif isinstance(self._graph_data, Dict):
            self._logger.debug("treat graph data as cyjs object")
        elif isinstance(self._graph_data, nx.Graph):
            self._logger.debug("treat graph data as networkx graph")
        else:
            raise ValueError(
                "graph data has to be either str type, dict type, or a graph instance"
            )

        self._logger.debug(f"loaded graph data {self._graph_data}")
        self._graph = (
            self._graph_data
            if isinstance(self._graph_data, nx.Graph)
            else type(self)._graph_builder(self._graph_data)
        )
        self._logger.debug(f"made graph {self._graph}")

    def _build_recorder(self) -> None:
        if self._graph is None or not isinstance(self._graph, nx.Graph):
            from warnings import warn

            warn("initialization of recorder requires proper graph")
        self._recorder = _recorder_cls(graph=self._graph, logger=self._logger)
        self._logger.debug(f"made new recorder {self._recorder}")

    def _build_tracer(self) -> None:
        if self._recorder is None or not isinstance(self._recorder, _recorder_cls):
            raise ValueError("initialization of tracer requires proper recorder")
        self._tracer = deepcopy(_tracer_cls)
        self._logger.debug("made new tracer cls")
        self._tracer.set_logger(self._logger)
        self._tracer.set_new_recorder(self._recorder)
        self._tracer.set_additional_source(
            (_DEFAULT_MODULE_NAME, _DEFAULT_FILE_NAME),
            (_DEFAULT_FILE_NAME, self._code.splitlines()),
        )

    def _check_version(self) -> None:
        if self._target_version != SERVER_VERSION:
            raise ValueError(
                f"Request Version {self._target_version} does not match Server Version {SERVER_VERSION}"
            )

    @classmethod
    def _make_init_layers(cls) -> Sequence[LAYER_TYPE]:
        base = super()._make_init_layers()
        return (
            cls._check_version,
            cls._build_graph,
            cls._build_recorder,
            cls._build_tracer,
            *base,
        )

    def _collect_globals(self) -> None:
        self._add_custom_module(nx, "nx", "networkx")

        # place trace
        self._update_globals("tracer", self._tracer)
        self._logger.debug("collected `tracer` class")

        self._update_globals("graph", self._graph)
        self._logger.debug(f"updated graph in user globals with {self._graph}")

        super(GraphController, self)._collect_globals()

    def _graph_runner(self) -> List[MutableMapping]:
        """
        Graphery graph runner
        :return: a list of execution records but None for now
        """
        cmd = compile(self._code, _DEFAULT_FILE_NAME, "exec")
        exec(cmd, self._user_globals, self._user_globals)

        self._logger.debug(
            "executed successfully on \n"
            "```python\n"
            f"{self._code}\n"
            "```\n"
            "with globals \n"
            f"{self._user_globals}"
        )

        result = self._recorder.final_change_list
        self._logger.debug("final change list: \n" f"{result}")

        return result

    def format_result(self, result):
        return json.dumps(result)
