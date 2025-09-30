import streamlit as st
from datetime import date, timedelta, datetime
from settings import COOKIES
from functions import *
from bson import ObjectId
import time
from functools import partial

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

# --- Khởi tạo session state mặc định ---
for key, default in {
    "username": "",
    "full_name": "",
    "role": "",
    "remaining_days": 0,
    "department": "",
    "position": "",
    "leave_message": ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Hiển thị thông báo approve/reject ---
if st.session_state.get("leave_message"):
    st.info(st.session_state["leave_message"])
    st.session_state["leave_message"] = ""  # reset sau khi hiển thị

# --- Login UI ---
if not st.session_state.get("username"):
    st.markdown("## 🔑 Đăng nhập hệ thống")
    username = st.text_input("👤 Username", key="login_username")
    password = st.text_input(
        "🔑 Password", type="password", key="login_password")

    st.button("🚀 Login", on_click=do_login)

else:
    # --- Sidebar thông tin user ---
    st.sidebar.markdown("## 👤 Thông tin nhân viên")
    st.sidebar.write(f"**Họ tên:** {st.session_state['full_name']}")
    st.sidebar.write(f"**Username:** {st.session_state['username']}")
    st.sidebar.write(f"**Chức vụ:** {st.session_state['position']}")
    st.sidebar.write(f"**Phòng ban:** {st.session_state['department']}")
    st.sidebar.write(
        f"**Ngày nghỉ còn lại:** {st.session_state['remaining_days']}")

    st.sidebar.button("🚪 Đăng xuất", on_click=logout)

    # --- Tabs ---
    if st.session_state["role"] == "admin":
        tab1, tab3, tab2 = st.tabs(
            ["📅 Xin nghỉ", "📜 Lịch sử đã xin", "📋 Quản lý"])
    else:
        tab1, tab3 = st.tabs(["📅 Xin nghỉ", "📜 Lịch sử đã xin"])
        tab2 = None

    # --- Tab xin nghỉ ---
    with tab1:
        st.subheader("📝 Gửi yêu cầu nghỉ")
        leave_type = st.radio(
            "Vui lòng chọn loại ngày nghỉ",
            ("Nghỉ phép năm", "Nghỉ không hưởng lương",
             "Nghỉ hưởng BHXH", "Nghỉ việc riêng có hưởng lương"),
            index=0, horizontal=True
        )

        leave_case = ""
        if leave_type == "Nghỉ phép năm":
            leave_case = st.selectbox("Loại phép năm", ["Phép năm"])
        elif leave_type == "Nghỉ không hưởng lương":
            leave_case = st.selectbox("Lý do nghỉ không hưởng lương", [
                                      "Do hết phép năm", "Do việc cá nhân thời gian dài"])
        elif leave_type == "Nghỉ hưởng BHXH":
            leave_case = st.selectbox("Lý do nghỉ hưởng BHXH", [
                "Bản thân ốm", "Con ốm", "Bản thân ốm dài ngày",
                "Chế độ thai sản cho nữ", "Chế độ thai sản cho nam",
                "Dưỡng sức (sau phẫu thuật, sau sinh, sau ốm, ...)",
                "Suy giảm khả năng lao động (15% - trên 51%)"
            ])
        elif leave_type == "Nghỉ việc riêng có hưởng lương":
            leave_case = st.selectbox("Lý do nghỉ việc riêng có hưởng lương", [
                "Bản thân kết hôn", "Con kết hôn",
                "Tang chế tư thân phụ mẫu (Bố/mẹ - vợ/chồng, con chết)"
            ])

        col1, col2, col3 = st.columns(3)
        duration = col1.number_input(
            "Số ngày nghỉ", min_value=0.5, max_value=30.0, step=0.5, value=1.0)
        start_date = col2.date_input("Ngày bắt đầu nghỉ", value=date.today())
        end_date_default = start_date + timedelta(days=int(duration)-1)
        end_date = col3.date_input(
            "Ngày kết thúc nghỉ", value=end_date_default)
        reason_text = st.text_area("📝 Lý do chi tiết", height=100)

        # Lấy timestamp lần gửi gần nhất
        last_sent = st.session_state.get("last_leave_request", 0)
        now_ts = time.time()
        cooldown = 60  # giây

        if now_ts - last_sent < cooldown:
            remaining = int(cooldown - (now_ts - last_sent))
            warning_placeholder = st.empty()
            warning_placeholder.warning(
                f"⏳ Vui lòng đợi {remaining} giây trước khi gửi yêu cầu tiếp theo.")
            # 3 giây sau xóa thông báo
            time.sleep(3)
            warning_placeholder.empty()
            can_send = False
        else:
            can_send = True

        if st.button("📨 Gửi yêu cầu") and can_send:
            if not reason_text.strip():
                warning_placeholder = st.empty()
                warning_placeholder.warning("⚠️ Vui lòng nhập lý do nghỉ")
                time.sleep(3)
                warning_placeholder.empty()
            else:
                placeholder = st.empty()
                with placeholder:
                    st.info("📨 Đang gửi yêu cầu...")
                time.sleep(0.5)
                send_leave_request(
                    st.session_state["username"],
                    start_date,
                    end_date,
                    duration,
                    reason_text,
                    leave_type,
                    leave_case
                )
                placeholder.success("📤 Yêu cầu nghỉ đã được gửi!")
                st.session_state["last_leave_request"] = now_ts
                time.sleep(3)
                placeholder.empty()

    # --- Tab quản lý admin ---
    if tab2 is not None:
        with tab2:
            st.subheader("📊 Quản lý yêu cầu nghỉ")
            all_leaves = sorted(view_leaves(), key=lambda x: x.get(
                "start_date", "1900-01-01"), reverse=True)
            if not all_leaves:
                st.info("Chưa có yêu cầu nghỉ nào.")
            else:
                for leave in all_leaves:
                    with st.container():
                        st.markdown("---")
                        start = leave.get("start_date", "")
                        end = leave.get("end_date", "")
                        duration = leave.get("duration", "")
                        leave_type = leave.get("leave_type", "")
                        leave_case = leave.get("leave_case", "")
                        approved_by = leave.get("approved_by", "Chưa duyệt")
                        approved_at = leave.get("approved_at", "")

                        col1, col2, col3, col4 = st.columns([2, 2, 1, 1.5])
                        col1.write(f"👤 {leave['username']}")
                        col2.write(f"📅 {start} → {end} ({duration} ngày)")
                        col3.write(f"🗂 {leave_type} / {leave_case}")
                        col4.write(status_badge(
                            leave.get('status', 'pending')))

                        st.write(f"📝 Lý do: {leave.get('reason','')}")
                        if leave.get('status') != "pending":
                            st.write(
                                f"✅ Duyệt bởi: {approved_by} lúc {approved_at}")

                        if leave.get("status") == "pending":
                            btn_col1, btn_col2 = st.columns([4, 1])
                            approve_callback = partial(
                                approve_leave, leave["_id"], leave["username"])
                            reject_callback = partial(
                                reject_leave, leave["_id"], leave["username"])
                            with btn_col1:
                                st.button(
                                    "✅ Duyệt", key=f"approve_{leave['_id']}", on_click=approve_callback)
                            with btn_col2:
                                st.button(
                                    "❌ Từ chối", key=f"reject_{leave['_id']}", on_click=reject_callback)

    # --- Tab lịch sử ---
    with tab3:
        st.subheader("📜 Lịch sử yêu cầu đã xin")
        user_leaves = sorted(view_leaves(st.session_state["username"]), key=lambda x: x.get(
            "start_date", "1900-01-01"), reverse=True)
        if not user_leaves:
            st.info("Bạn chưa có yêu cầu nghỉ nào.")
        else:
            for leave in user_leaves:
                start = leave.get("start_date", "")
                end = leave.get("end_date", "")
                duration = leave.get("duration", "")
                leave_type = leave.get("leave_type", "")
                leave_case = leave.get("leave_case", "")
                approved_by = leave.get("approved_by", "Chưa duyệt")
                approved_at = leave.get("approved_at", "")

                col1, col2, col3, col4 = st.columns([2, 2, 1, 1.5])
                col1.write(f"📅 {start} → {end} ({duration} ngày)")
                col2.write(f"📝 {leave_type} / {leave_case}")
                col3.write(f"♾️Trạng thái: {status_badge(leave['status'])}")
                col4.write(
                    f"✅ Duyệt bởi: {approved_by}" if approved_by != "Chưa duyệt" else "")

                st.write(f"📝 Lý do: {leave['reason']}")
                if approved_at:
                    st.write(f"🕒 Duyệt lúc: {approved_at}")
                st.markdown("---")
