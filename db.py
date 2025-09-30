# db.py
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")


def get_connection():
    if not DB_URL:
        raise RuntimeError(
            "DATABASE_URL not set. Check .env or environment secrets.")
    # Optional: tăng timeout hoặc set sslmode nếu Supabase yêu cầu
    return psycopg2.connect(DB_URL, connect_timeout=10)
