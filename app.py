import streamlit as st
from datetime import date, timedelta
from functions import send_leave_request, view_leaves, approve_leave, reject_leave, status_badge, check_admin_login
from settings import EMPLOYEES_COL, LEAVES_COL
from datetime import datetime

# ===============================
# CẤU HÌNH CƠ BẢN
# ===============================
# ⚙️ Tắt các log cảnh báo (bao gồm cả st.cache deprecated)
st.set_page_config(
    page_title="Hệ thống xin nghỉ - Lâm Media",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
    /* Logo và tiêu đề responsive */
    .header-container {
        text-align: center;
        margin-top: 10px;
    }

    .header-container img {
        width: 200px;
    }

    .header-container h1 {
        font-size: 48px;
        font-weight: bold;
        margin-top: 10px;
    }

    /* Khi hiển thị trên điện thoại (màn hình nhỏ) */
    @media (max-width: 600px) {
        .header-container img {
            width: 180px;
        }
        .header-container h1 {
            font-size: 36px;
            line-height: 1.2;
        }
    }
    </style>

    <div class='header-container'>
        <img src='https://raw.githubusercontent.com/CaptainCattt/Report_of_shopee/main/logo-lamvlog.png'/>
        <h1>🏢 Yêu cầu Nghỉ phép 🏢</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("🔐 Đăng nhập HR")
    username = st.text_input("👤 Tên đăng nhập")
    password = st.text_input("🔑 Mật khẩu", type="password")

    if st.button("Đăng nhập"):
        if check_admin_login(username, password):
            st.rerun()

    if st.session_state.get("hr_logged_in"):
        st.success(f"Xin chào, {st.session_state.get('admin_name', 'Admin')}!")
        if st.button("Đăng xuất"):
            st.session_state.clear()
            st.rerun()


tabs = ["📝 Yêu cầu"]
if "hr_logged_in" in st.session_state and st.session_state.hr_logged_in:
    tabs.extend(["👩‍💼 Quản lý yêu cầu", "📊 Dashboard nhân viên"])

tab_objects = st.tabs(tabs)

# ===============================
# TAB 1: FORM XIN NGHỈ
# ===============================
with tab_objects[0]:

    # --- Khởi tạo biến session để lưu thời điểm bấm nút ---
    if "last_submit_time" not in st.session_state:
        st.session_state["last_submit_time"] = None

    cooldown_seconds = 60  # Thời gian chờ giữa các lần gửi

    tab_objects[0].subheader("📝 Gửi yêu cầu nghỉ")

    # --- Các phần nhập liệu như trước ---
    # Lấy danh sách nhân viên
    employees = list(EMPLOYEES_COL.find(
        {}, {"_id": 0, "full_name": 1, "department": 1, "position": 1, "remaining_days": 1}))
    employee_names = [emp["full_name"] for emp in employees]

    selected_name = st.selectbox("👤 Chọn tên của bạn", employee_names)

    selected_emp = next(
        (e for e in employees if e["full_name"] == selected_name), None)
    department = selected_emp.get("department", "") if selected_emp else ""
    position = selected_emp.get("position", "") if selected_emp else ""
    remaining_days = selected_emp.get(
        "remaining_days", 0) if selected_emp else 0

    st.text_input("🏢 Phòng ban", department, disabled=True)

    # Chọn loại nghỉ
    leave_type = st.selectbox(
        "Vui lòng chọn loại ngày nghỉ",
        ("Nghỉ phép năm", "Nghỉ không hưởng lương",
         "Nghỉ hưởng BHXH", "Nghỉ việc riêng có hưởng lương"),
        index=0
    )

    leave_case = ""
    if leave_type == "Nghỉ phép năm":
        leave_case = st.selectbox("Loại phép năm", ["Phép năm"])
    elif leave_type == "Nghỉ không hưởng lương":
        leave_case = st.selectbox("Lý do nghỉ không hưởng lương", [
            "Do hết phép năm", "Do việc cá nhân thời gian dài"
        ])
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
    end_date = col3.date_input("Ngày kết thúc nghỉ", value=end_date_default)
    reason_text = st.text_area("📝 Lý do chi tiết", height=100)

    # --- Kiểm tra cooldown ---
    now = datetime.now()
    if st.session_state["last_submit_time"]:
        elapsed = (now - st.session_state["last_submit_time"]).total_seconds()
    else:
        elapsed = cooldown_seconds + 1  # cho phép bấm lần đầu

    button_disabled = elapsed < cooldown_seconds
    cooldown_remaining = int(
        cooldown_seconds - elapsed) if button_disabled else 0

    if button_disabled:
        st.info(f"⏳ Vui lòng chờ {cooldown_remaining} giây trước khi gửi lại.")
    else:
        if st.button("📨 Gửi yêu cầu"):
            if not reason_text.strip():
                st.warning("⚠️ Vui lòng nhập lý do nghỉ.")
            else:
                # Gọi hàm gửi yêu cầu
                send_leave_request(
                    selected_name, department, start_date,
                    end_date, duration, reason_text, leave_type, leave_case
                )
                st.success("✅ Yêu cầu đã được gửi!")
                # Lưu thời điểm lần bấm nút
                st.session_state["last_submit_time"] = datetime.now()
    # ===============================
    # TAB 2: HR QUẢN LÝ
    # ===============================
    if len(tabs) > 1:
        with tab_objects[1]:
            st.markdown("""
                <h2 style='text-align: center; color: #1e3d59;'>
                    👩‍💼 Quản lý nghỉ phép
                </h2>
            """, unsafe_allow_html=True)

            # --- Bộ lọc dữ liệu ---
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

            with col1:
                # Tìm theo tên nhân viên, mặc định rỗng
                search_name = st.text_input("Tìm theo tên nhân viên", value="")

            with col2:
                # Trạng thái, mặc định "Tất cả"
                status_filter = st.selectbox(
                    "Trạng thái", ["Tất cả", "pending", "approved", "rejected"], index=0
                )
                query_status = None if status_filter == "Tất cả" else status_filter

            with col3:
                # Phòng ban, mặc định "Tất cả"
                department_filter = st.selectbox(
                    "Phòng ban", ["Tất cả", "Kinh doanh", "Marketing", "IT", "Editor"], index=0
                )
                department = None if department_filter == "Tất cả" else department_filter

            with col4:
                # Năm, mặc định năm hiện tại
                year_options = [
                    "Tất cả"] + [str(y) for y in range(2024, datetime.now().year + 1)]
                selected_year = st.selectbox(
                    "Năm", options=year_options, index=year_options.index(str(datetime.now().year))
                )

            with col5:
                # Tháng, mặc định tháng hiện tại
                month_options = ["Tất cả"] + [f"{i:02d}" for i in range(1, 13)]
                selected_month = st.selectbox(
                    "Tháng", options=month_options, index=datetime.now().month
                )

            # --- Lấy dữ liệu từ DB ---
            leaves = view_leaves(query_status)

            # --- Lọc theo tên ---
            if search_name:
                leaves = [l for l in leaves if search_name.lower() in l.get(
                    "full_name", "").lower()]

            # --- Lọc theo phòng ban ---
            if department:
                leaves = [l for l in leaves if l.get(
                    "department") == department]

            # --- Lọc theo tháng/năm ---
            filtered_leaves = []
            for leave in leaves:
                try:
                    start_date = leave.get("start_date")
                    if not start_date:
                        continue
                    year = start_date[:4]
                    month = start_date[5:7]

                    # Điều kiện lọc động
                    if (
                        (selected_year == "Tất cả" or year == selected_year)
                        and (selected_month == "Tất cả" or month == selected_month)
                    ):
                        filtered_leaves.append(leave)
                except Exception:
                    continue

            def parse_requested_at(leave):
                ra = leave.get("requested_at")
                if not ra:
                    return datetime.min
                try:
                    return datetime.strptime(ra, "%Y-%m-%d %H:%M:%S")
                except:
                    return datetime.min

            # Sắp xếp giảm dần theo thời gian gửi
            filtered_leaves.sort(key=parse_requested_at, reverse=True)

            # --- Hiển thị kết quả ---
            if not filtered_leaves:
                st.info(
                    f"🕊️ Không có yêu cầu nghỉ nào.")
            else:
                for leave in filtered_leaves:
                    status = leave.get("status", "")

                    # Tiêu đề expander bình thường
                    expander_title = f"📄 {leave.get('full_name', '')} | 📌 {leave.get('leave_case', '')} | {status_badge(status)}"

                    with st.expander(expander_title):
                        st.write(
                            f"**Phòng ban:** {leave.get('department', '')}")
                        st.write(
                            f"**Thời gian:** {leave.get('start_date')} → {leave.get('end_date')} ({leave.get('duration')} ngày)")
                        st.write(f"**Loại nghỉ:** {leave.get('leave_type')}")
                        st.write(
                            f"**Trường hợp nghỉ:** {leave.get('leave_case')}")
                        st.write(
                            f"**Lý do chi tiết:** {leave.get('reason', '')}")

                        # Hiển thị trạng thái với màu
                        if status == "pending":
                            st.write(f"**Trạng thái:** {status_badge(status)}")
                        elif status == "approved":
                            st.markdown(
                                f"**Trạng thái:** <span style='color:green;'>{status}</span>", unsafe_allow_html=True)
                        elif status == "rejected":
                            st.markdown(
                                f"**Trạng thái:** <span style='color:red;'>{status}</span>", unsafe_allow_html=True)
                        else:
                            st.write(f"**Trạng thái:** {status}")

                        st.write(
                            f"**Gửi lúc:** {leave.get('requested_at', '')}")
                        st.markdown("<br>", unsafe_allow_html=True)

                        if leave.get("approved_by"):
                            st.write(
                                f"**Phê duyệt bởi:** {leave.get('approved_by')} lúc {leave.get('approved_at')}")

                        # Nút duyệt/từ chối chỉ cho pending
                        if status == "pending":
                            col_left, col_spacer, col_right = st.columns([
                                                                         1, 3, 1])
                            with col_left:
                                if st.button("✅ Duyệt", key=f"approve_{leave['_id']}"):
                                    approve_leave(
                                        leave["_id"], st.session_state.hr_username)
                            with col_right:
                                if st.button("❌ Từ chối", key=f"reject_{leave['_id']}"):
                                    reject_leave(
                                        leave["_id"], st.session_state.hr_username)

    if len(tabs) > 2:
        with tab_objects[2]:
            st.markdown("""
                <h2 style='text-align: center; color: #1e3d59;'>
                    📊 Dashboard tổng hợp
                </h2>
            """, unsafe_allow_html=True)

            # --- Kiểm tra đăng nhập HR ---
            if "hr_logged_in" not in st.session_state:
                st.warning(
                    "⚠️ Bạn cần đăng nhập ở tab 'Dành cho HR' để xem Dashboard.")
                st.stop()
            employees = list(EMPLOYEES_COL.find({}, {"_id": 0}))
            employee_names = [emp["full_name"] for emp in employees]

            selected_emp_name = st.selectbox(
                "👤 Chọn nhân viên", employee_names)

            selected_emp = next(
                (e for e in employees if e["full_name"] == selected_emp_name), None)

            if not selected_emp:
                st.error("❌ Không tìm thấy thông tin nhân viên.")
                st.stop()

            # --- Thông tin cơ bản ---
            emp_name = selected_emp.get("full_name", "")
            department = selected_emp.get("department", "")
            position = selected_emp.get("position", "")
            dob = selected_emp.get("dob", "-")
            phone = selected_emp.get("phone", "-")
            remaining = selected_emp.get("remaining_days", 0)

            st.markdown(f"""
                <style>
                    .info-wrapper {{
                        display: flex;
                        justify-content: center;
                        margin-top: 20px;
                    }}
                    .info-card {{
                        background-color: #ffffff;
                        padding: 25px 30px;
                        border-radius: 15px;
                        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
                        width: 95%;
                        max-width: 1000px;  /* 👉 tăng từ 800 lên 1000 */
                        transition: all 0.3s ease;
                        font-family: "Segoe UI", sans-serif;
                    }}
                    .info-header {{
                        font-size: 1.2rem;
                        font-weight: 800;
                        color: #2c3e50;
                        margin-bottom: 15px;
                        text-align: center;
                        font-weight: 900;
                    }}
                    .info-flex {{
                        display: flex;
                        flex-direction: row;
                        flex-wrap: wrap;
                        justify-content: space-between;
                        align-items: center;
                        gap: 15px;  /* 👉 giảm gap để các item gần nhau hơn */
                    }}
                    .info-item {{
                        flex: 1;
                        min-width: 250px;
                        text-align: center;
                        line-height: 1.8;
                        color: #333;
                        font-size: 0.95rem;
                        word-break: keep-all; /* ✅ giữ tên trên cùng 1 dòng */
                        white-space: nowrap;
                    }}
                    .badge {{
                        background-color: #e0f7ec;
                        color: #15803d;
                        padding: 4px 10px;
                        border-radius: 8px;
                        font-weight: 600;
                    }}
                    /* 📱 Responsive cho điện thoại */
                    @media (max-width: 600px) {{
                        .info-flex {{
                            flex-direction: column;
                            align-items: flex-start;
                        }}
                        .info-item {{
                            text-align: left;
                            width: 100%;
                            white-space: normal; /* Cho phép xuống dòng trên mobile */
                        }}
                    }}
                </style>

                <div class="info-wrapper">
                    <div class="info-card">
                        <h3 class="info-header"> Thông tin cá nhân</h3>
                        <div class="info-flex">
                            <div class="info-item"><b>👤 Họ và tên:</b> {selected_emp.get('full_name', '')}</div>
                            <div class="info-item"><b>🏢 Phòng ban:</b> {selected_emp.get('department', '')}</div>
                            <div class="info-item"><b>💼 Chức vụ:</b> {selected_emp.get('position', '')}</div>
                            <div class="info-item"><b>🎂 Ngày sinh:</b> {selected_emp.get('dob', '-')}</div>
                            <div class="info-item"><b>📞 SĐT:</b> {selected_emp.get('phone', '-')}</div>
                            <div class="info-item"><b>🏖️ Còn lại:</b> <span class="badge">{selected_emp.get('remaining_days', 0)}</span></div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # --- Lấy toàn bộ dữ liệu nghỉ phép ---
            all_leaves = list(LEAVES_COL.find())
            st.markdown("<br><br>", unsafe_allow_html=True)
            if not all_leaves:
                st.info("Chưa có dữ liệu nghỉ phép.")
            else:
                import pandas as pd
                import plotly.express as px

                df = pd.DataFrame(all_leaves)
                df["start_date"] = pd.to_datetime(
                    df["start_date"], errors="coerce")
                df["year_month"] = df["start_date"].dt.to_period(
                    "M").astype(str)

                # --- Tổng số ngày nghỉ theo phòng ban ---
                dept_summary = df.groupby("department")[
                    "duration"].sum().reset_index()
                fig1 = px.bar(dept_summary, x="department", y="duration",
                              title="🏢 Tổng số ngày nghỉ theo phòng ban",
                              text_auto=True)
                st.plotly_chart(fig1, use_container_width=True)

                # --- Biểu đồ trạng thái ---
                status_summary = df["status"].value_counts().reset_index()
                status_summary.columns = ["status", "count"]
                fig2 = px.pie(status_summary, names="status", values="count",
                              title="📊 Tỷ lệ trạng thái nghỉ phép", hole=0.4)
                st.plotly_chart(fig2, use_container_width=True)

                # --- Biểu đồ theo tháng ---
                monthly = df.groupby("year_month")[
                    "duration"].sum().reset_index()
                fig3 = px.line(monthly, x="year_month", y="duration",
                               markers=True, title="📅 Tổng ngày nghỉ theo tháng")
                st.plotly_chart(fig3, use_container_width=True)

                # --- Bảng chi tiết ---
                st.markdown("### 📋 Bảng chi tiết nghỉ phép")
                st.dataframe(df[["full_name", "department", "leave_type",
                                "start_date", "end_date", "duration", "status"]])
