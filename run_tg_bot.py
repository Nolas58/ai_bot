import asyncio
from core_bot.tg_bot import dp, bot, remove_webhook

async def main():
    # Удаляем вебхук перед началом работы
    await remove_webhook()
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
