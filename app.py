import streamlit as st
import psycopg2
from db import get_connection

# ------------------ DB Functions -------------------


def login(username, password):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, role FROM users WHERE username=%s AND password=%s", (username, password))
            return cur.fetchone()


def create_leave_request(user_id, start_date, end_date, reason):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO leave_requests (user_id, start_date, end_date, reason) VALUES (%s, %s, %s, %s)",
                (user_id, start_date, end_date, reason)
            )
        conn.commit()


def get_leave_requests():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT lr.id, u.username, lr.start_date, lr.end_date, lr.reason, lr.status
                FROM leave_requests lr
                JOIN users u ON lr.user_id = u.id
                ORDER BY lr.id DESC
            """)
            return cur.fetchall()


def update_leave_request(request_id, status):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE leave_requests SET status=%s WHERE id=%s", (status, request_id))
        conn.commit()


def get_summary():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.username, DATE_TRUNC('month', lr.start_date) AS month, COUNT(*) AS total_days
                FROM leave_requests lr
                JOIN users u ON lr.user_id = u.id
                WHERE lr.status = 'approved'
                GROUP BY u.username, DATE_TRUNC('month', lr.start_date)
                ORDER BY month DESC
            """)
            return cur.fetchall()


# ------------------ Streamlit UI -------------------
st.title("🚀 Leave Management System")

# 🔍 Debug check secrets
if "DATABASE_URL" not in st.secrets:
    st.error("DATABASE_URL is missing in Streamlit Secrets!")
else:
    st.write("✅ DATABASE_URL loaded, starts with:",
             st.secrets["DATABASE_URL"][:30])


def get_connection():
    db_url = st.secrets["DATABASE_URL"]
    return psycopg2.connect(db_url, connect_timeout=10)

# phần code app tiếp tục bên dưới...


# Login
if "user" not in st.session_state:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login(username, password)
        if user:
            st.session_state.user = {
                "id": user[0], "username": user[1], "role": user[2]}
            st.success(f"Welcome {user[1]} ({user[2]})")
        else:
            st.error("Invalid credentials")

else:
    user = st.session_state.user
    st.sidebar.write(f"👤 {user['username']} ({user['role']})")
    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.experimental_rerun()

    # Employee View
    if user["role"] == "employee":
        st.header("📅 Submit Leave Request")
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        reason = st.text_area("Reason")
        if st.button("Submit Request"):
            create_leave_request(user["id"], start_date, end_date, reason)
            st.success("Request submitted!")

    # HR/Admin View
    elif user["role"] == "hr":
        st.header("📋 Manage Leave Requests")
        requests = get_leave_requests()
        for r in requests:
            st.write(
                f"ID {r[0]} | {r[1]} | {r[2]} → {r[3]} | Reason: {r[4]} | Status: {r[5]}")
            if r[5] == "pending":
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Approve", key=f"approve_{r[0]}"):
                        update_leave_request(r[0], "approved")
                        st.experimental_rerun()
                with col2:
                    if st.button("Reject", key=f"reject_{r[0]}"):
                        update_leave_request(r[0], "rejected")
                        st.experimental_rerun()

        st.header("📊 Dashboard")
        summary = get_summary()
        st.write("### Leave Summary")
        for s in summary:
            st.write(f"{s[0]} | {s[1].strftime('%Y-%m')} | {s[2]} days")
