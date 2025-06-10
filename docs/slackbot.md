# Slack Interactive Button Server Documentation

## Overview

The Slack Interactive Button Server component handles user interactions from Slack alert messages, enabling network operations teams to take corrective actions directly from Slack notifications. When an interface down event is detected, users can click interactive buttons to bring the interface back up or acknowledge the alert.

## Architecture

This component runs as a separate service from the main compliance script to provide better stability and independent operation. It exposes an API endpoint that Slack calls when users click interactive buttons in notifications.

## Components

- **Flask Server**: Handles HTTP requests from Slack
- **Slack Request Verification**: Validates incoming requests from Slack
- **CiscoDeviceManager Integration**: Executes network device commands
- **Response Handler**: Sends confirmation/error messages back to Slack

## Configuration

The Slack Interactive Button Server uses the same `config.yaml` file as the main compliance script. Key settings include:

```yaml
# Cisco credentials (used by the Slackbot to execute commands)
ciscoUsername: "admin"
ciscoPassword: "secure_password"
timeout: 10  # Connection timeout in seconds

# Slack settings (used for sending responses back to Slack)
posturl: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
default_channel: "#network-alerts"  # Default channel for notifications

# Interactive button settings
use_interactive_buttons: true
ngrok_url: "https://logzilla.ngrok.io"  # Public URL for Slack callbacks
```

### Environment Variables

These environment variables override settings in the config file:

```
# Security token (required)
SLACK_VERIFY_TOKEN=your_verification_token

# Server configuration
PORT=8080  # Port for the Flask server
FLASK_DEBUG=0  # Enable/disable debug mode

# Configuration file path
CONFIG_FILE=/path/to/config.yaml
```

## Security

The server implements Slack request verification using a token-based approach:
- Request verification method validates that incoming requests originate from your Slack workspace
- Token validation prevents unauthorized API access
- For production environments, implementing Slack signing secret verification is recommended

## Deployment

The Slack Interactive Button Server is deployed using Docker Compose:

```bash
# Start the slackbot service
docker compose -f docker-compose.slack.yml up -d

# View logs
docker logs slackbot-server

# Stop the service
docker compose -f docker-compose.slack.yml down
```

## ngrok Integration

Public internet exposure for the Slack API endpoint is provided through ngrok:

- Automatically creates a secure tunnel to your local server
- Custom domain capability for consistent URL (requires ngrok paid plan)
- Dashboard for traffic inspection at http://localhost:4040

## Troubleshooting

Common issues:

- **Button clicks returning errors**: Verify ngrok connection and Slack verification token
- **ngrok not connecting**: Check ngrok authentication token and network connectivity
- **Interface recovery failing**: Verify Cisco device credentials and permissions
