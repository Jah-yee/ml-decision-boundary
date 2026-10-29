"""
Vercel serverless function: /api/provenance

Expose experiment provenance (v13 DoD #1) and reproducibility replay
recipes (v13 DoD #2) over HTTP.

Query parameters:
  id      → model id whose provenance should be returned
            (GET /api/provenance?id=2026-10-25_ab12cd)
  compare → second model id; when present, a provenance diff is returned
            (GET /api/provenance?id=<a>&compare=<b>)
  replay  → when "1"/"true"/"yes", include the replay recipe
            (SDK snippet + CLI command + dependency digest)
  coverage → when "1"/"true"/"yes" and no 'id' is given, return the
            registry-wide provenance coverage audit (v13 DoD #3)
  integrity → when "1"/"true"/"yes" and no 'id' is given, return the
            registry-wide replay recipe integrity audit (v13 DoD #4);
            with an 'id', return that model's recipe drift verdict
  verify  → when "1"/"true"/"yes" and an 'id' is given, actually execute
            the model's replay and report whether it still reproduces
            (v13 DoD #4)

Response:
  single model → the provenance record
  compare      → {left, right, diff}
  replay       → {provenance, replay}
  integrity    → the registry-wide integrity report
  verify       → {verified, status, accuracy, drift, ...}

Errors:
  400 → 'id' is missing (nothing to look up)
  404 → the requested model id is not registered
  500 → unexpected failure
"""

from ml_db.client import MLDB
from ml_db.errors import ModelNotFoundError


def _is_truthy(value) -> bool:
    return str(value or '').lower() in ('1', 'true', 'yes')


def handle(req, res):
    """Vercel Python serverless handler."""
    try:
        args = getattr(req, 'args', {}) or {}
        model_id = args.get('id')
        compare_id = args.get('compare')
        want_replay = _is_truthy(args.get('replay'))
        want_coverage = _is_truthy(args.get('coverage'))
        want_integrity = _is_truthy(args.get('integrity'))
        want_verify = _is_truthy(args.get('verify'))

        db = MLDB()

        # v13 DoD #3: registry-wide coverage audit — no model id required.
        if want_coverage and not model_id:
            res.json(db.coverage())
            return

        # v13 DoD #4: registry-wide replay integrity audit — no model id required.
        if want_integrity and not model_id and not want_verify:
            res.json(db.replay_integrity())
            return

        if not model_id:
            res.status = 400
            res.json({'error': "Query parameter 'id' is required."})
            return

        # v13 DoD #4: execute the replay and report whether it reproduces.
        if want_verify:
            try:
                res.json(db.verify_replay(model_id))
            except ModelNotFoundError as e:
                res.status = 404
                res.json({'error': str(e), 'code': getattr(e, 'code', 'MODEL_NOT_FOUND')})
            return

        # v13 DoD #4: per-model recipe drift verdict.
        if want_integrity:
            try:
                res.json(db.recipe_drift(model_id))
            except ModelNotFoundError as e:
                res.status = 404
                res.json({'error': str(e), 'code': getattr(e, 'code', 'MODEL_NOT_FOUND')})
            return

        try:
            provenance = db.get_provenance(model_id)
        except ModelNotFoundError as e:
            res.status = 404
            res.json({'error': str(e), 'code': getattr(e, 'code', 'MODEL_NOT_FOUND')})
            return

        payload = dict(provenance or {})

        if compare_id:
            try:
                other = db.get_provenance(compare_id)
            except ModelNotFoundError as e:
                res.status = 404
                res.json({'error': str(e), 'code': getattr(e, 'code', 'MODEL_NOT_FOUND')})
                return
            payload = {
                'left': provenance,
                'right': other,
                'diff': db.compare_provenance(model_id, compare_id),
            }

        if want_replay:
            payload = {
                'provenance': payload,
                'replay': db.replay_plan(model_id),
            }

        res.json(payload)
    except Exception as e:
        res.status = 500
        res.json({'error': str(e)})
