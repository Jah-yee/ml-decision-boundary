"""Vercel serverless function: /api/health.

Health check endpoint for deployment validation. Always returns
{status: 'ok'} regardless of request body or method, confirming the
service is alive and responding.

Args:
    req: Vercel serverless request object (unused)
    res: Vercel serverless response object with .json() method

Returns:
    None (response sent via res.json())

Example:
    >>> # Any request returns OK
    >>> curl https://your-app.vercel.app/api/health
    {"status": "ok"}
"""

def handle(req, res):
    res.json({'status': 'ok'})
