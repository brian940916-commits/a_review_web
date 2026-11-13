"""以獨立的暫存 schema 測試，不清空專題資料表。"""
import os
import asyncio
import re
import uuid
import secrets
from pathlib import Path
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from security import hash_password

load_dotenv()
TEST_PASSWORD = secrets.token_urlsafe(24)


@pytest.fixture
def client(monkeypatch):
    original = os.environ["DATABASE_URL"]
    schema = "test_" + uuid.uuid4().hex
    with psycopg.connect(original, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    test_url = make_conninfo(original, options=f"-c search_path={schema}")
    monkeypatch.setenv("DATABASE_URL", test_url)
    try:
        with psycopg.connect(test_url) as conn:
            conn.execute(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
            for name, role in [("author", "author"), ("author2", "author"), ("editor", "editor")]:
                conn.execute("INSERT INTO users(username,password_hash,role) VALUES(%s,%s,%s)", (name, hash_password(TEST_PASSWORD), role))
        from main import app
        with TestClient(app, backend_options={"loop_factory": asyncio.SelectorEventLoop}) as browser:
            yield browser
    finally:
        with psycopg.connect(original, autocommit=True) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def token(client, path="/"):
    return re.search(r'name="csrf" value="([^"]+)"', client.get(path).text).group(1)


def login(client, username):
    client.cookies.clear()
    response = client.post("/login", data={"username": username, "password": TEST_PASSWORD, "csrf": token(client, "/login")})
    assert response.status_code == 200


def post(client, path, **fields):
    return client.post(path, data={"csrf": token(client), **fields})


def test_full_review_workflow(client):
    assert client.get("/").url.path == "/login"
    login(client, "author")
    assert "還沒有投稿" in client.get("/").text
    assert post(client, "/article/add", category="科技", title="第一篇", content="文章內容").status_code == 200
    assert "編輯中" in client.get("/").text
    assert post(client, "/article/1/edit", category="生活", title="已修改", content="<script>alert(1)</script>").status_code == 200
    assert "&lt;script&gt;" in client.get("/article/1").text
    assert post(client, "/article/1/submit").status_code == 200
    assert "審查中" in client.get("/").text
    assert post(client, "/article/1/delete").status_code == 403
    assert post(client, "/article/1/edit", category="生活", title="不允許", content="test").status_code == 403
    assert post(client, "/article/1/review", decision="approve").status_code == 403
    login(client, "author2")
    assert client.get("/article/1").status_code == 403
    assert post(client, "/article/1/submit").status_code == 403
    login(client, "editor")
    assert "已修改" in client.get("/").text
    assert post(client, "/article/add", category="x", title="x", content="x").status_code == 403
    assert post(client, "/article/1/review", decision="invalid").status_code == 400
    assert post(client, "/article/1/review", decision="return").status_code == 200
    login(client, "author")
    assert client.get("/article/1/edit").status_code == 200
    assert post(client, "/article/1/submit").status_code == 200
    login(client, "editor")
    assert post(client, "/article/1/review", decision="approve").status_code == 200
    assert post(client, "/article/1/review", decision="return").status_code == 409
    login(client, "author")
    assert "已通過" in client.get("/").text
    assert post(client, "/article/1/delete").status_code == 403
    assert post(client, "/article/add", category="測試", title="刪除測試", content="內容").status_code == 200
    assert post(client, "/article/2/delete").status_code == 200
    assert client.get("/article/2").status_code == 404
    assert post(client, "/logout").url.path == "/login"


def test_validation_and_auth(client):
    assert client.get("/article/add").status_code == 401
    response = client.post("/login", data={"username": "author", "password": "wrong", "csrf": token(client, "/login")})
    assert "帳號或密碼錯誤" in response.text
    login(client, "author")
    assert client.post("/article/add", data={"category": "x", "title": "x", "content": "x", "csrf": "bad"}).status_code == 403
    assert post(client, "/article/add", category=" ", title="x", content="x").status_code == 400
    assert post(client, "/article/add", category="x", title="x" * 151, content="x").status_code == 400
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/script.js").status_code == 200
