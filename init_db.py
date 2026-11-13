"""建立資料表與課堂示範帳號，不刪除既有資料。"""
import os
import sys
from getpass import getpass
from pathlib import Path
import psycopg
from dotenv import load_dotenv
from security import hash_password

load_dotenv()

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    password = getpass("Set demo account password (8+ characters): ")
    if len(password) < 8:
        raise SystemExit("Password must have at least 8 characters.")
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
        for username, role in [("author", "author"), ("author2", "author"), ("editor", "editor")]:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) ON CONFLICT (username) DO NOTHING",
                (username, hash_password(password), role),
            )
    print("資料表已建立。示範帳號 author、author2、editor，新帳號密碼為剛才輸入的值。")
