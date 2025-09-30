import streamlit as st
from pymongo import MongoClient
from bson import ObjectId

# --- MongoDB Config ---
MONGO_URL = st.secrets["MONGO_URL"]
DB_NAME = "leave_management"

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Collections
users_col = db["users"]
leaves_col = db["leaves"]

# --- Functions ---


def login(username, password):
    return users_col.find_one({"username": username, "password": password})


def register(username, password, role="employee"):
    if users_col.find_one({"username": username}):
        return False
    users_col.insert_one(
        {"username": username, "password": password, "role": role})
    return True


def request_leave(username, date, reason):
    leaves_col.insert_one({
        "username": username,
        "date": date,
        "reason": reason,
        "status": "pending"
    })


def view_leaves(username=None):
    if username:
        return list(leaves_col.find({"username": username}))
    return list(leaves_col.find())


def update_leave_status(leave_id, new_status):
    leaves_col.update_one({"_id": ObjectId(leave_id)}, {
                          "$set": {"status": new_status}})


# --- Streamlit UI ---
st.title("🚀 Leave Management System")

if "username" not in st.session_state:
    choice = st.radio("Bạn muốn:", ["Đăng nhập", "Đăng ký"])

    if choice == "Đăng nhập":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = login(username, password)
            if user:
                st.session_state["username"] = user["username"]
                st.session_state["role"] = user.get("role", "employee")
                st.success(f"Xin chào {user['username']} 👋")
            else:
                st.error("Sai username hoặc password")

    else:  # Đăng ký
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Register"):
            if register(username, password):
                st.success("Đăng ký thành công! Hãy đăng nhập")
            else:
                st.error("Username đã tồn tại!")

else:
    st.write(
        f"Bạn đang đăng nhập với tài khoản: {st.session_state['username']} ({st.session_state['role']})")

    tab1, tab2 = st.tabs(["📅 Xin nghỉ", "📋 Quản lý"])

    with tab1:
        date = st.date_input("Ngày nghỉ")
        reason = st.text_area("Lý do")
        if st.button("Gửi yêu cầu"):
            request_leave(st.session_state["username"], str(date), reason)
            st.success("Đã gửi yêu cầu nghỉ!")

        st.subheader("Lịch sử xin nghỉ")
        for leave in view_leaves(st.session_state["username"]):
            st.write(
                f"- {leave['date']} | {leave['reason']} | {leave['status']}")

    if st.session_state["role"] == "admin":
        with tab2:
            st.subheader("Tất cả yêu cầu nghỉ")
            all_leaves = view_leaves()
            for leave in all_leaves:
                col1, col2, col3, col4 = st.columns([2, 2, 3, 3])
                with col1:
                    st.write(leave["username"])
                with col2:
                    st.write(leave["date"])
                with col3:
                    st.write(leave["reason"])
                with col4:
                    st.write(leave["status"])

                c1, c2 = st.columns(2)
                with c1:
                    if st.button(f"✅ Approve {leave['_id']}", key=f"a{leave['_id']}"):
                        update_leave_status(leave["_id"], "approved")
                        st.success(f"Đã duyệt nghỉ cho {leave['username']}")
                        st.rerun()
                with c2:
                    if st.button(f"❌ Reject {leave['_id']}", key=f"r{leave['_id']}"):
                        update_leave_status(leave["_id"], "rejected")
                        st.warning(f"Đã từ chối nghỉ của {leave['username']}")
                        st.rerun()

    if st.button("Đăng xuất"):
        st.session_state.clear()
