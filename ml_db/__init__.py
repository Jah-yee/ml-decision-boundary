"""
ml_db — Python SDK for ml-decision-boundary (v12 DoD #1)

Top-level API:

    from ml_db import MLDB

    db = MLDB()
    result = db.train(model="SVM", dataset="circles")
    preds = db.predict(result.model_id, X=[[0.0, 0.0], [1.0, 1.0]])

The SDK is a thin, stable wrapper around the existing `core/` layer —
it does not fork any training logic, so CLI / API / SDK stay consistent.
"""

from ml_db.client import MLDB, TrainResult
from ml_db.errors import (
    InvalidInputError,
    MLDBError,
    ModelNotFoundError,
    UnknownDatasetError,
    UnknownModelError,
)

__version__ = "0.1.0"

__all__ = [
    "MLDB",
    "TrainResult",
    "MLDBError",
    "UnknownDatasetError",
    "UnknownModelError",
    "ModelNotFoundError",
    "InvalidInputError",
    "__version__",
]
