import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv(
    "postgresql://postgres.pydslnyczzkuepitdgbq:[luuquangtienHoang2007@]@aws-1-us-east-2.pooler.supabase.com:5432/postgres")


def get_connection():
    return psycopg2.connect(DB_URL)


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            with open("schema.sql", "r") as f:
                cur.execute(f.read())
        conn.commit()
