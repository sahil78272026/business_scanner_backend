import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_CONN = psycopg2.connect(
    host="localhost",
    database="business_scanner",
    user="postgres",
    password=os.getenv("POSTGRES_PASSWORD")
)

def get_cursor():
    return DB_CONN.cursor(cursor_factory=RealDictCursor)