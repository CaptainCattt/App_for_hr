# functions.py
from bson import ObjectId
from datetime import datetime
import streamlit as st
import time
from settings import USERS_COL, LEAVES_COL, COOKIES, STATUS_COLORS

# --- User functions ---


def login(username, password):
    return USERS_COL.find_one({"username": username, "password": password})


def register(username, password, role="employee"):
    if USERS_COL.find_one({"username": username}):
        return False
    USERS_COL.insert_one(
        {"username": username, "password": password, "role": role})
    return True

# --- Leave functions ---


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
    with st.spinner("📨 Đang gửi yêu cầu..."):
        time.sleep(0.5)
        request_leave(username, start_date, end_date,
                      duration, reason, leave_type, leave_case)
        st.success(
            f"📤 Yêu cầu '{leave_case}' từ {start_date} đến {end_date} ({duration} ngày) đã gửi!")


def approve_leave(l_id, user_name):
    with st.spinner("✅ Đang duyệt..."):
        time.sleep(0.5)
        leave = LEAVES_COL.find_one({"_id": ObjectId(l_id)})
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Cập nhật status, người duyệt và thời gian duyệt
        LEAVES_COL.update_one(
            {"_id": ObjectId(l_id)},
            {"$set": {
                "status": "approved",
                "approved_by": st.session_state.get("full_name", "Admin"),
                "approved_at": now_str
            }}
        )

        # Nếu là Nghỉ phép năm, trừ remaining_days
        if leave.get("leave_type") == "Nghỉ phép năm":
            duration = float(leave.get("duration", 1))
            USERS_COL.update_one(
                {"username": user_name},
                {"$inc": {"remaining_days": -duration}}
            )

        st.success(
            f"✅ Yêu cầu của {user_name} đã được duyệt lúc {now_str} bởi {st.session_state.get('full_name', 'Admin')}!")


def reject_leave(l_id, user_name):
    with st.spinner("❌ Đang từ chối..."):
        time.sleep(0.5)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_leave_status(l_id, "rejected")
        st.error(f"❌ Yêu cầu của {user_name} đã bị từ chối lúc {now_str}!")


def do_login(username, password):
    with st.spinner("🔑 Đang đăng nhập..."):
        time.sleep(0.5)  # giả lập delay
        user = login(username, password)
        if user:
            st.session_state["username"] = user["username"]
            st.session_state["role"] = user.get("role", "employee")
            COOKIES["username"] = user["username"]
            COOKIES["role"] = user.get("role", "employee")
            COOKIES.save()
            st.success(f"✅ Đăng nhập thành công! Chào {user['username']}")
            time.sleep(0.5)  # cho người dùng thấy thông báo
            st.session_state["rerun_needed"] = True  # <-- dùng flag
        else:
            st.error("❌ Sai username hoặc password")


def logout():
    with st.spinner("🚪 Đang đăng xuất..."):
        time.sleep(0.5)
        st.session_state.clear()
        COOKIES["username"] = ""
        COOKIES["role"] = ""
        COOKIES.save()
        st.success("✅ Bạn đã đăng xuất thành công!")
        time.sleep(0.5)
        st.session_state["rerun_needed"] = True
