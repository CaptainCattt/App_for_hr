# functions.py
import streamlit as st
from datetime import datetime, timedelta
from bson import ObjectId
import time
import uuid
import jwt
from streamlit_cookies_manager import EncryptedCookieManager
from settings import USERS_COL, LEAVES_COL, STATUS_COLORS, JWT_SECRET

# ===============================
# CẤU HÌNH
# ===============================
JWT_ALGO = "HS256"
SESSION_COOKIE_KEY = "session_token"
SESSION_DURATION_HOURS = 8  # thời gian tồn tại token (giờ)

# === Cookie manager (mỗi trình duyệt riêng biệt) ===
cookies = EncryptedCookieManager(prefix="auth_", password="super_secret_key")
if not cookies.ready():
    st.stop()

# ===============================
# JWT FUNCTIONS
# ===============================


def create_jwt(user_id, session_id):
    """Tạo JWT cho user dựa trên session_id"""
    exp = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    payload = {
        "user_id": str(user_id),
        "session_id": session_id,
        "exp": exp
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    return token, exp


def verify_jwt(token):
    """Decode JWT, trả về payload hoặc None nếu hết hạn/invalid"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ===============================
# USER SESSION FUNCTIONS
# ===============================

def get_current_user():
    token = cookies.get(SESSION_COOKIE_KEY)
    if not token:
        return None

    payload = verify_jwt(token)
    if not payload:
        cookies[SESSION_COOKIE_KEY] = ""
        cookies.save()
        return None

    user_id = payload.get("user_id")
    session_id = payload.get("session_id")
    if not user_id or not session_id:
        cookies[SESSION_COOKIE_KEY] = ""
        cookies.save()
        return None

    user = USERS_COL.find_one({"_id": ObjectId(user_id)})
    if not user:
        cookies[SESSION_COOKIE_KEY] = ""
        cookies.save()
        return None

    # ❗ Kiểm tra session_id có tồn tại trong DB không
    if session_id not in user.get("sessions", []):
        cookies[SESSION_COOKIE_KEY] = ""
        cookies.save()
        return None

    return {
        "_id": str(user["_id"]),
        "username": user["username"],
        "full_name": user.get("full_name", user["username"]),
        "role": user.get("role", "employee"),
        "position": user.get("position", ""),
        "department": user.get("department", ""),
        "remaining_days": user.get("remaining_days", 0),
        "session_id": session_id
    }


def do_login(username, password):
    placeholder = st.empty()
    with placeholder:
        st.info("🔑 Đang đăng nhập...")
    time.sleep(0.4)

    user = USERS_COL.find_one({"username": username})
    if not user:
        placeholder.error("❌ Người dùng không tồn tại")
        time.sleep(1)
        placeholder.empty()
        return False

    if user.get("password") != password:
        placeholder.error("❌ Sai username hoặc password")
        time.sleep(1)
        placeholder.empty()
        return False

    # --- Tạo session_id riêng ---
    session_id = str(uuid.uuid4())

    # --- Lưu session_id vào DB ---
    USERS_COL.update_one(
        {"_id": user["_id"]},
        {
            "$addToSet": {"sessions": session_id},
            "$set": {"last_login_at": datetime.utcnow()}
        }
    )

    # --- Tạo JWT ---
    token, _ = create_jwt(user["_id"], session_id)

    # --- Lưu cookie trên trình duyệt ---
    cookies[SESSION_COOKIE_KEY] = token
    cookies.save()

    # --- Lưu thông tin user trong session_state ---
    st.session_state.update({
        "username": user["username"],
        "full_name": user.get("full_name", username),
        "role": user.get("role", "employee"),
        "position": user.get("position", ""),
        "department": user.get("department", ""),
        "remaining_days": user.get("remaining_days", 0),
        "session_id": session_id,
        "rerun_needed": True
    })

    placeholder.success(
        f"✅ Đăng nhập thành công! Chào {st.session_state['full_name']}")
    time.sleep(1)
    placeholder.empty()
    return True


def logout():
    token = cookies.get(SESSION_COOKIE_KEY)
    if token:
        payload = verify_jwt(token)
        if payload:
            user_id = payload.get("user_id")
            session_id = payload.get("session_id")
            if user_id and session_id:
                USERS_COL.update_one(
                    {"_id": ObjectId(user_id)},
                    {"$pull": {"sessions": session_id}}
                )

    # --- Xóa cookie ---
    cookies[SESSION_COOKIE_KEY] = ""
    cookies.save()

    # --- Xóa session_state ---
    for k in ["username", "role", "full_name", "position", "department", "remaining_days", "session_id"]:
        st.session_state.pop(k, None)

    st.session_state["rerun_needed"] = True


# ===============================
# LEAVE MANAGEMENT
# ===============================
def request_leave(username, start_date, end_date, duration, reason, leave_type, leave_case):
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

    LEAVES_COL.update_one(
        {"_id": ObjectId(l_id)},
        {"$set": {
            "status": "approved",
            "approved_by": st.session_state.get("full_name", "Admin"),
            "approved_at": now_str
        }}
    )

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
    LEAVES_COL.update_one(
        {"_id": ObjectId(l_id)},
        {"$set": {
            "status": "rejected",
            "approved_by": st.session_state.get("full_name", "Admin"),
            "approved_at": now_str
        }}
    )

    placeholder.error(
        f"❌ Yêu cầu của {user_name} đã bị từ chối lúc {now_str}!")
    time.sleep(1)
    placeholder.empty()
    st.session_state["rerun_needed"] = True
