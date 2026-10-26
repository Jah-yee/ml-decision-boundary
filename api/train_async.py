"""
Vercel serverless function: /api/train_async

Starts a background training job and returns a task id immediately.
The client polls /api/tasks?id=<task_id> for the outcome.

Request body:
  {model, dataset, params, n_samples, noise, test_size, register, tags}

Response:
  {id, status, created_at, ...}   → poll with /api/tasks
"""

from ml_db.client import MLDB
from ml_db.errors import (
    InvalidInputError,
    UnknownDatasetError,
    UnknownModelError,
)


def handle(req, res):
    """Vercel Python serverless handler."""
    try:
        body = req.get_json() or {}
        db = MLDB()

        task = db.train_async(
            model=body.get('model', 'SVM'),
            dataset=body.get('dataset', 'circles'),
            params=body.get('params') or {},
            n_samples=int(body.get('n_samples', 500)),
            noise=float(body.get('noise', 0.3)),
            test_size=float(body.get('test_size', 0.2)),
            register=bool(body.get('register', True)),
            tags=body.get('tags') or [],
        )

        res.status = 202
        res.json(task)
    except UnknownDatasetError as e:
        res.status = 400
        res.json({'error': str(e), 'code': e.code})
    except UnknownModelError as e:
        res.status = 400
        res.json({'error': str(e), 'code': e.code})
    except InvalidInputError as e:
        res.status = 400
        res.json({'error': str(e), 'code': e.code})
    except Exception as e:
        res.status = 500
        res.json({'error': str(e)})
