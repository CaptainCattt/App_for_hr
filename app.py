# app.py
import streamlit as st
from datetime import date
from settings import COOKIES
from functions import *
from datetime import timedelta

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
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Login UI ---
if not st.session_state.get("username", ""):
    st.markdown("## 🔑 Đăng nhập hệ thống")
    username = st.text_input("👤 Username", key="login_username")
    password = st.text_input(
        "🔑 Password", type="password", key="login_password")

    def handle_login():
        user = login(username, password)
        if user:
            # Lưu thông tin vào session
            st.session_state["username"] = user.get("username", "")
            st.session_state["full_name"] = user.get(
                "full_name", st.session_state["username"])
            st.session_state["role"] = user.get("role", "employee")
            st.session_state["remaining_days"] = user.get("remaining_days", 12)
            st.session_state["department"] = user.get("department", "")
            st.session_state["position"] = user.get("position", "")

            # Lưu cookies
            COOKIES["username"] = st.session_state["username"]
            COOKIES["role"] = st.session_state["role"]
            COOKIES.save()

            st.success(f"✅ Chào mừng {st.session_state["role"]} {st.session_state['full_name']} !")
            # reload UI để sidebar nhận dữ liệu
            st.session_state["rerun_needed"] = True
        else:
            st.error("❌ Sai username hoặc password")

    st.button("🚀 Login", on_click=handle_login)

else:
    # --- Sidebar hiển thị thông tin user ---
    st.sidebar.markdown("## 👤 Thông tin nhân viên")
    st.sidebar.write(f"**Họ tên:** {st.session_state.get('full_name', '')}")
    st.sidebar.write(f"**Username:** {st.session_state.get('username', '')}")
    st.sidebar.write(f"**Chức vụ:** {st.session_state.get('position', '')}")
    st.sidebar.write(
        f"**Phòng ban:** {st.session_state.get('department', '')}")

    st.sidebar.write(
        f"**Ngày nghỉ còn lại:** {st.session_state.get('remaining_days', 0)}")

    st.sidebar.button("🚪 Đăng xuất", on_click=logout)

    # Tabs
    tab1, tab2 = st.tabs(["📅 Xin nghỉ", "📋 Quản lý"])

    # --- Tab xin nghỉ ---
    with tab1:
        st.subheader("📝 Gửi yêu cầu nghỉ")

        # --- Chọn loại nghỉ chính ---
        leave_type = st.radio(
            "Vui lòng chọn loại ngày nghỉ mà bạn muốn",
            ("Nghỉ phép năm", "Nghỉ không hưởng lương",
             "Nghỉ hưởng BHXH", "Nghỉ việc riêng có hưởng lương"),
            index=0
        )

        # --- Chọn sub-option tùy loại ---
        if leave_type == "Nghỉ phép năm":
            leave_case = st.selectbox("Loại phép năm", ["Phép năm"])
        elif leave_type == "Nghỉ không hưởng lương":
            leave_case = st.selectbox("Lý do nghỉ không hưởng lương", [
                "Do hết phép năm",
                "Do việc cá nhân thời gian dài"
            ])
        elif leave_type == "Nghỉ hưởng BHXH":
            leave_case = st.selectbox("Lý do nghỉ hưởng BHXH", [
                "Bản thân ốm",
                "Con ốm",
                "Bản thân ốm dài ngày",
                "Chế độ thai sản cho nữ",
                "Chế độ thai sản cho nam",
                "Dưỡng sức (sau phẫu thuật, sau sinh, sau ốm, sau sẩy, nạo hút thai,...)",
                "Suy giảm khả năng lao động (15% - trên 51%)"
            ])
        elif leave_type == "Nghỉ việc riêng có hưởng lương":
            leave_case = st.selectbox("Lý do nghỉ việc riêng có hưởng lương", [
                "Bản thân kết hôn",
                "Con kết hôn",
                "Tang chế tư thân phụ mẫu (Bố/mẹ - vợ/chồng, vợ/chồng, con chết)"
            ])

        # --- Số ngày nghỉ ---
        duration = st.number_input(
            "Số ngày nghỉ",
            min_value=0.5,
            max_value=30.0,
            step=0.5,
            value=1.0,
            help="Nhập số ngày nghỉ (0.5, 1, 2, …)"
        )

        # --- Ngày bắt đầu / kết thúc ---
        start_date = st.date_input("Ngày bắt đầu nghỉ", value=date.today())
        end_date_default = start_date + timedelta(days=int(duration) - 1)
        end_date = st.date_input("Ngày kết thúc nghỉ", value=end_date_default)

        # --- Lý do ---
        reason = st.text_area("Lý do chi tiết")

        # --- Gửi yêu cầu ---
        if st.button("📨 Gửi yêu cầu"):
            if not reason.strip():
                st.warning("Vui lòng nhập lý do nghỉ")
            else:
                send_leave_request(
                    st.session_state["username"],
                    start_date,
                    end_date,
                    duration,
                    reason,
                    leave_type,
                    leave_case
                )

    # --- Tab quản lý (admin) ---
    if st.session_state["role"] == "admin":
        with tab2:
            st.subheader("📊 Quản lý yêu cầu nghỉ")
            all_leaves = sorted(
                view_leaves(),
                key=lambda x: x.get("start_date", "1900-01-01"),
                reverse=True
            )
            if not all_leaves:
                st.info("Chưa có yêu cầu nghỉ nào.")
            else:
                for idx, leave in enumerate(all_leaves):
                    with st.container():
                        st.markdown("---")
                        start = leave.get("start_date", "")
                        end = leave.get("end_date", "")
                        duration = leave.get("duration", "")
                        leave_type = leave.get("leave_type", "")
                        leave_case = leave.get("leave_case", "")
                        approved_by = leave.get("approved_by", "Chưa duyệt")
                        approved_at = leave.get("approved_at", "")

                        # Dòng chính: Username, Ngày nghỉ, Status
                        col1, col2, col3, col4 = st.columns([2, 2, 1, 1.5])
                        col1.write(f"👤 {leave['username']}")
                        col2.write(f"📅 {start} → {end} ({duration} ngày)")
                        col3.write(f"🗂 {leave_type} / {leave_case}")
                        col4.write(status_badge(leave['status']))

                        # Lý do nghỉ
                        st.write(f"📝 Lý do: {leave['reason']}")

                        # Ai duyệt & khi nào
                        if leave['status'] != "pending":
                            st.write(
                                f"✅ Duyệt bởi: {approved_by} lúc {approved_at}")

                        st.write("")  # Dòng trống

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
