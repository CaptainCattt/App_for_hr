# functions.py
import streamlit as st
from datetime import datetime, timedelta
from bson import ObjectId
import time
import uuid

from settings import USERS_COL, LEAVES_COL, COOKIES, STATUS_COLORS

SESSION_COOKIE_KEY = "session_token"


# ---------------------------
# Authentication (no DB sessions)
# ---------------------------

def get_current_user():
    """
    Lấy thông tin user hiện tại từ st.session_state.
    Nếu chưa có, kiểm tra cookie để populate session_state.
    """
    if "username" in st.session_state and st.session_state["username"]:
        return {
            "username": st.session_state["username"],
            "role": st.session_state.get("role", "employee"),
            "full_name": st.session_state.get("full_name", st.session_state["username"]),
            "position": st.session_state.get("position", ""),
            "department": st.session_state.get("department", ""),
            "remaining_days": st.session_state.get("remaining_days", 0)
        }

    # Kiểm tra cookie
    username = COOKIES.get(SESSION_COOKIE_KEY)
    if not username:
        return None

    user = USERS_COL.find_one({"username": username})
    if not user:
        COOKIES[SESSION_COOKIE_KEY] = ""
        COOKIES.save()
        return None

    # Populate session_state
    st.session_state["username"] = user["username"]
    st.session_state["role"] = user.get("role", "employee")
    st.session_state["full_name"] = user.get("full_name", user["username"])
    st.session_state["position"] = user.get("position", "")
    st.session_state["department"] = user.get("department", "")
    st.session_state["remaining_days"] = user.get("remaining_days", 0)
    return get_current_user()


def do_login(username, password):
    """
    Authenticate user.
    Nếu user chưa có trong DB thì tạo mới.
    Lưu trực tiếp session vào st.session_state + cookie.
    """
    placeholder = st.empty()
    with placeholder:
        st.info("🔑 Đang đăng nhập...")
    time.sleep(0.4)

    user = USERS_COL.find_one({"username": username})
    if not user:
        # Tạo user mới
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
        # Kiểm tra password
        if user.get("password") != password:
            placeholder.error("❌ Sai username hoặc password")
            time.sleep(1.2)
            placeholder.empty()
            return False

    # Tạo session_id cho lần login này
    session_id = str(uuid.uuid4())
    st.session_state["session_id"] = session_id

    # Populate session_state
    st.session_state["username"] = user["username"]
    st.session_state["role"] = user.get("role", "employee")
    st.session_state["full_name"] = user.get("full_name", user["username"])
    st.session_state["position"] = user.get("position", "")
    st.session_state["department"] = user.get("department", "")
    st.session_state["remaining_days"] = user.get("remaining_days", 0)

    # Lưu cookie đơn giản username (không còn token)
    COOKIES[SESSION_COOKIE_KEY] = username
    COOKIES.save()

    placeholder.success(
        f"✅ Đăng nhập thành công! Chào {st.session_state['full_name']}")
    time.sleep(1)
    placeholder.empty()

    st.session_state["rerun_needed"] = True
    return True


def logout():
    placeholder = st.empty()
    with placeholder:
        st.info("🚪 Đang đăng xuất...")
    time.sleep(0.4)

    # Clear session_state
    keys_to_clear = ["username", "role", "full_name",
                     "position", "department", "remaining_days", "session_id"]
    for k in keys_to_clear:
        if k in st.session_state:
            del st.session_state[k]

    # Clear cookie
    COOKIES[SESSION_COOKIE_KEY] = ""
    COOKIES.save()

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
