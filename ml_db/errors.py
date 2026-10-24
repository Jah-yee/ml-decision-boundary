"""
ml_db/errors.py — SDK exception hierarchy (v12 DoD #1)

All SDK-raised errors inherit from MLDBError so callers can catch a
single base class. Error codes follow the repo convention documented in
core/error_messages.py (E1xxx) — SDK-specific codes use the E2xxx range.
"""


class MLDBError(Exception):
    """Base class for every error raised by the ml_db SDK."""


class UnknownDatasetError(MLDBError):
    """Raised when an unknown dataset name is requested.

    Code: E2001_UNKNOWN_DATASET
    """

    code = "E2001_UNKNOWN_DATASET"

    def __init__(self, name: str, available=None):
        self.name = name
        self.available = list(available) if available else []
        msg = f"Unknown dataset '{name}'."
        if self.available:
            msg += f" Available: {', '.join(self.available)}."
        super().__init__(msg)


class UnknownModelError(MLDBError):
    """Raised when an unknown model type is requested.

    Code: E2002_UNKNOWN_MODEL
    """

    code = "E2002_UNKNOWN_MODEL"

    def __init__(self, name: str, available=None):
        self.name = name
        self.available = list(available) if available else []
        msg = f"Unknown model '{name}'."
        if self.available:
            msg += f" Available: {', '.join(self.available)}."
        super().__init__(msg)


class ModelNotFoundError(MLDBError):
    """Raised when a model id is not present in the registry.

    Code: E2003_MODEL_NOT_FOUND
    """

    code = "E2003_MODEL_NOT_FOUND"

    def __init__(self, model_id: str):
        self.model_id = model_id
        super().__init__(
            f"Model '{model_id}' not found in registry. "
            "Use MLDB.list_models() to see available models."
        )


class InvalidInputError(MLDBError):
    """Raised when caller-supplied input fails validation.

    Code: E2004_INVALID_INPUT
    """

    code = "E2004_INVALID_INPUT"
