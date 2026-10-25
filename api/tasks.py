"""
Vercel serverless function: /api/tasks

Poll the state of background training jobs started via /api/train_async.

Query parameters:
  id     → single task record (GET /api/tasks?id=2026-10-25_ab12cd)
  status → optional filter when listing (pending|running|succeeded|failed)

Response:
  single task → {id, status, created_at, started_at, finished_at, result, error, meta}
  list        → {tasks: [...], count: int}
"""

from ml_db.client import MLDB
from ml_db.errors import TaskNotFoundError


def handle(req, res):
    """Vercel Python serverless handler."""
    try:
        args = getattr(req, 'args', {}) or {}
        task_id = args.get('id')
        status = args.get('status')

        db = MLDB()

        if task_id:
            try:
                res.json(db.get_task(task_id))
            except TaskNotFoundError as e:
                res.status = 404
                res.json({'error': str(e), 'code': e.code})
            return

        tasks = db.list_tasks(status=status)
        res.json({'tasks': tasks, 'count': len(tasks)})
    except Exception as e:
        res.status = 500
        res.json({'error': str(e)})
