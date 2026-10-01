import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.core.config import settings
from app.bot.handlers import customer, admin, admin_panel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

dp.include_router(customer.router)
dp.include_router(admin.router)
dp.include_router(admin_panel.router)

async def start_bot():
    if not settings.BOT_TOKEN or settings.BOT_TOKEN == "dummy_token":
        logger.warning("BOT_TOKEN is not configured properly. Bot will not start.")
        return
    logger.info("Starting bot...")
    
    if settings.WEB_APP_URL:
        try:
            from aiogram.types import MenuButtonWebApp, WebAppInfo
            import time
            v = int(time.time())
            await bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="ilova",
                    web_app=WebAppInfo(url=f"{settings.WEB_APP_URL}?v={v}")
                )
            )
            logger.info(f"Updated Chat Menu Button WebApp URL with version v={v}")
        except Exception as e:
            logger.error(f"Failed to update chat menu button: {e}")
            
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning(f"delete_webhook error: {e}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_bot())
