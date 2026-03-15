import asyncio

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from handlers import register_handlers

dp = Dispatcher()
register_handlers(dp)


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
