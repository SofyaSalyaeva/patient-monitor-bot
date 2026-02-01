import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.core.config import settings
from app.db.session import init_db
from app.services.llm_client import LLMClient
from app.services.nlu import NLU
from app.services.chatbot import ChatBot
from app.services.summarizer import Summarizer
from app.services.scheduler import ReminderScheduler
from app.handlers import main as main_handlers
from app.handlers import fallback as fallback_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PatientBot")


async def run():
    await init_db()

    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()

    llm = LLMClient()
    nlu = NLU(llm=llm)
    chatbot = ChatBot(llm=llm)
    summarizer = Summarizer(llm=llm)
    scheduler = ReminderScheduler(bot=bot)

    main_handlers.set_services(scheduler=scheduler, summarizer=summarizer)
    fallback_handlers.set_services(
        nlu=nlu, chatbot=chatbot, scheduler=scheduler, summarizer=summarizer, bot=bot
    )

    dp.include_router(main_handlers.router)
    dp.include_router(fallback_handlers.router)

    await scheduler.load_from_db()
    asyncio.create_task(scheduler.run_loop())

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run())
