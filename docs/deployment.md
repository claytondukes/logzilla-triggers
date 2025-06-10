# Deployment Guide

## System Requirements

- Docker Engine 20.10+
- Docker Compose 2.0+
- Internet connectivity for Slack API calls
- Optional: ngrok account for custom domains

## Initial Setup

### 1. Configure the Environment

Create a `.env` file in the project root:

```
# Slack API credentials - used for verifying Slack requests
SLACK_VERIFY_TOKEN=your_verification_token

# Server configuration
PORT=8080
FLASK_DEBUG=0

# ngrok authentication
NGROK_AUTHTOKEN=your_ngrok_auth_token
```

### 2. Configure the Application

Update `config.yaml` with your specific settings:

```yaml
# Cisco credentials
ciscoUsername: "admin"
ciscoPassword: "secure_password"
timeout: 10  # Connection timeout in seconds

# Slack settings
posturl: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
default_channel: "#network-alerts"
slack_user: "logzilla-bot"  # Bot username for display

# Slack App ID (found in Basic Information)
slack_app_id: "A123456789"

# Interface recovery settings
bring_interface_up: false  # Set to true to auto-recover interfaces
command_delay: 10  # Delay between commands in seconds

# Interactive button settings
use_interactive_buttons: true
ngrok_url: "https://logzilla.ngrok.io"

# Security settings (can also be set as env variable)
SLACK_VERIFY_TOKEN: "your_verification_token"
```

## Deployment Options

### Option 1: Combined Deployment (Development)

For development or testing, you can run both services together:

```bash
docker compose -f compose.yml -f docker-compose.slack.yml up -d
```

### Option 2: Separated Deployment (Recommended for Production)

Run the compliance script and Slack server independently:

#### Step 1: Start the compliance monitoring service

```bash
docker compose -f compose.yml up -d
```

#### Step 2: Start the Slack interactive server

```bash
docker compose -f docker-compose.slack.yml up -d
```

## Slack App Configuration

1. Create a new Slack App at https://api.slack.com/apps
2. Enable Interactive Components:
   - Request URL: `https://your-ngrok-domain.ngrok.io/slack/actions`
   - Actions: Add the actions `fix_interface` and `acknowledge`
3. Install the app to your workspace
4. Add the Bot Token to your `.env` file

## Updating the ngrok URL

When using the free tier of ngrok, the URL changes each time the service restarts. Update your configuration:

1. Get the new ngrok URL: `docker logs ngrok | grep "started tunnel"`
2. Update the URL in `config.yaml`
3. Update the Request URL in your Slack App settings

For persistent URLs, use a paid ngrok account with reserved domains.

## Monitoring and Maintenance

### View Logs

```bash
# Compliance script logs
docker logs compliance-script-server

# Slack server logs
docker logs slackbot-server

# ngrok logs
docker logs slackbot-ngrok
```

### Restart Services

```bash
# Restart individual services
docker restart compliance-script-server
docker restart slackbot-server

# Or restart all services
docker compose -f compose.yml -f docker-compose.slack.yml restart
```
