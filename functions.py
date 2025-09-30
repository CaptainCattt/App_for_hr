# functions.py
from bson import ObjectId
from datetime import datetime
import streamlit as st
import time
from settings import USERS_COL, LEAVES_COL, COOKIES, STATUS_COLORS


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
    placeholder = st.empty()
    with placeholder:
        st.info("📨 Đang gửi yêu cầu...")
    time.sleep(0.5)
    LEAVES_COL.insert_one({
        "username": username,
        "start_date": start_date.strftime("%Y-%m-%d") if not isinstance(start_date, str) else start_date,
        "end_date": end_date.strftime("%Y-%m-%d") if not isinstance(end_date, str) else end_date,
        "duration": duration,
        "reason": reason,
        "leave_type": leave_type,
        "leave_case": leave_case,
        "status": "pending",
        "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "approved_by": None,
        "approved_at": None
    })
    placeholder.success(
        f"📤 Yêu cầu '{leave_case}' từ {start_date} đến {end_date} ({duration} ngày) đã gửi!")
    time.sleep(3)
    placeholder.empty()


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
    LEAVES_COL.update_one({"_id": ObjectId(l_id)}, {
                          "$set": {"status": "rejected"}})
    placeholder.error(f"❌ Yêu cầu của {user_name} đã bị từ chối!")
    time.sleep(3)
    placeholder.empty()


def do_login(username, password):
    placeholder = st.empty()
    with placeholder:
        st.info("🔑 Đang đăng nhập...")
    time.sleep(0.5)

    user = USERS_COL.find_one({"username": username, "password": password})
    if user:
        # Lưu thông tin session
        st.session_state["username"] = user["username"]
        st.session_state["role"] = user.get("role", "employee")
        st.session_state["full_name"] = user.get("full_name", user["username"])
        st.session_state["position"] = user.get("position", "")
        st.session_state["department"] = user.get("department", "")
        st.session_state["remaining_days"] = user.get("remaining_days", 0)

        # Lưu cookie
        COOKIES["username"] = user["username"]
        COOKIES["role"] = user.get("role", "employee")
        COOKIES.save()

        placeholder.success(
            f"✅ Đăng nhập thành công! Chào {st.session_state['full_name']}")
    else:
        placeholder.error("❌ Sai username hoặc password")

    time.sleep(1)
    placeholder.empty()

    # Yêu cầu app rerun để cập nhật UI
    st.session_state["rerun_needed"] = True


def logout():
    placeholder = st.empty()
    with placeholder:
        st.info("🚪 Đang đăng xuất...")
    time.sleep(0.5)
    st.session_state.clear()
    COOKIES["username"] = ""
    COOKIES["role"] = ""
    COOKIES.save()
    placeholder.success("✅ Bạn đã đăng xuất thành công!")
    time.sleep(3)
    placeholder.empty()
    st.session_state["rerun_needed"] = True
