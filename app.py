import streamlit as st
from datetime import date, timedelta
import time
from functions import send_leave_request, view_leaves, approve_leave, reject_leave, check_admin_login, status_badge
from settings import EMPLOYEES_COL, LEAVES_COL, USERS_COL

st.set_page_config(page_title="HR Leave Form",
                   page_icon="🏖️", layout="centered")

st.title("🏖️ Hệ thống xin nghỉ nội bộ")

tab1, tab2 = st.tabs(["📨 Gửi yêu cầu nghỉ", "🧑‍💼 Quản lý HR"])

# ==========================
#  TAB 1 – FORM XIN NGHỈ
# ==========================
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

# ==========================
#  TAB 2 – QUẢN LÝ HR
# ==========================
with tab2:
    st.subheader("🧑‍💼 Khu vực HR")

    if not st.session_state.get("is_admin", False):
        pwd = st.text_input("🔐 Nhập mật khẩu HR", type="password")
        if st.button("Đăng nhập"):
            check_admin_login(pwd)
        st.stop()

    # --- Nếu đã đăng nhập HR ---
    st.markdown("### 📋 Danh sách yêu cầu nghỉ")

    status_filter = st.selectbox("Lọc theo trạng thái", [
                                 "Tất cả", "pending", "approved", "rejected"], index=0)
    leaves = view_leaves(None if status_filter == "Tất cả" else status_filter)

    if not leaves:
        st.info("📭 Chưa có yêu cầu nghỉ nào.")
    else:
        for leave in leaves:
            with st.expander(f"👤 {leave['full_name']} | 🏢 {leave['department']} | {status_badge(leave['status'])}"):
                st.markdown(
                    f"- **Loại nghỉ:** {leave['leave_type']} ({leave['leave_case']})\n"
                    f"- **Thời gian:** {leave['start_date']} → {leave['end_date']} ({leave['duration']} ngày)\n"
                    f"- **Lý do:** {leave['reason']}\n"
                    f"- **Gửi lúc:** {leave['requested_at']}\n"
                )
                if leave.get("approved_by"):
                    st.markdown(
                        f"✅ Duyệt bởi **{leave['approved_by']}** lúc {leave.get('approved_at')}")

                col1, col2 = st.columns(2)
                if col1.button("✅ Duyệt", key=f"approve_{leave['_id']}"):
                    approve_leave(leave["_id"], st.session_state["admin_name"])
                if col2.button("❌ Từ chối", key=f"reject_{leave['_id']}"):
                    reject_leave(leave["_id"], st.session_state["admin_name"])
