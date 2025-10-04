import streamlit as st
from datetime import date
from functions import send_leave_request, view_leaves, approve_leave, reject_leave, status_badge, check_hr_login

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
    st.subheader("📩 Gửi yêu cầu nghỉ phép")

    full_name = st.text_input("👤 Họ và tên")
    department = st.text_input("🏢 Phòng ban")
    leave_type = st.selectbox(
        "📂 Loại nghỉ", ["Nghỉ phép năm", "Nghỉ việc riêng", "Nghỉ bệnh", "Khác"])
    leave_case = st.text_input(
        "🗒️ Nội dung nghỉ (ví dụ: về quê, khám bệnh, ...)")
    start_date = st.date_input("📅 Ngày bắt đầu", min_value=date.today())
    end_date = st.date_input("📅 Ngày kết thúc", min_value=start_date)
    duration = (end_date - start_date).days + 1
    reason = st.text_area("✏️ Ghi chú / Lý do chi tiết")

    if st.button("📤 Gửi yêu cầu"):
        if not full_name or not department or not leave_case:
            st.warning("⚠️ Vui lòng điền đầy đủ thông tin trước khi gửi!")
        else:
            send_leave_request(full_name, department, start_date,
                               end_date, duration, reason, leave_type, leave_case)

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
            if check_hr_login(username, password):
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
