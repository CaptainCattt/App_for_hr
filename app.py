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
        {"username": username, "password": password, "role": role}
    )
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
    leaves_col.update_one(
        {"_id": ObjectId(leave_id)},
        {"$set": {"status": new_status}}
    )

# --- Helpers ---


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
    # CSS cho form login
    st.markdown("""
        <style>
        .login-box {
            background-color: #ffffff;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 6px 15px rgba(0,0,0,0.15);
            max-width: 380px;
            margin: 80px auto;
            text-align: center;
        }
        .stTextInput>div>div>input {
            border-radius: 10px;
            border: 1px solid #ccc;
            padding: 12px;
        }
        .stButton>button {
            background: linear-gradient(90deg, #4CAF50, #45a049);
            color: white;
            font-weight: bold;
            border-radius: 10px;
            padding: 12px 24px;
            border: none;
            transition: 0.3s;
            width: 100%;
        }
        .stButton>button:hover {
            background: linear-gradient(90deg, #45a049, #3e8e41);
            transform: scale(1.03);
        }
        </style>
    """, unsafe_allow_html=True)

    # Form Login
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.markdown("## 🔑 Đăng nhập hệ thống")
    username = st.text_input("👤 Username")
    password = st.text_input("🔑 Password", type="password")

    if st.button("🚀 Login"):
        user = login(username, password)
        if user:
            st.session_state["username"] = user["username"]
            st.session_state["role"] = user.get("role", "employee")
            st.success(f"Xin chào {user['username']} 👋")
            st.rerun()
        else:
            st.error("❌ Sai username hoặc password")

    st.markdown("</div>", unsafe_allow_html=True)


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
