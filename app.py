import streamlit as st
from datetime import date, timedelta
from functions import send_leave_request, view_leaves, approve_leave, reject_leave, status_badge, check_admin_login
from settings import EMPLOYEES_COL, LEAVES_COL
from datetime import datetime

# ===============================
# CẤU HÌNH CƠ BẢN
# ===============================
st.set_page_config(
    page_title="Hệ thống xin nghỉ - Lâm Media", layout="centered")
st.title("🏖️ HỆ THỐNG XIN NGHỈ PHÉP NỘI BỘ")


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


tabs = ["📝 Gửi yêu cầu nghỉ"]
if "hr_logged_in" in st.session_state and st.session_state.hr_logged_in:
    tabs.extend(["👩‍💼 Quản lý yêu cầu", "📊 Dashboard nhân viên"])

tab_objects = st.tabs(tabs)

# ===============================
# TAB 1: FORM XIN NGHỈ
# ===============================
with tab_objects[0]:
    st.subheader("📝 Gửi yêu cầu nghỉ")

    # --- Lấy danh sách nhân viên ---
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

    # --- Chọn loại nghỉ ---
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
    end_date = col3.date_input(
        "Ngày kết thúc nghỉ", value=end_date_default)
    reason_text = st.text_area("📝 Lý do chi tiết", height=100)

    # --- Gửi yêu cầu ---
    if st.button("📨 Gửi yêu cầu"):
        if not reason_text.strip():
            st.warning("⚠️ Vui lòng nhập lý do nghỉ.")
        else:
            send_leave_request(selected_name, department, start_date,
                               end_date, duration, reason_text, leave_type, leave_case)

    # ===============================
    # TAB 2: HR QUẢN LÝ
    # ===============================
    if len(tabs) > 1:
        with tab_objects[1]:
            st.subheader("👩‍💼 Trang quản lý nghỉ phép")

            # --- Bộ lọc dữ liệu ---
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                search_name = st.text_input("Tìm theo tên nhân viên")
            with col2:
                status_filter = st.selectbox(
                    "Trạng thái", ["Tất cả", "pending", "approved", "rejected"])
                query_status = None if status_filter == "Tất cả" else status_filter
            with col3:
                year_options = [
                    "Tất cả"] + [str(y) for y in range(2024, datetime.now().year + 1)]
                selected_year = st.selectbox(
                    "Năm", options=year_options, index=year_options.index(str(datetime.now().year)))
            with col4:
                month_options = ["Tất cả"] + [f"{i:02d}" for i in range(1, 13)]
                selected_month = st.selectbox(
                    "Tháng", options=month_options, index=datetime.now().month)

            # --- Lấy dữ liệu từ DB ---
            leaves = view_leaves(query_status)

            # --- Lọc theo tên ---
            if search_name:
                leaves = [l for l in leaves if search_name.lower() in l.get(
                    "full_name", "").lower()]

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

            # --- Hiển thị kết quả ---
            if not filtered_leaves:
                st.info(
                    f"🕊️ Không có yêu cầu nghỉ nào trong {selected_month}/{selected_year}.")
            else:
                for leave in filtered_leaves:
                    with st.expander(f"📄 {leave.get('full_name', '')} | {leave.get('leave_case', '')}"):
                        st.write(
                            f"**Phòng ban:** {leave.get('department', '')}")
                        st.write(
                            f"**Thời gian:** {leave.get('start_date')} → {leave.get('end_date')} ({leave.get('duration')} ngày)"
                        )
                        st.write(f"**Loại nghỉ:** {leave.get('leave_type')}")
                        st.write(
                            f"**Lý do chi tiết:** {leave.get('reason', '')}")
                        st.write(
                            f"**Trạng thái:** {status_badge(leave.get('status', ''))}")
                        st.write(
                            f"**Gửi lúc:** {leave.get('requested_at', '')}")
                        st.markdown("<br>", unsafe_allow_html=True)

                        if leave.get("approved_by"):
                            st.write(
                                f"**Phê duyệt bởi:** {leave.get('approved_by')} lúc {leave.get('approved_at')}")

                        if leave.get("status") == "pending":
                            col_left, col_spacer, col_right = st.columns([
                                                                         1, 4, 1])

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
            st.subheader("📊 Dashboard tổng hợp nghỉ phép")

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
                        width: 85%;
                        max-width: 900px;
                        transition: all 0.3s ease;
                        font-family: "Segoe UI", sans-serif;
                    }}
                    .info-card:hover {{
                        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
                    }}
                    .info-header {{
                        font-size: 1.3rem;
                        font-weight: 600;
                        color: #2c3e50;
                        margin-bottom: 15px;
                        padding-left: 10px;
                        text-align: center;
                    }}
                    .info-flex {{
                        display: flex;
                        flex-wrap: wrap;
                        justify-content: center;
                        gap: 40px;
                    }}
                    .info-col {{
                        flex: 1;
                        min-width: 250px;
                        line-height: 1.8;
                        color: #333;
                    }}
                    .badge {{
                        background-color: #e0f7ec;
                        color: #15803d;
                        padding: 4px 10px;
                        border-radius: 8px;
                        font-weight: 600;
                    }}
                </style>

                <div class="info-wrapper">
                    <div class="info-card">
                        <h3 class="info-header">🧾 Thông tin cá nhân</h3>
                        <div class="info-flex">
                            <div class="info-col">
                                <p><b>👤 Họ và tên:</b> {selected_emp.get('full_name', '')}</p>
                                <p><b>🏢 Phòng ban:</b> {selected_emp.get('department', '')}</p>
                                <p><b>💼 Chức vụ:</b> {selected_emp.get('position', '')}</p>
                            </div>
                            <div class="info-col">
                                <p><b>🎂 Ngày sinh:</b> {selected_emp.get('dob', '-')}</p>
                                <p><b>📞 Số điện thoại:</b> {selected_emp.get('phone', '-')}</p>
                                <p><b>🏖️ Ngày phép còn lại:</b> <span class="badge">{selected_emp.get('remaining_days', 0)}</span></p>
                            </div>
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
