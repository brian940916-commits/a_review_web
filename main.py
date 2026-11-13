import os
import secrets
from pathlib import Path
from fastapi import FastAPI, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from db import getDB, lifespan
from security import check_password

BASE = Path(__file__).resolve().parent
app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.environ["SESSION_SECRET"], same_site="lax")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")


def page(request, name, **data):
    if "csrf" not in request.session:
        request.session["csrf"] = secrets.token_hex(32)
    return templates.TemplateResponse(request=request, name=name, context=data)


def go_home():
    return RedirectResponse("/", status_code=303)


def require_user(request, role=None):
    user = request.session.get("user")
    if not user:
        raise HTTPException(401, "請先登入")
    if role and user["role"] != role:
        raise HTTPException(403, "沒有操作權限")
    return user


def check_csrf(request, token):
    if not secrets.compare_digest(request.session.get("csrf", ""), token) or not token:
        raise HTTPException(403, "表單已失效，請重新整理頁面")


def check_fields(category, title, content):
    if not category.strip() or not title.strip() or not content.strip():
        raise HTTPException(400, "類別、標題、內容不可空白")
    if len(category) > 50 or len(title) > 150 or len(content) > 20000:
        raise HTTPException(400, "類別最多 50 字、標題 150 字、內容 20000 字")


@app.get("/login")
async def login_page(request: Request):
    return page(request, "login.html")


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), csrf: str = Form(...), db=Depends(getDB)):
    check_csrf(request, csrf)
    cur = await db.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = await cur.fetchone()
    if not user or not check_password(password, user["password_hash"]):
        return page(request, "login.html", error="帳號或密碼錯誤")
    request.session.clear()
    request.session["user"] = {"id": user["id"], "username": user["username"], "role": user["role"]}
    return go_home()


@app.post("/logout")
async def logout(request: Request, csrf: str = Form(...)):
    check_csrf(request, csrf)
    request.session.clear()
    return go_home()


@app.get("/")
async def home(request: Request, db=Depends(getDB)):
    if not request.session.get("user"):
        return RedirectResponse("/login", status_code=303)
    user = require_user(request)
    if user["role"] == "author":
        cur = await db.execute("SELECT * FROM articles WHERE author_id=%s ORDER BY id DESC", (user["id"],))
    else:
        cur = await db.execute("SELECT a.*, u.username FROM articles a JOIN users u ON a.author_id=u.id WHERE a.status='審查中' ORDER BY a.id")
    return page(request, "list.html", articles=await cur.fetchall(), user=user)


@app.get("/article/add")
async def add_page(request: Request):
    require_user(request, "author")
    return page(request, "form.html", article=None)


@app.post("/article/add")
async def add(request: Request, category: str = Form(...), title: str = Form(...), content: str = Form(...), csrf: str = Form(...), db=Depends(getDB)):
    user = require_user(request, "author")
    check_csrf(request, csrf)
    check_fields(category, title, content)
    await db.execute("INSERT INTO articles (author_id, category, title, content) VALUES (%s,%s,%s,%s)", (user["id"], category.strip(), title.strip(), content.strip()))
    return go_home()


@app.get("/article/{article_id}")
async def detail(article_id: int, request: Request, db=Depends(getDB)):
    user = require_user(request)
    cur = await db.execute("SELECT a.*, u.username FROM articles a JOIN users u ON a.author_id=u.id WHERE a.id=%s", (article_id,))
    article = await cur.fetchone()
    if not article:
        raise HTTPException(404, "找不到稿件")
    if user["role"] == "author" and article["author_id"] != user["id"]:
        raise HTTPException(403, "只能查看自己的稿件")
    return page(request, "detail.html", article=article, user=user)


@app.get("/article/{article_id}/edit")
async def edit_page(article_id: int, request: Request, db=Depends(getDB)):
    user = require_user(request, "author")
    cur = await db.execute("SELECT * FROM articles WHERE id=%s AND author_id=%s AND status='編輯中'", (article_id, user["id"]))
    article = await cur.fetchone()
    if not article:
        raise HTTPException(403, "只能修改自己編輯中的稿件")
    return page(request, "form.html", article=article)


@app.post("/article/{article_id}/edit")
async def edit(article_id: int, request: Request, category: str = Form(...), title: str = Form(...), content: str = Form(...), csrf: str = Form(...), db=Depends(getDB)):
    user = require_user(request, "author")
    check_csrf(request, csrf)
    check_fields(category, title, content)
    cur = await db.execute("UPDATE articles SET category=%s,title=%s,content=%s WHERE id=%s AND author_id=%s AND status='編輯中'", (category.strip(), title.strip(), content.strip(), article_id, user["id"]))
    if cur.rowcount != 1:
        raise HTTPException(403, "只能修改自己編輯中的稿件")
    return go_home()


@app.post("/article/{article_id}/delete")
async def delete(article_id: int, request: Request, csrf: str = Form(...), db=Depends(getDB)):
    user = require_user(request, "author")
    check_csrf(request, csrf)
    cur = await db.execute("DELETE FROM articles WHERE id=%s AND author_id=%s AND status='編輯中'", (article_id, user["id"]))
    if cur.rowcount != 1:
        raise HTTPException(403, "只能刪除自己編輯中的稿件")
    return go_home()


@app.post("/article/{article_id}/submit")
async def submit(article_id: int, request: Request, csrf: str = Form(...), db=Depends(getDB)):
    user = require_user(request, "author")
    check_csrf(request, csrf)
    cur = await db.execute("UPDATE articles SET status='審查中' WHERE id=%s AND author_id=%s AND status='編輯中'", (article_id, user["id"]))
    if cur.rowcount != 1:
        raise HTTPException(403, "只能送出自己編輯中的稿件")
    return go_home()


@app.post("/article/{article_id}/review")
async def review(article_id: int, request: Request, decision: str = Form(...), csrf: str = Form(...), db=Depends(getDB)):
    require_user(request, "editor")
    check_csrf(request, csrf)
    if decision == "approve":
        status = "已通過"
    elif decision == "return":
        status = "編輯中"
    else:
        raise HTTPException(400, "不正確的審查選項")
    cur = await db.execute("UPDATE articles SET status=%s WHERE id=%s AND status='審查中'", (status, article_id))
    if cur.rowcount != 1:
        raise HTTPException(409, "稿件已不在審查中，請重新整理清單")
    return go_home()
