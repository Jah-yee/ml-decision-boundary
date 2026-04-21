"""Vercel serverless function: /api/health"""

def handle(req, res):
    res.json({'status': 'ok'})
