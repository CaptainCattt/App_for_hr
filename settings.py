# settings.py
import streamlit as st
from pymongo import MongoClient
from streamlit_cookies_manager import EncryptedCookieManager

# --- MongoDB Config ---
MONGO_URL = st.secrets["MONGO_URL"]
DB_NAME = "leave_management"

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Collections
USERS_COL = db["users"]
LEAVES_COL = db["leaves"]

# --- Cookie Config ---
COOKIES = EncryptedCookieManager(
    prefix="leave_mgmt",
    password=st.secrets["COOKIE_PASSWORD"],
)
if not COOKIES.ready():
    st.stop()

# --- Constants ---
STATUS_COLORS = {
    "pending": "🟡 Chờ duyệt",
    "approved": "🟢 Đã duyệt",
    "rejected": "🔴 Từ chối"
}
