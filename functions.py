# functions.py
import streamlit as st
from datetime import datetime, timedelta
from bson import ObjectId
import time
import uuid
import jwt
from settings import USERS_COL, LEAVES_COL, COOKIES, STATUS_COLORS, JWT_SECRET

JWT_ALGO = "HS256"
SESSION_COOKIE_KEY = "session_token"
SESSION_DURATION_HOURS = 8  # token lifetime


def create_jwt_for_user(user):
    """Tạo JWT chứa thông tin user + session_id duy nhất"""
    exp = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    session_id = str(uuid.uuid4())
    payload = {
        "sid": session_id,
        "sub": str(user.get("_id", "")),
        "username": user["username"],
        "role": user.get("role", "employee"),
        "exp": exp.timestamp()  # lưu timestamp
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    return token


def verify_jwt(token):
    """Decode JWT, trả về payload hoặc None nếu hết hạn/invalid"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user():
    """Lấy thông tin user từ cookie + JWT"""
    token = COOKIES.get(SESSION_COOKIE_KEY)
    if not token:
        return None
    payload = verify_jwt(token)
    if not payload:
        COOKIES[SESSION_COOKIE_KEY] = ""
        COOKIES.save()
        return None

    user = USERS_COL.find_one({"username": payload.get("username")})
    if not user:
        return None

    return {
        "_id": str(user["_id"]),
        "username": user["username"],
        "role": user.get("role", "employee"),
        "full_name": user.get("full_name", user["username"]),
        "position": user.get("position", ""),
        "department": user.get("department", ""),
        "remaining_days": user.get("remaining_days", 0)
    }


def do_login(username, password):
    """Đăng nhập user, tạo JWT và lưu vào cookie"""
    placeholder = st.empty()
    with placeholder:
        st.info("🔑 Đang đăng nhập...")
    time.sleep(0.4)

    user = USERS_COL.find_one({"username": username})
    if not user:
        # Tạo user mới nếu chưa có
        USERS_COL.insert_one({
            "username": username,
            "password": password,
            "role": "employee",
            "full_name": username,
            "position": "",
            "department": "",
            "remaining_days": 0,
            "created_at": datetime.utcnow()
        })
        user = USERS_COL.find_one({"username": username})
    else:
        if user.get("password") != password:
            placeholder.error("❌ Sai username hoặc password")
            time.sleep(1.2)
            placeholder.empty()
            return False

    # Tạo token JWT
    token = create_jwt_for_user(user)

    # Lưu cookie client hiện tại
    COOKIES[SESSION_COOKIE_KEY] = token
    COOKIES.save()

    # Update session_state
    st.session_state.update({
        "username": user["username"],
        "role": user.get("role", "employee"),
        "full_name": user.get("full_name", user["username"]),
        "position": user.get("position", ""),
        "department": user.get("department", ""),
        "remaining_days": user.get("remaining_days", 0),
        "rerun_needed": True
    })

    placeholder.success(
        f"✅ Đăng nhập thành công! Chào {st.session_state['full_name']}")
    time.sleep(1)
    placeholder.empty()
    return True


def logout():
    COOKIES[SESSION_COOKIE_KEY] = ""
    COOKIES.save()
    for k in ["username", "role", "full_name", "position", "department", "remaining_days"]:
        if k in st.session_state:
            del st.session_state[k]
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
