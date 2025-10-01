# functions.py
import streamlit as st
from datetime import datetime, timedelta
from bson import ObjectId
import time
import jwt
import uuid

from settings import USERS_COL, LEAVES_COL, SESSIONS_COL, COOKIES, STATUS_COLORS, JWT_SECRET

# ---------------------------
# Authentication & sessions
# ---------------------------

JWT_ALGO = "HS256"
SESSION_COOKIE_KEY = "session_token"
SESSION_DURATION_HOURS = 8  # token/session lifetime


def create_jwt_for_user(user):
    exp = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    payload = {
        "sub": str(user.get("_id", "")),
        "username": user["username"],
        "role": user.get("role", "employee"),
        "exp": exp
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    return token, exp


def save_session(token, username, role, expired_at, meta=None):
    doc = {
        "token": token,
        "username": username,
        "role": role,
        "expired_at": expired_at,
        "meta": meta or {},
        "created_at": datetime.utcnow()
    }
    SESSIONS_COL.insert_one(doc)
    return doc


def verify_jwt(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user():
    token = COOKIES.get(SESSION_COOKIE_KEY)
    if not token:
        return None

    # Kiểm tra session trong DB
    session_doc = SESSIONS_COL.find_one({"token": token})
    if not session_doc:
        COOKIES[SESSION_COOKIE_KEY] = ""
        COOKIES.save()
        return None

    # Verify JWT
    payload = verify_jwt(token)
    if not payload:
        SESSIONS_COL.delete_one({"token": token})
        COOKIES[SESSION_COOKIE_KEY] = ""
        COOKIES.save()
        return None

    # Load user từ DB
    user = USERS_COL.find_one({"username": payload.get("username")})
    if not user:
        return None

    return {
        "username": user["username"],
        "role": user.get("role", "employee"),
        "full_name": user.get("full_name", user["username"]),
        "position": user.get("position", ""),
        "department": user.get("department", ""),
        "remaining_days": user.get("remaining_days", 0)
    }


def do_login(username, password):
    """
    Authenticate user, create JWT and session record, set cookie.
    """
    placeholder = st.empty()
    with placeholder:
        st.info("🔑 Đang đăng nhập...")
    time.sleep(0.4)

    user = USERS_COL.find_one({"username": username, "password": password})
    if not user:
        placeholder.error("❌ Sai username hoặc password")
        time.sleep(1.2)
        placeholder.empty()
        return False

    token, exp = create_jwt_for_user(user)
    # Save session doc
    save_session(token, user["username"], user.get("role", "employee"), exp)

    # Set cookie
    COOKIES[SESSION_COOKIE_KEY] = token
    COOKIES.save()

    # populate session_state
    st.session_state["username"] = user["username"]
    st.session_state["role"] = user.get("role", "employee")
    st.session_state["full_name"] = user.get("full_name", user["username"])
    st.session_state["position"] = user.get("position", "")
    st.session_state["department"] = user.get("department", "")
    st.session_state["remaining_days"] = user.get("remaining_days", 0)

    placeholder.success(
        f"✅ Đăng nhập thành công! Chào {st.session_state['full_name']}")
    time.sleep(1)
    placeholder.empty()
    # ask app to rerun to refresh UI
    st.session_state["rerun_needed"] = True
    return True


def logout():
    placeholder = st.empty()
    with placeholder:
        st.info("🚪 Đang đăng xuất...")
    time.sleep(0.4)

    # delete session from DB if exists
    token = COOKIES.get(SESSION_COOKIE_KEY)
    if token:
        SESSIONS_COL.delete_one({"token": token})

    # clear cookie and st.session_state
    COOKIES[SESSION_COOKIE_KEY] = ""
    COOKIES.save()

    # clear only keys we used (do not clear all arbitrary state if other data needed)
    keys_to_clear = ["username", "role", "full_name",
                     "position", "department", "remaining_days"]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

    placeholder.success("✅ Bạn đã đăng xuất thành công!")
    time.sleep(0.8)
    placeholder.empty()
    st.session_state["rerun_needed"] = True

# ---------------------------
# Leave-related functions
# ---------------------------


def request_leave(username, start_date, end_date, duration, reason, leave_type, leave_case):
    if not isinstance(start_date, str):
        start_date = start_date.strftime("%Y-%m-%d")
    if not isinstance(end_date, str):
        end_date = end_date.strftime("%Y-%m-%d")
    LEAVES_COL.insert_one({
        "username": username,
        "start_date": start_date,
        "end_date": end_date,
        "duration": duration,
        "reason": reason,
        "leave_type": leave_type,
        "leave_case": leave_case,
        "status": "pending",
        "requested_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "approved_by": None,
        "approved_at": None
    })


def view_leaves(username=None):
    if username:
        return list(LEAVES_COL.find({"username": username}))
    return list(LEAVES_COL.find())


def update_leave_status(leave_id, new_status):
    LEAVES_COL.update_one({"_id": ObjectId(leave_id)}, {
                          "$set": {"status": new_status}})


def status_badge(status: str):
    return STATUS_COLORS.get(status, status)


def send_leave_request(username, start_date, end_date, duration, reason, leave_type, leave_case):
    # Called from UI; block double clicks by setting state in UI before calling this function.
    # Normalize dates
    start_str = start_date.strftime(
        "%Y-%m-%d") if not isinstance(start_date, str) else start_date
    end_str = end_date.strftime(
        "%Y-%m-%d") if not isinstance(end_date, str) else end_date

    LEAVES_COL.insert_one({
        "username": username,
        "start_date": start_str,
        "end_date": end_str,
        "duration": duration,
        "reason": reason,
        "leave_type": leave_type,
        "leave_case": leave_case,
        "status": "pending",
        "requested_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "approved_by": None,
        "approved_at": None
    })
    st.success(
        f"📤 Yêu cầu '{leave_case}' từ {start_str} đến {end_str} ({duration} ngày) đã gửi!")


def approve_leave(l_id, user_name):
    placeholder = st.empty()
    with placeholder:
        st.info("✅ Đang duyệt...")
    time.sleep(0.4)
    leave = LEAVES_COL.find_one({"_id": ObjectId(l_id)})
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    LEAVES_COL.update_one({"_id": ObjectId(l_id)}, {"$set": {
        "status": "approved",
        "approved_by": st.session_state.get("full_name", "Admin"),
        "approved_at": now_str
    }})
    if leave.get("leave_type") == "Nghỉ phép năm":
        duration = float(leave.get("duration", 1))
        USERS_COL.update_one({"username": user_name}, {
                             "$inc": {"remaining_days": -duration}})
    placeholder.success(
        f"✅ Yêu cầu của {user_name} đã được duyệt lúc {now_str}!")
    time.sleep(1)
    placeholder.empty()
    st.session_state["rerun_needed"] = True


def reject_leave(l_id, user_name):
    placeholder = st.empty()
    with placeholder:
        st.info("❌ Đang từ chối...")
    time.sleep(0.4)
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    LEAVES_COL.update_one({"_id": ObjectId(l_id)}, {"$set": {
        "status": "rejected",
        "approved_by": st.session_state.get("full_name", "Admin"),
        "approved_at": now_str
    }})
    placeholder.error(
        f"❌ Yêu cầu của {user_name} đã bị từ chối lúc {now_str}!")
    time.sleep(1)
    placeholder.empty()
    st.session_state["rerun_needed"] = True
