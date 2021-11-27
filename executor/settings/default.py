from variables import DefaultVars


class DefaultENVVars(DefaultVars):
    pass


DefaultENVVars.read_from_env(use_default=True)
