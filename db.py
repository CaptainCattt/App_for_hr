# db.py
import streamlit as st
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")


def get_connection():
    db_url = st.secrets["DATABASE_URL"]

    return psycopg2.connect(db_url, connect_timeout=10)
