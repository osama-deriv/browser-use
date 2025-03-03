"""
Main application for the Browser Use Slack Bot using Socket Mode.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from browser_use import BrowserConfig
from .slack_bot import SlackBot

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("slack_app")

async def main():
    """
    Main function to run the Slack bot.
    """
    # Load credentials from environment variables
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    app_token = os.getenv("SLACK_APP_TOKEN")
    
    if not bot_token or not app_token:
        raise ValueError(
            "SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in the .env file. "
            "See README.md for instructions."
        )
    
    # Load API key for the language model
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY must be set in the .env file. "
            "See README.md for instructions."
        )
    
    # Initialize the language model
    from pydantic import SecretStr
    llm = ChatOpenAI(model="gpt-4o", api_key=SecretStr(api_key))
    
    # Initialize the Slack bot
    slack_bot = SlackBot(
        llm=llm,
        bot_token=bot_token,
        app_token=app_token,
        browser_config=BrowserConfig(headless=True),
    )
    
    # Start the bot
    slack_bot.start()
    
    logger.info("Browser Use Slack Bot is running. Press Ctrl+C to exit.")
    
    try:
        # Keep the bot running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Stop the bot
        await slack_bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
