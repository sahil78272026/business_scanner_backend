import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

host =  os.getenv('DB_HOST')
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
database =  os.getenv("DB_NAME")
port = os.getenv("DB_PORT")

# DB_CONN = psycopg2.connect(
#     host=host,
#     database=database,
#     user=user,
#     password=password,
#     port=port
# )

# def get_cursor():
#     return DB_CONN.cursor(cursor_factory=RealDictCursor)



def get_cursor():
    try:
        print("Db Connection string", os.getenv("DATABASE_URL"))
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn.cursor(cursor_factory=RealDictCursor)

    except Exception as e:
        print("Database connection error:", e)
        raise

def get_db_connection():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        return conn

    except Exception as e:
        print("Database connection error:", e)
        raise