"""Our own error types, so a failure says what is wrong in plain words."""


class BeyondSearchError(Exception):
    """Base class for every expected failure."""


class ConfigError(BeyondSearchError):
    """The YAML configuration is missing something or points to something that does not exist."""


class DataError(BeyondSearchError):
    """The input data does not look the way the configuration says it should."""
