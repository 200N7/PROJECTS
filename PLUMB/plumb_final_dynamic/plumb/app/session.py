from __future__ import annotations
import secrets
from fastapi import Request, Response

COOKIE='plumb_session'

def get_session_id(request: Request, response: Response | None = None):
    sid=request.cookies.get(COOKIE)
    if sid: return sid
    sid=secrets.token_urlsafe(24)
    if response is not None:
        response.set_cookie(COOKIE, sid, httponly=True, samesite='lax', secure=request.url.scheme=='https', max_age=60*60*24*30)
    return sid
