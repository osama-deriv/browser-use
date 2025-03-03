# Browser Use Slack Bot

A Slack bot that allows users to run Browser Use tasks directly from Slack using Socket Mode.

## Features

- Run browser automation tasks directly from Slack
- Uses Slack's Socket Mode for secure communication (no public endpoints needed)
- Supports threading for organized conversations
- Provides helpful feedback during task execution
- Configurable command prefix

## Setup Instructions

### 1. Create a Slack App

1. Go to the [Slack API Dashboard](https://api.slack.com/apps)
2. Click "Create New App" and choose "From scratch"
3. Give your app a name (e.g., "Browser Use Bot") and select your workspace

### 2. Configure Bot Permissions

1. Navigate to "OAuth & Permissions" in the sidebar
2. Under "Bot Token Scopes", add the following scopes:
   - `chat:write` - To send messages
   - `channels:history` - To read channel messages
   - `im:history` - To read direct messages

### 3. Enable Socket Mode

1. Navigate to "Socket Mode" in the sidebar
2. Enable Socket Mode
3. Generate an app-level token with the `connections:write` scope
4. Save this token as it will be used as your `SLACK_APP_TOKEN`

### 4. Enable Event Subscriptions

1. Navigate to "Event Subscriptions" in the sidebar
2. Enable events
3. Under "Subscribe to bot events", add:
   - `message.channels` - To receive messages in channels
   - `message.im` - To receive direct messages

### 5. Install the App to Your Workspace

1. Navigate to "Install App" in the sidebar
2. Click "Install to Workspace"
3. Authorize the app

### 6. Set Up Environment Variables

Create a `.env` file in the root directory with the following variables:

```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
OPENAI_API_KEY=your-openai-api-key
```

- `SLACK_BOT_TOKEN`: Found in "OAuth & Permissions" > "Bot User OAuth Token"
- `SLACK_APP_TOKEN`: The app-level token generated when enabling Socket Mode
- `OPENAI_API_KEY`: Your OpenAI API key for GPT-4o

### 7. Install Required Packages

```bash
pip install slack_sdk langchain_openai browser-use pydantic
```

## Usage

### Starting the Bot

Run the bot with:

```bash
python -m agent.slack-app.app
```

### Using the Bot in Slack

Once the bot is running, you can use it in any channel where the bot is invited:

1. Invite the bot to a channel: `/invite @your-bot-name`
2. Send a command: `$bu Compare the price of gpt-4o and DeepSeek-V3`

### Available Commands

- `$bu <task>` - Run a browser task
- `$bu help` - Show help information

### Example Tasks

- `$bu Compare the price of gpt-4o and DeepSeek-V3`
- `$bu Find the latest news about AI on techcrunch.com`
- `$bu Search for job openings at OpenAI and summarize the requirements`

## Customization

You can customize the bot by modifying the parameters in `app.py`:

- Change the command prefix (default: `$bu`)
- Configure browser settings (headless mode, etc.)
- Set the maximum number of steps for the agent
- Change the acknowledgment behavior

## Troubleshooting

### Bot Not Responding

- Ensure the bot is running
- Check that the bot has been invited to the channel
- Verify that the bot has the necessary permissions
- Check the logs for any errors

### Authentication Errors

- Verify that your environment variables are set correctly
- Ensure that the bot token and app token are valid
- Check that the bot has been properly installed to your workspace

### Browser Errors

- Ensure that Playwright is installed: `playwright install`
- Check that the browser is accessible in your environment
- If using a remote server, ensure that the browser can run in headless mode
