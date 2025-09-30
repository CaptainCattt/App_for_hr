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


def request_leave(username, date_str, reason):
    LEAVES_COL.insert_one({
        "username": username,
        "date": date_str,
        "reason": reason,
        "status": "pending"
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


def send_leave_request(username, leave_date, reason):
    with st.spinner("📨 Đang gửi yêu cầu..."):
        time.sleep(0.5)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        request_leave(username, str(leave_date), reason)
        st.success(f"📤 Yêu cầu nghỉ đã được gửi lúc {now_str}!")


def approve_leave(l_id, user_name):
    with st.spinner("✅ Đang duyệt..."):
        time.sleep(0.5)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_leave_status(l_id, "approved")
        st.success(f"✅ Yêu cầu của {user_name} đã được duyệt lúc {now_str}!")


def reject_leave(l_id, user_name):
    with st.spinner("❌ Đang từ chối..."):
        time.sleep(0.5)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_leave_status(l_id, "rejected")
        st.error(f"❌ Yêu cầu của {user_name} đã bị từ chối lúc {now_str}!")


def do_login(username, password):
    user = login(username, password)
    if user:
        st.session_state["username"] = user["username"]
        st.session_state["role"] = user.get("role", "employee")
        COOKIES["username"] = user["username"]
        COOKIES["role"] = user.get("role", "employee")
        COOKIES.save()
        st.success(f"✅ Đăng nhập thành công! Chào {user['username']}")
        st.session_state["rerun_needed"] = True
    else:
        st.error("❌ Sai username hoặc password")


def logout():
    st.session_state.clear()
    COOKIES["username"] = ""
    COOKIES["role"] = ""
    COOKIES.save()
    st.success("✅ Bạn đã đăng xuất thành công!")
    st.session_state["rerun_needed"] = True
