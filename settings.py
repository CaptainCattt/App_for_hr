# settings.py
import uuid
import streamlit as st
from pymongo import MongoClient
from streamlit_cookies_manager import EncryptedCookieManager
import os

# --- MongoDB Config ---
MONGO_URL = st.secrets["MONGO_URL"]
DB_NAME = "leave_management"
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# --- Collections ---
USERS_COL = db["users"]
LEAVES_COL = db["leaves"]
# Lưu sessions trong mảng "sessions" của user, không dùng collection riêng

# --- Cookie Config ---
cookie_key = "leave_mgmt_session"  # cố định, không random
COOKIES = EncryptedCookieManager(
    prefix=cookie_key, password=st.secrets["COOKIE_PASSWORD"])
if not COOKIES.ready():
    st.stop()

# --- JWT Secret ---
JWT_SECRET = st.secrets.get("JWT_SECRET", os.environ.get(
    "JWT_SECRET", "dev_secret_change_me"))

# --- Constants ---
STATUS_COLORS = {
    "pending": "🟡 Chờ duyệt",
    "approved": "🟢 Đã duyệt",
    "rejected": "🔴 Từ chối"
}
