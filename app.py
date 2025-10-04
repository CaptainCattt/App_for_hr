import streamlit as st
from datetime import date, timedelta
import time
from functions import send_leave_request, view_leaves, update_leave_status, check_admin_login

st.set_page_config(page_title="HR Leave App",
                   page_icon="🗓️", layout="centered")

st.title("🏖️ Hệ thống xin nghỉ nội bộ")

tab1, tab2 = st.tabs(["📨 Gửi yêu cầu nghỉ", "🧑‍💼 Quản lý HR"])

# ==========================
#  TAB 1 – FORM XIN NGHỈ
# ==========================
with tab1:
    st.subheader("📝 Gửi yêu cầu nghỉ")

    username = st.text_input("👤 Họ và tên của bạn")
    if not username:
        st.info("👉 Nhập tên để tiếp tục gửi yêu cầu nghỉ")
    else:
        leave_type = st.selectbox(
            "Vui lòng chọn loại ngày nghỉ",
            (
                "Nghỉ phép năm",
                "Nghỉ không hưởng lương",
                "Nghỉ hưởng BHXH",
                "Nghỉ việc riêng có hưởng lương",
            ),
            index=0
        )

        leave_case = ""
        if leave_type == "Nghỉ phép năm":
            leave_case = st.selectbox("Loại phép năm", ["Phép năm"])
        elif leave_type == "Nghỉ không hưởng lương":
            leave_case = st.selectbox(
                "Lý do nghỉ không hưởng lương",
                ["Do hết phép năm", "Do việc cá nhân thời gian dài"]
            )
        elif leave_type == "Nghỉ hưởng BHXH":
            leave_case = st.selectbox(
                "Lý do nghỉ hưởng BHXH",
                [
                    "Bản thân ốm", "Con ốm", "Bản thân ốm dài ngày",
                    "Chế độ thai sản cho nữ", "Chế độ thai sản cho nam",
                    "Dưỡng sức (sau phẫu thuật, sau sinh, sau ốm, ...)",
                    "Suy giảm khả năng lao động (15% - trên 51%)"
                ]
            )
        elif leave_type == "Nghỉ việc riêng có hưởng lương":
            leave_case = st.selectbox(
                "Lý do nghỉ việc riêng có hưởng lương",
                ["Bản thân kết hôn", "Con kết hôn",
                    "Tang chế tư thân phụ mẫu (Bố/mẹ - vợ/chồng, con chết)"]
            )

        col1, col2, col3 = st.columns(3)
        duration = col1.number_input(
            "Số ngày nghỉ", min_value=0.5, max_value=30.0, step=0.5, value=1.0
        )
        start_date = col2.date_input("Ngày bắt đầu nghỉ", value=date.today())
        end_date_default = start_date + timedelta(days=int(duration) - 1)
        end_date = col3.date_input(
            "Ngày kết thúc nghỉ", value=end_date_default)

        reason_text = st.text_area("📝 Lý do chi tiết", height=100)

        # Cooldown logic
        if "leave_btn_disabled" not in st.session_state:
            st.session_state["leave_btn_disabled"] = False
        if "last_leave_request" not in st.session_state:
            st.session_state["last_leave_request"] = 0

        cooldown = 60
        now_ts = time.time()
        last_sent = st.session_state.get("last_leave_request", 0)
        remaining = max(0, int(cooldown - (now_ts - last_sent)))

        if remaining <= 0:
            st.session_state["leave_btn_disabled"] = False

        if st.button("📨 Gửi yêu cầu", disabled=st.session_state["leave_btn_disabled"]):
            if st.session_state["leave_btn_disabled"]:
                st.warning(
                    f"⏳ Vui lòng đợi {remaining} giây trước khi gửi yêu cầu tiếp theo.")
            elif not reason_text.strip():
                st.warning("⚠️ Vui lòng nhập lý do nghỉ")
            else:
                st.session_state["leave_btn_disabled"] = True
                st.session_state["last_leave_request"] = now_ts
                send_leave_request(username, start_date, end_date,
                                   duration, reason_text, leave_type, leave_case)
                st.markdown("<br>" * 10, unsafe_allow_html=True)


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

    # Nếu đã đăng nhập HR
    leaves = view_leaves()
    if not leaves:
        st.info("📭 Chưa có yêu cầu nghỉ nào.")
    else:
        for leave in leaves:
            with st.container(border=True):
                st.markdown(
                    f"**👤 {leave['username']}**  |  🏷️ {leave['leave_type']} - {leave['leave_case']}  \n"
                    f"📅 {leave['start_date']} → {leave['end_date']} ({leave['duration']} ngày)\n\n"
                    f"📝 {leave['reason']}\n\n"
                    f"**Trạng thái:** {leave['status']}"
                )
                colA, colB, colC = st.columns(3)
                if colA.button("✅ Duyệt", key=f"approve_{leave['leave_id']}"):
                    update_leave_status(leave["leave_id"], "Đã duyệt")
                if colB.button("❌ Từ chối", key=f"reject_{leave['leave_id']}"):
                    update_leave_status(leave["leave_id"], "Từ chối")
                if colC.button("🗑️ Xóa", key=f"delete_{leave['leave_id']}"):
                    from settings import LEAVES_COL
                    LEAVES_COL.delete_one({"leave_id": leave["leave_id"]})
                    st.warning("🗑️ Đã xóa yêu cầu này.")
