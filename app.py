from contextlib import asynccontextmanager
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, Request

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
try:
    from config import BOT_TOKEN
except ImportError:
    pass

dp = Dispatcher()

try:
    from handlers import register_handlers
    register_handlers(dp)
except ImportError:
    import sys
    import os
    sys.path.insert(0, str(Path(__file__).parent))
    from handlers import register_handlers
    register_handlers(dp)

bot: Bot | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot
    bot = Bot(token=BOT_TOKEN)
    yield
    if bot:
        await bot.session.close()


app = FastAPI(lifespan=lifespan)


@app.post("/")
async def telegram_webhook(request: Request) -> dict:
    if bot is None:
        return {"status": "error"}
    try:
        update = Update.model_validate(await request.json(), context={"bot": bot})
        await dp.feed_update(bot=bot, update=update)
    except Exception:
        pass
    return {"ok": True}


@app.get("/")
async def root() -> dict:
    return {"status": "running"}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}
