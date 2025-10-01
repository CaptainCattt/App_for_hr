from settings import SESSIONS_COL, COOKIES
from datetime import datetime


def get_current_user():
    token = COOKIES.get("session_token")
    if not token:
        return None

    session = SESSIONS_COL.find_one({"token": token})
    if not session or session["expired_at"] < datetime.now():
        return None

    return {"username": session["username"], "role": session["role"]}
