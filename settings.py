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
EMPLOYEES_COL = db["employees"]

# --- Constants ---
STATUS_COLORS = {
    "pending": "🟡 Chờ duyệt",
    "approved": "🟢 Đã duyệt",
    "rejected": "🔴 Từ chối"
}
