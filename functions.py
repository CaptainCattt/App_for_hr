# functions.py
from settings import USERS_COL, LEAVES_COL, SESSIONS_COL, COOKIES, STATUS_COLORS
from bson import ObjectId
from datetime import datetime, timedelta
import streamlit as st
import time
import uuid

# ---------- Auth / session helpers ----------


def get_current_user():
    """
    Trả về user từ cookie/session token nếu hợp lệ.
    Đồng thời ghi lại thông tin vào st.session_state để UI sử dụng.
    """
    token = COOKIES.get("session_token")
    if not token:
        return None

    session = SESSIONS_COL.find_one({"token": token})
    if not session:
        return None

    # Nếu expired => xóa session + cookie
    if session.get("expired_at") and session["expired_at"] < datetime.now():
        SESSIONS_COL.delete_one({"token": token})
        COOKIES["session_token"] = ""
        COOKIES.save()
        return None

    # Ghi vào session_state (giúp UI không yêu cầu đăng nhập lại sau reload)
    st.session_state["username"] = session["username"]
    st.session_state["role"] = session.get("role", "employee")

    # Điền thêm thông tin từ users collection nếu có
    user = USERS_COL.find_one({"username": session["username"]})
    if user:
        st.session_state["full_name"] = user.get("full_name", user["username"])
        st.session_state["position"] = user.get("position", "")
        st.session_state["department"] = user.get("department", "")
        st.session_state["remaining_days"] = user.get("remaining_days", 0)
    return {"username": session["username"], "role": session.get("role", "employee")}


def do_login(username, password):
    """
    Kiểm tra user/password, tạo session token, lưu cookie.
    Gọi do_login bằng partial từ app khi bấm nút Login.
    """
    placeholder = st.empty()
    with placeholder:
        st.info("🔑 Đang đăng nhập...")
    time.sleep(0.4)

    user = USERS_COL.find_one({"username": username, "password": password})
    if not user:
        placeholder.error("❌ Sai username hoặc password")
        time.sleep(1.5)
        placeholder.empty()
        return

    # tạo token & session
    token = str(uuid.uuid4())
    expired_at = datetime.now() + timedelta(hours=8)

    SESSIONS_COL.insert_one({
        "username": user["username"],
        "role": user.get("role", "employee"),
        "token": token,
        "expired_at": expired_at
    })

    # lưu cookie token (riêng cho trình duyệt)
    COOKIES["session_token"] = token
    COOKIES.save()

    # lưu session_state để UI dùng
    st.session_state["username"] = user["username"]
    st.session_state["role"] = user.get("role", "employee")
    st.session_state["full_name"] = user.get("full_name", user["username"])
    st.session_state["position"] = user.get("position", "")
    st.session_state["department"] = user.get("department", "")
    st.session_state["remaining_days"] = user.get("remaining_days", 0)

    placeholder.success(
        f"✅ Đăng nhập thành công! Chào {st.session_state['full_name']}")
    time.sleep(1.2)
    placeholder.empty()

    # yêu cầu app rerun để cập nhật UI
    st.session_state["rerun_needed"] = True


def logout():
    placeholder = st.empty()
    with placeholder:
        st.info("🚪 Đang đăng xuất...")
    time.sleep(0.4)

    token = COOKIES.get("session_token")
    if token:
        SESSIONS_COL.delete_one({"token": token})

    # clear local state & cookie
    st.session_state.clear()
    COOKIES["session_token"] = ""
    COOKIES.save()

    placeholder.success("✅ Bạn đã đăng xuất thành công!")
    time.sleep(1.2)
    placeholder.empty()
    st.session_state["rerun_needed"] = True


# ---------- Leave related ----------

def status_badge(status: str):
    return STATUS_COLORS.get(status, status)


def request_leave(username, start_date, end_date, duration, reason, leave_type, leave_case):
    # ensure date string
    if not isinstance(start_date, str):
        start_date = start_date.strftime("%Y-%m-%d")
    if not isinstance(end_date, str):
        end_date = end_date.strftime("%Y-%m-%d")

    LEAVES_COL.insert_one({
        "username": username,
        "start_date": start_date,
        "end_date": end_date,
        "duration": duration,
        "reason": reason,
        "leave_type": leave_type,
        "leave_case": leave_case,
        "status": "pending",
        "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "approved_by": None,
        "approved_at": None
    })


def view_leaves(username=None):
    if username:
        return list(LEAVES_COL.find({"username": username}))
    return list(LEAVES_COL.find())


def send_leave_request(username, start_date, end_date, duration, reason, leave_type, leave_case):
    """
    Gọi khi user bấm gửi. Khóa nút ngay lập tức bằng session_state trước khi insert.
    """
    st.session_state["leave_btn_disabled"] = True
    st.session_state["last_leave_request"] = time.time()

    # Insert trực tiếp (không sleep lớn)
    request_leave(username, start_date, end_date,
                  duration, reason, leave_type, leave_case)

    # hiển thị success flash ngắn
    placeholder = st.empty()
    placeholder.success("📤 Yêu cầu đã gửi!")
    time.sleep(1.5)
    placeholder.empty()
    # cho UI cập nhật (không bắt buộc)
    st.session_state["rerun_needed"] = True


def approve_leave(l_id, user_name):
    """
    Approve: cập nhật status + approved_by/approved_at + trừ remaining_days nếu phù hợp.
    Hàm này gọi từ UI của admin. Khóa UI bên app bằng rerun flag + hiển thị flash.
    """
    placeholder = st.empty()
    with placeholder:
        st.info("✅ Đang duyệt...")
    time.sleep(0.4)

    leave = LEAVES_COL.find_one({"_id": ObjectId(l_id)})
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    LEAVES_COL.update_one({"_id": ObjectId(l_id)}, {"$set": {
        "status": "approved",
        "approved_by": st.session_state.get("full_name", "Admin"),
        "approved_at": now_str
    }})

    if leave and leave.get("leave_type") == "Nghỉ phép năm":
        duration = float(leave.get("duration", 1))
        USERS_COL.update_one({"username": user_name}, {
                             "$inc": {"remaining_days": -duration}})

    placeholder.success(
        f"✅ Yêu cầu của {user_name} đã được duyệt lúc {now_str}!")
    time.sleep(1.2)
    placeholder.empty()
    # set message to show on next render
    st.session_state["leave_message"] = f"Yêu cầu của {user_name} đã được duyệt."
    st.session_state["rerun_needed"] = True


def reject_leave(l_id, user_name):
    placeholder = st.empty()
    with placeholder:
        st.info("❌ Đang từ chối...")
    time.sleep(0.4)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    LEAVES_COL.update_one({"_id": ObjectId(l_id)}, {"$set": {
        "status": "rejected",
        "approved_by": st.session_state.get("full_name", "Admin"),
        "approved_at": now_str
    }})

    placeholder.error(
        f"❌ Yêu cầu của {user_name} đã bị từ chối lúc {now_str}!")
    time.sleep(1.2)
    placeholder.empty()
    st.session_state["leave_message"] = f"Yêu cầu của {user_name} đã bị từ chối."
    st.session_state["rerun_needed"] = True
