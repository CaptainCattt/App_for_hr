import streamlit as st
from pymongo import MongoClient
from bson import ObjectId
import bcrypt

# --- MongoDB Config ---
MONGO_URL = st.secrets["MONGO_URL"]
DB_NAME = "leave_management"

client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)  # tránh treo
db = client[DB_NAME]

# Collections
users_col = db["users"]
leaves_col = db["leaves"]

# --- Auth Helpers ---


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def register_user(username, password, role="employee"):
    if users_col.find_one({"username": username}):
        return False
    hashed_pw = hash_password(password)
    users_col.insert_one(
        {"username": username, "password": hashed_pw, "role": role})
    return True


def validate_user(username, password):
    user = users_col.find_one({"username": username})
    if not user:
        return None
    if check_password(password, user["password"]):
        return user
    return None

# --- Leave functions ---


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


def status_badge(status: str):
    colors = {
        "pending": "🟡 Chờ duyệt",
        "approved": "🟢 Đã duyệt",
        "rejected": "🔴 Từ chối"
    }
    return colors.get(status, status)


# --- Streamlit UI ---
st.set_page_config(page_title="Leave Management", page_icon="📅", layout="wide")
st.title("🚀 Hệ thống Quản lý Nghỉ phép")

if "username" not in st.session_state:
    st.markdown("## 🔑 Đăng nhập hệ thống")
    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")

    if st.button("🚀 Login"):
        user = validate_user(username, password)
        if user:
            st.session_state["username"] = user["username"]
            st.session_state["role"] = user.get("role", "employee")
            st.success(f"Xin chào {user['username']} 👋")
            st.rerun()
        else:
            st.error("❌ Sai username hoặc password")

    st.info("👉 Nếu chưa có tài khoản, hãy đăng ký bên dưới:")
    new_user = st.text_input("Tạo username mới")
    new_pass = st.text_input("Tạo password mới", type="password")
    if st.button("📝 Đăng ký"):
        if register_user(new_user, new_pass):
            st.success("✅ Tạo tài khoản thành công! Hãy đăng nhập.")
        else:
            st.warning("⚠️ Username đã tồn tại.")

else:
    st.sidebar.success(
        f"👤 {st.session_state['username']} ({st.session_state['role']})")
    if st.sidebar.button("🚪 Đăng xuất"):
        st.session_state.clear()
        st.rerun()

    tab1, tab2 = st.tabs(["📅 Xin nghỉ", "📋 Quản lý"])

    with tab1:
        st.subheader("📝 Gửi yêu cầu nghỉ")
        date = st.date_input("Ngày nghỉ")
        reason = st.text_area("Lý do")
        if st.button("📨 Gửi yêu cầu"):
            request_leave(st.session_state["username"], str(date), reason)
            st.success("✅ Đã gửi yêu cầu nghỉ!")

        st.divider()
        st.subheader("📜 Lịch sử xin nghỉ")
        leaves = view_leaves(st.session_state["username"])
        if not leaves:
            st.info("Bạn chưa có yêu cầu nghỉ nào.")
        else:
            for leave in leaves:
                with st.expander(f"{leave['date']} - {status_badge(leave['status'])}"):
                    st.write(f"**Lý do:** {leave['reason']}")

    if st.session_state["role"] == "admin":
        with tab2:
            st.subheader("📊 Quản lý yêu cầu nghỉ")
            all_leaves = view_leaves()
            if not all_leaves:
                st.info("Chưa có yêu cầu nghỉ nào.")
            else:
                for leave in all_leaves:
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 2, 3, 3])
                        col1.write(f"👤 {leave['username']}")
                        col2.write(f"📅 {leave['date']}")
                        col3.write(f"📝 {leave['reason']}")
                        col4.write(status_badge(leave['status']))

                        if leave["status"] == "pending":
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button(f"✅ Duyệt", key=f"a{leave['_id']}"):
                                    update_leave_status(
                                        leave["_id"], "approved")
                                    st.success(
                                        f"Đã duyệt nghỉ cho {leave['username']}")
                                    st.rerun()
                            with c2:
                                if st.button(f"❌ Từ chối", key=f"r{leave['_id']}"):
                                    update_leave_status(
                                        leave["_id"], "rejected")
                                    st.warning(
                                        f"Đã từ chối nghỉ của {leave['username']}")
                                    st.rerun()
