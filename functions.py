# functions.py
from settings import USERS_COL
import streamlit as st
from datetime import datetime
from bson import ObjectId
import time
from settings import LEAVES_COL, USERS_COL, STATUS_COLORS, EMPLOYEES_COL


# ===============================
# LEAVE MANAGEMENT FUNCTIONS
# ===============================

def send_leave_request(full_name, department, start_date, end_date, duration, reason, leave_type, leave_case):
    """Lưu yêu cầu nghỉ mới vào MongoDB"""
    start_str = start_date.strftime(
        "%Y-%m-%d") if not isinstance(start_date, str) else start_date
    end_str = end_date.strftime(
        "%Y-%m-%d") if not isinstance(end_date, str) else end_date

    LEAVES_COL.insert_one({
        "full_name": full_name,
        "department": department,
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


def view_leaves(status_filter=None):
    """Lấy danh sách tất cả yêu cầu nghỉ"""
    query = {}
    if status_filter:
        query["status"] = status_filter
    return list(LEAVES_COL.find(query))


def approve_leave(leave_id, hr_name):
    """Duyệt yêu cầu nghỉ"""
    placeholder = st.empty()
    with placeholder:
        st.info("⏳ Đang duyệt...")
    time.sleep(0.4)

    # Lấy thông tin yêu cầu nghỉ
    leave = LEAVES_COL.find_one({"_id": ObjectId(leave_id)})

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    LEAVES_COL.update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {
            "status": "approved",
            "approved_by": hr_name,
            "approved_at": now_str
        }}
    )

    # Nếu là nghỉ phép năm → trừ số ngày phép còn lại
    if leave and leave.get("leave_type") == "Nghỉ phép năm":
        emp_name = leave.get("full_name")
        duration = float(leave.get("duration", 0))
        EMPLOYEES_COL.update_one(
            {"full_name": emp_name},
            {"$inc": {"remaining_days": -duration}}
        )

    placeholder.success("✅ Đã duyệt yêu cầu nghỉ!")
    time.sleep(1)
    placeholder.empty()
    st.rerun()


def reject_leave(leave_id, hr_name):
    """Từ chối yêu cầu nghỉ"""
    placeholder = st.empty()
    with placeholder:
        st.info("🚫 Đang từ chối...")
    time.sleep(0.4)

    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    LEAVES_COL.update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {
            "status": "rejected",
            "approved_by": hr_name,
            "approved_at": now_str
        }}
    )

    placeholder.error("❌ Đã từ chối yêu cầu nghỉ!")
    time.sleep(1)
    placeholder.empty()
    st.rerun()


def status_badge(status: str):
    return STATUS_COLORS.get(status, status)


def check_admin_login(username_input, password_input):
    """Kiểm tra thông tin đăng nhập HR trong database"""
    user = USERS_COL.find_one({"username": username_input})
    if not user:
        st.error("❌ Không tìm thấy tài khoản trong database.")
        return False
    if user.get("password") != password_input:
        st.error("❌ Sai mật khẩu.")
        return False

    st.session_state["hr_logged_in"] = True
    st.session_state["hr_username"] = username_input
    st.session_state["admin_name"] = user.get("full_name", "Admin")
    st.success(f"🎉 Xin chào {user.get('full_name', 'Admin')}!")
    return True
