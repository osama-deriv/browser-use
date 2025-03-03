"""
SlackBot class for handling Slack events and running Browser Use agents using Socket Mode.
"""

import asyncio
import logging
import re
from typing import Optional, Dict, Any, List, Callable

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.socket_mode.request import SocketModeRequest
from langchain_core.language_models.chat_models import BaseChatModel

from browser_use import Agent, Browser, BrowserConfig
from browser_use.agent.views import AgentHistoryList

logger = logging.getLogger("slack_bot")

class SlackBot:
    """
    SlackBot class for handling Slack events and running Browser Use agents using Socket Mode.
    
    This class provides functionality to:
    - Handle incoming Slack events via Socket Mode
    - Run Browser Use agents based on commands
    - Send responses back to Slack
    """
    
    def __init__(
        self, 
        llm: BaseChatModel, 
        bot_token: str, 
        app_token: str,
        command_prefix: str = "$bu",
        ack: bool = True, 
        browser_config: BrowserConfig = BrowserConfig(headless=True),
        max_steps: int = 100
    ):
        """
        Initialize the SlackBot.
        
        Args:
            llm: The language model to use for the Browser Use agent
            bot_token: The Slack bot token (xoxb-...)
            app_token: The Slack app-level token for Socket Mode (xapp-...)
            command_prefix: The prefix for commands (default: "$bu")
            ack: Whether to acknowledge task receipt with a message (default: True)
            browser_config: Configuration for the browser (default: headless=True)
            max_steps: Maximum number of steps for the agent to take (default: 100)
        """
        if not bot_token or not app_token:
            raise ValueError("Bot token and app token must be provided")
        
        self.llm = llm
        self.command_prefix = command_prefix
        self.ack = ack
        self.browser_config = browser_config
        self.max_steps = max_steps
        self.client = AsyncWebClient(token=bot_token)
        self.socket_client = SocketModeClient(
            app_token=app_token,
            web_client=self.client
        )
        self.processed_events = set()
        self.running = False
        logger.info("SlackBot initialized with Socket Mode")
        
    def start(self):
        """
        Start the Socket Mode client to listen for events.
        """
        self.socket_client.socket_mode_request_listeners.append(self._handle_socket_request)
        self.running = True
        asyncio.create_task(self._start_socket_mode())
        logger.info("Socket Mode client started")
        
    async def _start_socket_mode(self):
        """
        Start the Socket Mode client in the background.
        """
        await self.socket_client.connect()
        logger.info("Socket Mode client connected")
        
    async def stop(self):
        """
        Stop the Socket Mode client.
        """
        self.running = False
        await self.socket_client.disconnect()
        logger.info("Socket Mode client stopped")
        
    async def _handle_socket_request(self, client: SocketModeClient, request: SocketModeRequest):
        """
        Handle a Socket Mode request.
        
        Args:
            client: The Socket Mode client
            request: The Socket Mode request
        """
        # Acknowledge the request
        response = SocketModeResponse(envelope_id=request.envelope_id)
        await client.send_socket_mode_response(response)
        
        # Process the event
        if request.type == "events_api":
            event = request.payload.get("event", {})
            event_id = request.payload.get("event_id", "")
            await self._handle_event(event, event_id)
            
    async def _handle_event(self, event: Dict[str, Any], event_id: str) -> None:
        """
        Handle a Slack event.
        
        Args:
            event: The Slack event data
            event_id: The ID of the event
        """
        try:
            logger.info(f"Received event id: {event_id}")
            if not event_id:
                logger.warning("Event ID missing in event data")
                return

            # Avoid processing duplicate events
            if event_id in self.processed_events:
                logger.info(f"Event {event_id} already processed")
                return
            self.processed_events.add(event_id)
            
            # Only process message events
            if event.get("type") != "message":
                return

            # Skip bot messages to avoid loops
            if 'subtype' in event and event['subtype'] == 'bot_message':
                return

            text = event.get('text', '')
            user_id = event.get('user')
            channel = event.get('channel')
            thread_ts = event.get('ts')
            
            # Check if the message is a command and has required fields
            if (text and text.startswith(f"{self.command_prefix} ") and 
                user_id is not None and channel is not None):
                await self._handle_command(text, user_id, channel, thread_ts)
            elif text and text.startswith(f"{self.command_prefix} "):
                logger.error(f"Missing required fields in event: user_id={user_id}, channel={channel}")
            
        except Exception as e:
            logger.error(f"Error in handle_event: {str(e)}")
    
    async def _handle_command(self, text: str, user_id: str, channel: str, thread_ts: Optional[str] = None) -> None:
        """
        Handle a command from a user.
        
        Args:
            text: The command text
            user_id: The ID of the user who sent the command
            channel: The channel where the command was sent
            thread_ts: The thread timestamp (for threading replies)
        """
        # Extract the task from the command
        task = text[len(self.command_prefix) + 1:].strip()
        
        # Handle help command
        if task.lower() in ["help", "--help", "-h"]:
            help_text = (
                f"*Browser Use Slack Bot*\n\n"
                f"Use `{self.command_prefix} <task>` to run a browser task.\n\n"
                f"Examples:\n"
                f"• `{self.command_prefix} Compare the price of gpt-4o and DeepSeek-V3`\n"
                f"• `{self.command_prefix} Find the latest news about AI on techcrunch.com`\n"
                f"• `{self.command_prefix} Search for job openings at OpenAI and summarize the requirements`"
            )
            await self.send_message(channel, help_text, thread_ts)
            return
        
        # Acknowledge receipt of the task
        if self.ack:
            try:
                await self.send_message(
                    channel, 
                    f"<@{user_id}> I'm working on: *{task}*\nThis may take a few minutes...", 
                    thread_ts
                )
            except Exception as e:
                logger.error(f"Error sending acknowledgment message: {e}")

        # Run the agent
        try:
            agent_message = await self.run_agent(task)
            await self.send_message(
                channel, 
                f"<@{user_id}> Task completed:\n\n{agent_message}", 
                thread_ts
            )
        except Exception as e:
            error_message = f"Error during task execution: {str(e)}"
            logger.error(error_message)
            await self.send_message(channel, error_message, thread_ts)

    async def run_agent(self, task: str) -> str:
        """
        Run a Browser Use agent with the given task.
        
        Args:
            task: The task to run
            
        Returns:
            The result of the task
        """
        try:
            browser = Browser(config=self.browser_config)
            agent = Agent(task=task, llm=self.llm, browser=browser)
            result: AgentHistoryList = await agent.run(max_steps=self.max_steps)

            # Extract the result from the agent history
            agent_message = None
            if result.is_done():
                agent_message = result.history[-1].result[0].extracted_content

            if agent_message is None:
                agent_message = 'Task completed, but no specific result was returned.'

            return agent_message

        except Exception as e:
            logger.error(f"Error during task execution: {str(e)}")
            return f'Error during task execution: {str(e)}'

    async def send_message(self, channel: str, text: str, thread_ts: Optional[str] = None) -> None:
        """
        Send a message to a Slack channel.
        
        Args:
            channel: The channel to send the message to
            text: The text of the message
            thread_ts: The thread timestamp (for threading replies)
        """
        try:
            await self.client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)
        except SlackApiError as e:
            logger.error(f"Error sending message: {e.response['error']}")
