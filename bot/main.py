"""Entry point: `python -m bot.main`.

Webhook mode when WEBHOOK_URL / RENDER_EXTERNAL_URL is set (production),
otherwise long polling (local development).
"""

import asyncio
import logging
import sys
import warnings

from telegram import BotCommand, Update
from telegram.ext import Application
from telegram.warnings import PTBUserWarning

from bot import config, db, handlers

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # its logs include the bot token in URLs

# Expected: our conversation mixes message and callback-query handlers.
warnings.filterwarnings("ignore", category=PTBUserWarning, message=".*per_message.*")


log = logging.getLogger("bot")


async def on_startup(app: Application) -> None:
    log.info("Connecting to the database...")
    await db.open_pool()
    where = await db.connection_info()
    log.info("Connected to Postgres at %s", where)
    # Shown in Telegram's "Menu" button next to the text box.
    await app.bot.set_my_commands([
        BotCommand("menu", "Show the main menu"),
        BotCommand("setbudget", "Set monthly budget, e.g. /setbudget 1500"),
        BotCommand("cancel", "Cancel the current action"),
        BotCommand("dbstatus", "Check the database connection"),
    ])
    mode = f"webhook ({config.WEBHOOK_URL})" if config.WEBHOOK_URL else "polling (local)"
    log.info("Bot is running in %s mode", mode)
    try:
        await app.bot.send_message(
            config.ALLOWED_USER_ID,
        )
    except Exception:
        # Happens if you never pressed Start on the bot, or ALLOWED_USER_ID is wrong.
        log.warning("Could not send startup message to user %s", config.ALLOWED_USER_ID)


async def on_error(update: object, context) -> None:
    log.error("Error while handling an update", exc_info=context.error)


async def on_shutdown(app: Application) -> None:
    await db.close_pool()
    log.info("Bot stopped, database connection closed")


def main() -> None:
    if sys.platform == "win32":
        # psycopg's async mode doesn't support the default Windows event loop.
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )
    handlers.register(app)
    app.add_error_handler(on_error)

    if config.WEBHOOK_URL:
        app.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            url_path="telegram",
            webhook_url=f"{config.WEBHOOK_URL}/telegram",
            secret_token=config.WEBHOOK_SECRET,
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
