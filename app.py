import streamlit as st
import psycopg2
import pandas as pd
import bcrypt
from db import get_connection

st.set_page_config(page_title="Leave Management App", layout="wide")

# ---- Login ----


def login(username, password):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, password, role FROM users WHERE username=%s", (username,))
            user = cur.fetchone()
            if user and bcrypt.checkpw(password.encode(), user[1].encode()):
                return {"id": user[0], "role": user[2]}
    return None

# ---- Create leave request ----


def create_leave_request(user_id, start_date, end_date, reason):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO leave_requests (user_id, start_date, end_date, reason)
                VALUES (%s, %s, %s, %s)
            """, (user_id, start_date, end_date, reason))
        conn.commit()

# ---- Admin update status ----


def update_request_status(req_id, status):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE leave_requests SET status=%s WHERE id=%s", (status, req_id))
        conn.commit()

# ---- Dashboard ----


def get_dashboard():
    with get_connection() as conn:
        df = pd.read_sql("""
            SELECT u.username, 
                   COUNT(lr.id) FILTER (WHERE lr.status='approved') AS approved_leaves
            FROM users u
            LEFT JOIN leave_requests lr ON u.id = lr.user_id
            GROUP BY u.username
        """, conn)
    return df


# ---- UI ----
st.title("🚀 Leave Management System")

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Logged in as {username} ({user['role']})")
        else:
            st.error("Invalid credentials")
else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as {user['role']}")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.experimental_rerun()

    # Employee view
    if user["role"] == "employee":
        st.subheader("Tạo yêu cầu nghỉ")
        start_date = st.date_input("Ngày bắt đầu")
        end_date = st.date_input("Ngày kết thúc")
        reason = st.text_area("Lý do")
        if st.button("Gửi yêu cầu"):
            create_leave_request(user["id"], start_date, end_date, reason)
            st.success("Đã gửi yêu cầu nghỉ")

    # Admin view
    elif user["role"] == "admin":
        st.subheader("Duyệt yêu cầu nghỉ")
        with get_connection() as conn:
            df = pd.read_sql(
                "SELECT lr.id, u.username, lr.start_date, lr.end_date, lr.reason, lr.status FROM leave_requests lr JOIN users u ON lr.user_id=u.id", conn)
        st.dataframe(df)
        req_id = st.number_input("ID yêu cầu cần duyệt", min_value=1, step=1)
        action = st.selectbox("Trạng thái", ["approved", "rejected"])
        if st.button("Cập nhật"):
            update_request_status(req_id, action)
            st.success("Đã cập nhật yêu cầu")

        st.subheader("📊 Dashboard nghỉ phép")
        dash = get_dashboard()
        st.bar_chart(dash.set_index("username")["approved_leaves"])
