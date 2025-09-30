import streamlit as st
from pymongo import MongoClient
from bson import ObjectId
from streamlit_cookies_manager import EncryptedCookieManager
from datetime import date
import time

# --- MongoDB Config ---
MONGO_URL = st.secrets["MONGO_URL"]
DB_NAME = "leave_management"

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Collections
users_col = db["users"]
leaves_col = db["leaves"]

# --- Cookie Config ---
cookies = EncryptedCookieManager(
    prefix="leave_mgmt",
    password=st.secrets["COOKIE_PASSWORD"],
)
if not cookies.ready():
    st.stop()

# --- Functions ---


def login(username, password):
    return users_col.find_one({"username": username, "password": password})


def register(username, password, role="employee"):
    if users_col.find_one({"username": username}):
        return False
    users_col.insert_one(
        {"username": username, "password": password, "role": role})
    return True


def request_leave(username, date_str, reason):
    leaves_col.insert_one({
        "username": username,
        "date": date_str,
        "reason": reason,
        "status": "pending"
    })


def view_leaves(username=None):
    if username:
        return list(leaves_col.find({"username": username}))
    return list(leaves_col.find())


def update_leave_status(leave_id, new_status):
    leaves_col.update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {"status": new_status}}
    )


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

# --- Restore session from cookies ---
if "username" not in st.session_state:
    if cookies.get("username"):
        st.session_state["username"] = cookies.get("username")
        st.session_state["role"] = cookies.get("role")

# --- Logout callback ---


def logout():
    st.session_state.clear()
    cookies["username"] = ""
    cookies["role"] = ""
    cookies.save()
    with st.spinner("⏳ Đang đăng xuất, vui lòng đợi..."):
        time.sleep(3)
    st.experimental_rerun()


# --- Login UI ---
if "username" not in st.session_state:
    st.markdown("## 🔑 Đăng nhập hệ thống")
    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")

    def do_login():
        with st.spinner("⏳ Đang đăng nhập..."):
            time.sleep(1)
            user = login(username, password)
            if user:
                st.session_state["username"] = user["username"]
                st.session_state["role"] = user.get("role", "employee")
                cookies["username"] = user["username"]
                cookies["role"] = user.get("role", "employee")
                cookies.save()
                st.success(f"Xin chào {user['username']} 👋")
                time.sleep(1)
                st.experimental_rerun()
            else:
                st.error("❌ Sai username hoặc password")

    st.button("🚀 Login", on_click=do_login)

else:
    # Sidebar user info
    st.sidebar.success(
        f"👤 {st.session_state['username']} ({st.session_state['role']})")
    st.sidebar.button("🚪 Đăng xuất", on_click=logout)

    # Tabs
    tab1, tab2 = st.tabs(["📅 Xin nghỉ", "📋 Quản lý"])

    # --- Tab xin nghỉ ---
    with tab1:
        st.subheader("📝 Gửi yêu cầu nghỉ")
        leave_date = st.date_input("Ngày nghỉ", value=date.today())
        reason = st.text_area("Lý do")

        def send_leave_request():
            with st.spinner("⏳ Đang gửi yêu cầu nghỉ..."):
                time.sleep(1)
                request_leave(
                    st.session_state["username"], str(leave_date), reason)
                st.success("✅ Đã gửi yêu cầu nghỉ!")
                time.sleep(1)
                st.experimental_rerun()

        st.button("📨 Gửi yêu cầu", on_click=send_leave_request)

        st.divider()
        st.subheader("📜 Lịch sử xin nghỉ")
        leaves = view_leaves(st.session_state["username"])
        if not leaves:
            st.info("Bạn chưa có yêu cầu nghỉ nào.")
        else:
            for leave in leaves:
                with st.expander(f"{leave['date']} - {status_badge(leave['status'])}"):
                    st.write(f"**Lý do:** {leave['reason']}")

    # --- Tab quản lý (admin) ---
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
                            def approve_leave(l_id=leave["_id"], user_name=leave["username"]):
                                with st.spinner(f"⏳ Đang duyệt nghỉ cho {user_name}..."):
                                    time.sleep(1)
                                    update_leave_status(l_id, "approved")
                                    st.success(
                                        f"Đã duyệt nghỉ cho {user_name}")
                                    time.sleep(1)
                                    st.experimental_rerun()

                            def reject_leave(l_id=leave["_id"], user_name=leave["username"]):
                                with st.spinner(f"⏳ Đang từ chối nghỉ của {user_name}..."):
                                    time.sleep(1)
                                    update_leave_status(l_id, "rejected")
                                    st.warning(
                                        f"Đã từ chối nghỉ của {user_name}")
                                    time.sleep(1)
                                    st.experimental_rerun()

                            c1, c2 = st.columns(2)
                            with c1:
                                st.button(
                                    "✅ Duyệt", key=f"a{leave['_id']}", on_click=approve_leave)
                            with c2:
                                st.button(
                                    "❌ Từ chối", key=f"r{leave['_id']}", on_click=reject_leave)
