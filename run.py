"""Windows 的 PostgreSQL 非同步連線需要 SelectorEventLoop。"""
import asyncio
import uvicorn

if __name__ == "__main__":
    server = uvicorn.Server(uvicorn.Config("main:app", host="127.0.0.1", port=8000))
    asyncio.run(server.serve(), loop_factory=asyncio.SelectorEventLoop)
