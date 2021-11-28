from . import DefaultVars

__all__ = ["DefaultENVVars"]


class DefaultENVVars(DefaultVars):
    pass


DefaultENVVars.read_from_env(use_default=True, all_arg=True)
