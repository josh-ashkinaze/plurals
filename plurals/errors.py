"""
Custom exceptions
"""


class PluralsError(Exception):
    """Base class for all Plurals exceptions."""


class PersonaError(PluralsError, ValueError):
    """
    Raised when a persona cannot be generated from ANES data.

    Typical causes:
    - ``ideology`` or ``query_str`` matched no rows in the dataset.
    """


class ConfigurationError(PluralsError, ValueError):
    """
    Raised when an Agent or Structure is initialised with invalid or
    conflicting arguments.

    Typical causes:
    - Passing more than one of ``ideology``, ``query_str``,
      ``system_instructions``, or ``persona`` to ``Agent``.
    - Providing an ideology value that is not in the allowed list.
    - Using a custom ``persona_template`` that lacks the required
      ``${persona}`` placeholder.
    """


class LLMError(PluralsError, RuntimeError):
    """
    Raised when a call to the underlying LLM API fails.

    The original exception is always chained (``raise LLMError(...) from e``)
    so the full traceback is preserved.
    """
