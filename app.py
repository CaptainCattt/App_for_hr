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

# --- Restore session from cookies ---
if "username" not in st.session_state:
    if cookies.get("username"):
        st.session_state["username"] = cookies.get("username")
        st.session_state["role"] = cookies.get("role")

# --- Flags for rerun ---
if "rerun_needed" not in st.session_state:
    st.session_state["rerun_needed"] = False

if "leave_submitted" not in st.session_state:
    st.session_state["leave_submitted"] = False

# --- Rerun if flag set ---
if st.session_state.get("rerun_needed"):
    st.session_state["rerun_needed"] = False


# --- Logout callback ---
def do_login(username, password):
    user = login(username, password)
    if user:
        st.session_state["username"] = user["username"]
        st.session_state["role"] = user.get("role", "employee")
        cookies["username"] = user["username"]
        cookies["role"] = user.get("role", "employee")

        cookies.save()
        st.session_state["rerun_needed"] = True

    else:
        st.error("❌ Sai username hoặc password")


def logout():
    st.session_state.clear()
    cookies["username"] = ""
    cookies["role"] = ""
    cookies.save()
    st.session_state["rerun_needed"] = True


def send_leave_request(leave_date, reason):
    request_leave(st.session_state["username"], str(leave_date), reason)
    st.session_state["rerun_needed"] = True


def approve_leave(l_id, user_name):
    update_leave_status(l_id, "approved")
    st.session_state["rerun_needed"] = True


def reject_leave(l_id, user_name):
    update_leave_status(l_id, "rejected")
    st.session_state["rerun_needed"] = True


# --- Login UI ---
if "username" not in st.session_state:
    st.markdown("## 🔑 Đăng nhập hệ thống")
    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")
    st.button("🚀 Login", on_click=do_login, args=(username, password))

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
        st.button("📨 Gửi yêu cầu", on_click=send_leave_request,
                  args=(leave_date, reason))

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
                        st.markdown("---")

                        # Dòng thông tin: Username, Ngày, Status
                        # Dòng thông tin: Username, Ngày, Status
                        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                        col1.write(f"👤 {leave['username']}")
                        col2.write(f"📅 {leave['date']}")
                        col3.empty()  # giữ khoảng trống
                        col4.write(status_badge(leave['status']))

                        # Lý do nghỉ
                        st.write(f"📝 {leave['reason']}")

                        # Dòng trống để tách các yêu cầu nghỉ
                        # hoặc st.markdown("<br>", unsafe_allow_html=True)
                        st.write("")

                        # Hai nút duyệt/từ chối luôn nằm **cùng dòng cuối**
                        if leave["status"] == "pending":
                            btn_col1, btn_col2 = st.columns([4, 1])
                            with btn_col1:
                                st.button(
                                    "✅ Duyệt", key=f"a{leave['_id']}",
                                    on_click=approve_leave,
                                    args=(leave["_id"], leave["username"])
                                )
                            with btn_col2:
                                st.button(
                                    "❌ Từ chối", key=f"r{leave['_id']}",
                                    on_click=reject_leave,
                                    args=(leave["_id"], leave["username"])
                                )
