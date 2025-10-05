# settings.py
import streamlit as st
from pymongo import MongoClient

# --- MongoDB Config ---


@st.cache_resource
def get_mongo_client():
    """Kết nối MongoDB (chỉ tạo 1 lần, dùng lại giữa các lần rerun)"""
    return MongoClient(st.secrets["MONGO_URL"])


client = get_mongo_client()
db = client["leave_management"]

# --- Collections ---
USERS_COL = db["users"]
LEAVES_COL = db["leaves"]
EMPLOYEES_COL = db["employees"]

# --- Constants ---
STATUS_COLORS = {
    "pending": "🟡 Chờ duyệt",
    "approved": "🟢 Đã duyệt",
    "rejected": "🔴 Từ chối"
}
