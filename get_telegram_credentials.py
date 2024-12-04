import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with the user's chat ID."""
    chat = update.effective_chat
    await update.message.reply_text(f"Your Chat ID is: {chat.id}")

async def main() -> None:
    """Start the bot."""
    # Read bot token from .env file
    from dotenv import load_dotenv
    load_dotenv()

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Please set TELEGRAM_BOT_TOKEN in your .env file first!")
        return

    # Create the Application and pass it your bot's token
    application = Application.builder().token(token).build()

    # Register the command handler
    application.add_handler(CommandHandler("start", start))

    # Start the bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    print("Bot is running. Send /start to get your Chat ID.")
    print("Press Ctrl+C to stop.")

    # Run the bot until the user presses Ctrl-C
    await application.updater.idle()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
