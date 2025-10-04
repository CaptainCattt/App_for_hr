import streamlit as st
from datetime import date, timedelta
from functions import send_leave_request, view_leaves, approve_leave, reject_leave, status_badge, check_admin_login
from settings import EMPLOYEES_COL, LEAVES_COL
import time

# ===============================
# CẤU HÌNH CƠ BẢN
# ===============================
st.set_page_config(
    page_title="Hệ thống xin nghỉ - Lâm Media", layout="centered")
st.title("🏖️ HỆ THỐNG XIN NGHỈ PHÉP NỘI BỘ")

tab1, tab2 = st.tabs(["📝 Gửi yêu cầu nghỉ", "👩‍💼 Dành cho HR"])

# ===============================
# TAB 1: FORM XIN NGHỈ
# ===============================
with tab1:
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
    st.text_input("💼 Chức vụ", position, disabled=True)
    st.text_input("🏖️ Ngày phép còn lại", str(remaining_days), disabled=True)

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
    end_date = col3.date_input("Ngày kết thúc nghỉ", value=end_date_default)
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
with tab2:
    st.subheader("👩‍💼 Trang quản lý nghỉ phép")

    # --- Nếu HR chưa đăng nhập ---
    if "hr_logged_in" not in st.session_state:
        username = st.text_input("👤 Tên đăng nhập")
        password = st.text_input("🔒 Mật khẩu", type="password")

        if st.button("Đăng nhập"):
            if check_admin_login(username, password):
                st.session_state.hr_logged_in = True
                st.session_state.hr_username = username
                st.success("✅ Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("❌ Sai tài khoản hoặc mật khẩu!")
        st.stop()

    # --- Sau khi đăng nhập ---
    st.success(f"👋 Xin chào {st.session_state.hr_username}")

    if st.button("🚪 Đăng xuất"):
        st.session_state.clear()
        st.rerun()

    # --- Bộ lọc dữ liệu ---
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox("Lọc theo trạng thái", [
            "Tất cả", "pending", "approved", "rejected"])
        query_status = None if status_filter == "Tất cả" else status_filter
    with col2:
        search_name = st.text_input("Tìm theo tên nhân viên")

    leaves = view_leaves(query_status)

    if search_name:
        leaves = [l for l in leaves if search_name.lower() in l.get(
            "full_name", "").lower()]

    if not leaves:
        st.info("🕊️ Chưa có yêu cầu nghỉ nào.")
    else:
        for leave in leaves:
            with st.expander(f"📄 {leave.get('full_name', '')} | {leave.get('leave_case', '')}"):
                st.write(f"**Phòng ban:** {leave.get('department', '')}")
                st.write(
                    f"**Thời gian:** {leave.get('start_date')} → {leave.get('end_date')} ({leave.get('duration')} ngày)")
                st.write(f"**Loại nghỉ:** {leave.get('leave_type')}")
                st.write(f"**Lý do chi tiết:** {leave.get('reason', '')}")
                st.write(
                    f"**Trạng thái:** {status_badge(leave.get('status', ''))}")
                st.write(f"**Gửi lúc:** {leave.get('requested_at', '')}")

                if leave.get("approved_by"):
                    st.write(
                        f"**Phê duyệt bởi:** {leave.get('approved_by')} lúc {leave.get('approved_at')}")

                if leave.get("status") == "pending":
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("✅ Duyệt", key=f"approve_{leave['_id']}"):
                            approve_leave(
                                leave["_id"], st.session_state.hr_username)
                    with col_b:
                        if st.button("❌ Từ chối", key=f"reject_{leave['_id']}"):
                            reject_leave(
                                leave["_id"], st.session_state.hr_username)
