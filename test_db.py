# test_db.py
import os
from dotenv import load_dotenv
import psycopg2
import pandas as pd

load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
print("Using DB_URL:", DB_URL[:80] + "..." if DB_URL else "None")

try:
    conn = psycopg2.connect(DB_URL, connect_timeout=10)
    print("✅ Connected to DB")
    df = pd.read_sql(
        "SELECT u.id,u.username,lr.id as request_id, lr.start_date, lr.end_date, lr.status FROM users u LEFT JOIN leave_requests lr ON u.id=lr.user_id LIMIT 10", conn)
    print(df)
    conn.close()
except Exception as e:
    print("❌ Connection failed:", e)
