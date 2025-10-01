import streamlit as st
from datetime import date, timedelta, datetime
from settings import COOKIES
from functions import *
from bson import ObjectId
import time
from functools import partial
import pandas as pd

st.set_page_config(page_title="Request for Time Off", layout="wide")

st.markdown(
    """
    <div style='top: 30px; left: 40px; z-index: 1000;'>
        <img src='https://raw.githubusercontent.com/CaptainCattt/Report_of_shopee/main/logo-lamvlog.png' width='200'/>
    </div>
    <h1 style='text-align: center;'> 🏢 Hệ thống Quản lý Nghỉ phép 🏢</h1>""",
    unsafe_allow_html=True,
)

st.markdown("<br><br>", unsafe_allow_html=True)  # Tạo khoảng cách sau tiêu đề

# --- Restore session từ cookies ---
user = get_current_user()

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

    st.button(
        "🚀 Login",
        on_click=partial(do_login,
                         st.session_state.get("login_username", ""),
                         st.session_state.get("login_password", ""))
    )

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
        leave_type = st.selectbox(
            "Vui lòng chọn loại ngày nghỉ",
            ("Nghỉ phép năm", "Nghỉ không hưởng lương",
             "Nghỉ hưởng BHXH", "Nghỉ việc riêng có hưởng lương"),
            index=0  # bỏ horizontal
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

        if "leave_btn_disabled" not in st.session_state:
            st.session_state["leave_btn_disabled"] = False
        if "last_leave_request" not in st.session_state:
            st.session_state["last_leave_request"] = 0

        cooldown = 60  # giây
        now_ts = time.time()
        last_sent = st.session_state.get("last_leave_request", 0)
        remaining = max(0, int(cooldown - (now_ts - last_sent)))

        if "leave_btn_disabled" not in st.session_state:
            st.session_state["leave_btn_disabled"] = False
        if "show_cooldown_warning" not in st.session_state:
            st.session_state["show_cooldown_warning"] = False

        # Tự mở lại nếu hết cooldown
        if remaining <= 0:
            st.session_state["leave_btn_disabled"] = False
            st.session_state["show_cooldown_warning"] = False

        # Luôn render nút, chỉ khác disabled
        if st.button("📨 Gửi yêu cầu", disabled=st.session_state["leave_btn_disabled"]):
            if st.session_state["leave_btn_disabled"]:
                # Nếu đang cooldown → hiện flash warning
                st.session_state["show_cooldown_warning"] = True
            elif not reason_text.strip():
                st.warning("⚠️ Vui lòng nhập lý do nghỉ")
            else:
                # Khóa button và ghi timestamp
                st.session_state["leave_btn_disabled"] = True
                st.session_state["last_leave_request"] = now_ts

                # Gửi yêu cầu
                send_leave_request(
                    st.session_state["username"],
                    start_date,
                    end_date,
                    duration,
                    reason_text,
                    leave_type,
                    leave_case
                )

        # Flash warning trong 1.5s nếu spam bấm
        if st.session_state["show_cooldown_warning"]:
            placeholder = st.empty()
            placeholder.info(
                f"⏳ Vui lòng đợi {remaining} giây trước khi gửi yêu cầu tiếp theo."
            )
            time.sleep(1.5)
            placeholder.empty()
            st.session_state["show_cooldown_warning"] = False

            # Fix nhanh bug UI
        st.markdown("<br>"*15, unsafe_allow_html=True)

    # --- Tab quản lý admin ---
    if tab2 is not None:
        with tab2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown(
                "<h2 style='text-align: center;'> 🪪 Quản lý yêu cầu nghỉ 🪪</h2>",
                unsafe_allow_html=True
            )
            st.markdown("<br><br>", unsafe_allow_html=True)

            all_leaves = sorted(
                view_leaves(),
                key=lambda x: datetime.strptime(
                    x.get("requested_at", "1900-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S"
                ),
                reverse=True
            )

            if not all_leaves:
                st.info("Chưa có yêu cầu nghỉ nào.")
            else:
                st.markdown('<div class="scrollable-table">',
                            unsafe_allow_html=True)

                # Header
                header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([
                                                                                             2, 3, 2, 2, 2])
                header_col1.write("👤 Nhân viên")
                header_col2.write("📅 Thời gian")
                header_col3.write("♾️ Loại nghỉ")
                header_col4.write("📌 Trạng thái")
                header_col5.write("📝 Thao tác")

                st.markdown("---")

                # Rows
                for leave in all_leaves:
                    start = leave.get("start_date", "")
                    end = leave.get("end_date", "")
                    duration = leave.get("duration", "")
                    leave_type = leave.get("leave_type", "")
                    leave_case = leave.get("leave_case", "")
                    approved_by = leave.get("approved_by", "Chưa duyệt")
                    approved_at = leave.get("approved_at", "")
                    reason = leave.get("reason", "")
                    status = leave.get("status", "pending")

                    col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 2])
                    col1.write(leave.get("username", ""))
                    col2.write(f"{start} → {end} ({duration} ngày)")
                    col3.write(f"{leave_type} / {leave_case}")
                    col4.write(status_badge(status))

                    with col5:
                        if status == "pending":
                            btn_col1, btn_col2 = st.columns([1, 1])
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
                        else:
                            col5.write(f"✅ {approved_by} lúc {approved_at}")

                    # Thêm lý do bên dưới
                    st.caption(f"📝 {reason}")

                    st.markdown("---")

                st.markdown("<br><br>", unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

    # --- Tab lịch sử ---
    with tab3:
        st.subheader("📜 Lịch sử yêu cầu đã xin")
        # Lấy danh sách yêu cầu của user, sort theo start_date giảm dần
        scroll_style = """
            <style>
                .scrollable {
                    max-height: 400px;
                    overflow-y: auto;
                }
            </style>
        """
        st.markdown(scroll_style, unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="scrollable">', unsafe_allow_html=True)

            user_leaves = sorted(
                view_leaves(st.session_state["username"]),
                key=lambda x: datetime.strptime(
                    x.get("requested_at", "1900-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S"),
                reverse=True
            )
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

                col1, col2, col3, col4 = st.columns([1, 1, 2, 4])
                col1.write(f"📅 {start} → {end} ({duration} ngày)")
                col2.write(f"📝 {leave_type} / {leave_case}")
                col3.write(f"♾️Trạng thái: {status_badge(leave['status'])}")
                col4.write(
                    f"✅ Duyệt bởi: {approved_by}" if approved_by != "Chưa duyệt" else "")

                st.write(f"📝 Lý do: {leave['reason']}")
                if approved_at:
                    st.write(f"🕒 Duyệt lúc: {approved_at}")
                st.markdown("---")
