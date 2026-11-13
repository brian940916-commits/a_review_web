"""沿用課堂的連線池、Depends 與直接 SQL 寫法。"""
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import Request
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

load_dotenv()


@asynccontextmanager
async def lifespan(app):
    app.state.pool = AsyncConnectionPool(
        conninfo=os.environ["DATABASE_URL"],
        kwargs={"row_factory": dict_row}, open=False,
    )
    await app.state.pool.open(wait=True)
    try:
        yield
    finally:
        await app.state.pool.close()


async def getDB(request: Request):
    # 正常完成會自動 commit，發生錯誤會 rollback。
    async with request.app.state.pool.connection() as conn:
        yield conn
