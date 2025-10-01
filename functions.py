# functions.py
from bson import ObjectId
from datetime import datetime, timedelta
import streamlit as st
import time
import secrets
from settings import USERS_COL, LEAVES_COL, COOKIES, STATUS_COLORS, SESSIONS_COL


def get_current_user():
    token = COOKIES.get("session_token")
    if not token:
        return None

    session = SESSIONS_COL.find_one({"token": token})
    if not session:
        return None

    # Nếu session hết hạn thì xóa đi
    if session["expired_at"] < datetime.now():
        SESSIONS_COL.delete_one({"token": token})
        COOKIES["session_token"] = ""
        COOKIES.save()
        return None

    return {
        "username": session["username"],
        "role": session["role"]
    }


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
        "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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

# --- UI helper ---


def status_badge(status: str):
    return STATUS_COLORS.get(status, status)

# --- Callbacks with spinner + notification ---


def send_leave_request(username, start_date, end_date, duration, reason, leave_type, leave_case):
    # --- Khóa button ngay khi bấm ---
    st.session_state["leave_btn_disabled"] = True
    st.session_state["last_leave_request"] = time.time()

    # Chuẩn hóa ngày
    start_str = start_date.strftime(
        "%Y-%m-%d") if not isinstance(start_date, str) else start_date
    end_str = end_date.strftime(
        "%Y-%m-%d") if not isinstance(end_date, str) else end_date

    # Insert vào DB
    LEAVES_COL.insert_one({
        "username": username,
        "start_date": start_str,
        "end_date": end_str,
        "duration": duration,
        "reason": reason,
        "leave_type": leave_type,
        "leave_case": leave_case,
        "status": "pending",
        "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "approved_by": None,
        "approved_at": None
    })

    # Thông báo thành công
    st.success(
        f"📤 Yêu cầu '{leave_case}' từ {start_str} đến {end_str} ({duration} ngày) đã gửi!"
    )


def approve_leave(l_id, user_name):
    placeholder = st.empty()
    with placeholder:
        st.info("✅ Đang duyệt...")
    time.sleep(0.5)
    leave = LEAVES_COL.find_one({"_id": ObjectId(l_id)})
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
    time.sleep(3)
    placeholder.empty()


def reject_leave(l_id, user_name):
    placeholder = st.empty()
    with placeholder:
        st.info("❌ Đang từ chối...")
    time.sleep(0.5)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
    time.sleep(3)
    placeholder.empty()


def do_login(username, password):
    placeholder = st.empty()
    user = USERS_COL.find_one({"username": username, "password": password})
    if user:
        # Tạo session token
        token = secrets.token_hex(16)
        expire_time = datetime.now() + timedelta(hours=12)

        # Lưu session vào MongoDB
        SESSIONS_COL.insert_one({
            "token": token,
            "username": user["username"],
            "role": user.get("role", "employee"),
            "expired_at": expire_time
        })

        # Lưu token vào cookie
        COOKIES["session_token"] = token
        COOKIES.save()

        # Lưu session_state (chỉ để tiện render UI lần đầu)
        st.session_state["username"] = user["username"]
        st.session_state["role"] = user.get("role", "employee")
        st.session_state["full_name"] = user.get("full_name", user["username"])
        st.session_state["position"] = user.get("position", "")
        st.session_state["department"] = user.get("department", "")
        st.session_state["remaining_days"] = user.get("remaining_days", 0)

        placeholder.success(
            f"✅ Đăng nhập thành công! Chào {st.session_state['full_name']}")
    else:
        placeholder.error("❌ Sai username hoặc password")

    time.sleep(1.5)
    placeholder.empty()

    # Rerun để cập nhật UI
    st.session_state["rerun_needed"] = True


def logout():
    placeholder = st.empty()
    with placeholder:
        st.info("🚪 Đang đăng xuất...")
    time.sleep(0.5)

    token = COOKIES.get("session_token")
    if token:
        SESSIONS_COL.delete_one({"token": token})

    st.session_state.clear()

    COOKIES["session_token"] = ""
    COOKIES.save()

    placeholder.success("✅ Bạn đã đăng xuất thành công!")
    time.sleep(1.5)
    placeholder.empty()

    # Trigger rerun để update UI
    st.session_state["rerun_needed"] = True
