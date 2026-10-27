"""
Vercel serverless function: /api/registry

Query the model registry: list models, filter by a batch of tags, and
inspect model versions (v1/v2) and families.

Query parameters:
  id       → single model metadata (GET /api/registry?id=2026-10-25_ab12cd)
  tags     → comma-separated tag names to match (e.g. ?tags=best,prod)
  match    → tag match mode: "any" (default) or "all"
  families → when "1"/"true", return the model-family grouping
  versions → when "1"/"true", return every version of the requested model

Response:
  single model → {id, model_type, version, family, tags, accuracy, ...}
  list         → {models: [...], count: int}
  families     → {families: {family: [...]}, count: int}
"""

from ml_db.client import MLDB


def handle(req, res):
    """Vercel Python serverless handler."""
    try:
        args = getattr(req, 'args', {}) or {}
        model_id = args.get('id')
        tags_arg = args.get('tags')
        match = args.get('match') or 'any'
        want_families = str(args.get('families', '')).lower() in ('1', 'true', 'yes')
        want_versions = str(args.get('versions', '')).lower() in ('1', 'true', 'yes')

        db = MLDB()

        if model_id:
            try:
                if want_versions:
                    versions = db.get_model_versions(model_id)
                    res.json({
                        'id': model_id,
                        'family': versions[0].get('family') if versions else '',
                        'count': len(versions),
                        'versions': versions,
                    })
                else:
                    res.json(db.get_model(model_id))
            except Exception as e:
                res.status = 404
                res.json({'error': str(e)})
            return

        if want_families:
            families = db.list_model_families()
            res.json({
                'families': families,
                'count': len(families),
                'version_total': sum(len(v) for v in families.values()),
            })
            return

        # `tags` explicitly provided (even empty) means the caller asked to
        # filter by tags — an empty value is a client error, not "no filter".
        if tags_arg is not None:
            tags = [t.strip() for t in tags_arg.split(',') if t.strip()]
            if not tags:
                res.status = 400
                res.json({'error': "Query parameter 'tags' must not be empty."})
                return
            try:
                models = db.list_models_by_tags(tags, mode=match)
            except ValueError as e:
                res.status = 400
                res.json({'error': str(e)})
                return
            res.json({
                'models': models,
                'count': len(models),
                'tags': tags,
                'match': match,
            })
            return

        models = db.list_models()
        res.json({'models': models, 'count': len(models)})
    except Exception as e:
        res.status = 500
        res.json({'error': str(e)})
