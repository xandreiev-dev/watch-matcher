import os
from dotenv import load_dotenv
import pymysql

load_dotenv()


def get_db_connection():
    return pymysql.connect(
        host=os.getenv("SQL_HOSTNAME", "localhost"),
        port=int(os.getenv("SQL_PORT", 3306)),
        user=os.getenv("SQL_USERNAME"),
        password=os.getenv("SQL_PASSWORD"),
        database=os.getenv("SQL_DATABASE"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )