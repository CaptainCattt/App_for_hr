# app.py
import streamlit as st
from datetime import date
from settings import COOKIES
from functions import *

st.set_page_config(page_title="Leave Management", page_icon="📅", layout="wide")
st.title("🚀 Hệ thống Quản lý Nghỉ phép")

# --- Restore session ---
if "username" not in st.session_state and COOKIES.get("username"):
    st.session_state["username"] = COOKIES.get("username")
    st.session_state["role"] = COOKIES.get("role")

# --- Flags ---
if "rerun_needed" not in st.session_state:
    st.session_state["rerun_needed"] = False

if st.session_state.get("rerun_needed"):
    st.session_state["rerun_needed"] = False
    try:
        st.experimental_rerun()
    except AttributeError:
        pass

# --- Login UI ---
# Khởi tạo session state mặc định để tránh KeyError
for key, default in {
    "username": "",
    "full_name": "",
    "role": "",
    "remaining_days": 0,
    "department": "",
    "position": "",
    "dob": "",
    "phone": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

if not st.session_state["username"]:
    st.markdown("## 🔑 Đăng nhập hệ thống")
    username = st.text_input("👤 Username", key="login_username")
    password = st.text_input(
        "🔑 Password", type="password", key="login_password")

    if st.button("🚀 Login"):
        user = login(username, password)  # kiểm tra username/password
        if user:
            # Lưu thông tin vào session
            st.session_state["username"] = user.get("username", "")
            st.session_state["full_name"] = user.get(
                "full_name", st.session_state["username"])
            st.session_state["role"] = user.get("role", "employee")
            st.session_state["remaining_days"] = user.get("remaining_days", 12)
            st.session_state["department"] = user.get("department", "")
            st.session_state["position"] = user.get("position", "")
            st.session_state["dob"] = user.get("dob", "")
            st.session_state["phone"] = user.get("phone", "")

            # Lưu cookies
            COOKIES["username"] = st.session_state["username"]
            COOKIES["role"] = st.session_state["role"]
            COOKIES.save()

            st.success(f"✅ Chào mừng {st.session_state['full_name']}!")
            st.experimental_rerun()  # reload giao diện
        else:
            st.error("❌ Sai username hoặc password")

else:
    # Sidebar hiển thị thông tin user
    st.sidebar.success(
        f"👤 {st.session_state.get('full_name', st.session_state['username'])} ({st.session_state.get('role', '')})\n"
        f"Phòng ban: {st.session_state.get('department', '')}\n"
        f"Chức vụ: {st.session_state.get('position', '')}\n"
        f"Ngày sinh: {st.session_state.get('dob', '')}\n"
        f"SĐT: {st.session_state.get('phone', '')}\n"
        f"Ngày nghỉ còn lại: {st.session_state.get('remaining_days', 0)}"
    )

    if st.sidebar.button("🚪 Đăng xuất"):
        logout()

    # Tabs
    tab1, tab2 = st.tabs(["📅 Xin nghỉ", "📋 Quản lý"])

    # --- Tab xin nghỉ ---
    with tab1:
        st.subheader("📝 Gửi yêu cầu nghỉ")
        leave_date = st.date_input(
            "Chọn ngày nghỉ", value=date.today(), key="leave_date_input")
        reason = st.text_area("Lý do nghỉ", key="leave_reason_input")

        st.button(
            "📨 Gửi yêu cầu",
            key="send_leave_btn",
            on_click=lambda: send_leave_request(leave_date, reason)
        )

        st.divider()
        st.subheader("📜 Lịch sử xin nghỉ")
        leaves = sorted(
            view_leaves(st.session_state["username"]),
            key=lambda x: x["date"],
            reverse=True
        )
        if not leaves:
            st.info("Bạn chưa có yêu cầu nghỉ nào.")
        else:
            for i, leave in enumerate(leaves):
                with st.expander(f"{leave['date']} - {status_badge(leave['status'])}"):
                    st.write(f"**Lý do:** {leave['reason']}")

    # --- Tab quản lý (admin) ---
    if st.session_state["role"] == "admin":
        with tab2:
            st.subheader("📊 Quản lý yêu cầu nghỉ")
            all_leaves = sorted(
                view_leaves(), key=lambda x: x["date"], reverse=True)
            if not all_leaves:
                st.info("Chưa có yêu cầu nghỉ nào.")
            else:
                for idx, leave in enumerate(all_leaves):
                    with st.container():
                        st.markdown("---")
                        col1, col2, col3, col4 = st.columns([2, 2, 1, 1.5])
                        col1.write(f"👤 {leave['username']}")
                        col2.write(f"📅 {leave['date']}")
                        col3.empty()
                        col4.write(status_badge(leave['status']))
                        st.write(f"📝 {leave['reason']}")
                        st.write("")
                        st.write("")

                        if leave["status"] == "pending":
                            btn_col1, btn_col2 = st.columns([4, 1])
                            with btn_col1:
                                st.button(
                                    "✅ Duyệt",
                                    key=f"approve_{leave['_id']}",
                                    on_click=lambda l_id=leave["_id"], u=leave["username"]: approve_leave(
                                        l_id, u)
                                )
                            with btn_col2:
                                st.button(
                                    "❌ Từ chối",
                                    key=f"reject_{leave['_id']}",
                                    on_click=lambda l_id=leave["_id"], u=leave["username"]: reject_leave(
                                        l_id, u)
                                )
