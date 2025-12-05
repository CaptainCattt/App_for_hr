# functions.py
from settings import USERS_COL
import streamlit as st
from datetime import datetime
from bson import ObjectId
import time
from settings import LEAVES_COL, USERS_COL, STATUS_COLORS, EMPLOYEES_COL, db
import pandas as pd
import io
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

    placeholder.success("✅ Đã duyệt !")
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

    placeholder.error("❌ Đã từ chối!")
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


def get_collections():
    """Danh sách collection trong db"""
    return db.list_collection_names()


def load_collection(col_name):
    """Load dữ liệu collection ra DataFrame"""
    col = db[col_name]
    data = list(col.find({}))
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["_id"] = df["_id"].astype(str)  # chuyển ObjectId về string để hiển thị
    return df


def save_dataframe(col_name, df):
    """
    Lưu DataFrame vào MongoDB
    - Dùng _id để quyết định update vs insert
    - Xóa những dòng bị xóa ở UI
    """
    col = db[col_name]

    # 1️⃣ Lấy danh sách _id cũ
    old_ids = set([str(doc["_id"]) for doc in col.find({}, {"_id": 1})])

    # 2️⃣ Lấy danh sách _id hiện có trong DataFrame
    if "_id" in df.columns:
        df["_id"] = df["_id"].astype(str)
        new_ids = set(df["_id"].dropna().tolist())
    else:
        df["_id"] = None
        new_ids = set()

    # 3️⃣ Xóa những dòng bị xóa trên UI
    ids_to_delete = old_ids - new_ids
    if ids_to_delete:
        col.delete_many({"_id": {"$in": [ObjectId(i) for i in ids_to_delete]}})

    # 4️⃣ Insert/Update từng dòng
    for _, row in df.iterrows():
        data = {k: v for k, v in row.to_dict().items() if pd.notnull(v)
                and k != "_id"}

        if row["_id"] and row["_id"].strip() != "None":
            # Update dòng cũ
            col.update_one({"_id": ObjectId(row["_id"])}, {"$set": data})
        else:
            # Insert dòng mới
            col.insert_one(data)


def to_excel(df):
    """Xuất DataFrame ra Excel"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()
