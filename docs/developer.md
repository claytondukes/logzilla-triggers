# Developer Guide

## Architecture Overview

The Cisco Interface Compliance system consists of two main components:

1. **Compliance Monitoring Service**: Polls Cisco devices for interface status and sends alerts
2. **Slack Interactive Server**: Handles user interactions from Slack notifications

These components are intentionally separated to ensure reliability and maintainability. The LogZilla script server architecture is designed for single-execution scripts rather than long-running server processes.

## Code Structure

### Core Components

- **compliance.py**: Main application entry point for monitoring
- **cisco_device_manager.py**: Handles device connections and commands
- **slack_notifier.py**: Manages Slack notification formatting and delivery
- **slack_server.py**: Standalone server for Slack interaction callbacks
- **utils.py**: Shared utility functions

### Key Classes

#### ComplianceApplication
- Central orchestrator for monitoring activities
- Schedules interface checks and manages alert state

#### CiscoDeviceManager

Handles connections and operations on Cisco devices:

- `connect(self, host)`: Connect to a device
- `disconnect(self)`: Disconnect from a device
- `bring_interface_up(self, device, interface)`: Connect to a device and bring up an interface
- `configure_interface(self, interface, command)`: Run configuration commands on an interface
- `get_interface_description(self, interface)`: Get interface descriptions and callback URLs
- Handles response updates after user interactions

#### SlackNotifier
- Formats rich Slack messages with Block Kit
- Manages interactive buttons and callback URLs
- Handles response updates after user interactions

## Integration Points

### LogZilla Integration
The system integrates with LogZilla in two ways:
1. As a script that can be executed by LogZilla's script server
2. By providing a standalone monitoring capability outside LogZilla

### Slack API Integration
The system uses two Slack integration methods:
1. Incoming Webhooks (for sending notifications)
2. Interactive Components (for receiving button clicks)

## Development Environment

### Local Setup

1. Clone the repository
2. Create a `config.yaml` file with your settings
3. Run the services using Docker Compose

### Testing

For testing button interactions locally:
1. Start ngrok: `docker compose -f docker-compose.slack.yml up -d ngrok`
2. Note the ngrok URL: `docker logs slackbot-ngrok | grep "started tunnel"`
3. Update Slack App configuration with the ngrok URL
4. Test button clicks in Slack notifications

## Extending the System

### Adding New Actions

To add a new button action:
1. Add a new action handler in `slack_server.py`
2. Update button definitions in `slack_notifier.py`
3. Register the action in your Slack App configuration

Example:
```python
# In slack_notifier.py
buttons = [
    {
        "type": "button",
        "text": {"type": "plain_text", "text": "Fix Interface"},
        "style": "primary",
        "value": f"{event_host}|{interface}",
        "action_id": "fix_interface"
    },
    {
        "type": "button", 
        "text": {"type": "plain_text", "text": "Acknowledge"},
        "value": f"{event_host}|{interface}",
        "action_id": "acknowledge"
    },
    # New button
    {
        "type": "button",
        "text": {"type": "plain_text", "text": "Escalate"},
        "style": "danger",
        "value": f"{event_host}|{interface}",
        "action_id": "escalate"
    }
]

# In slack_server.py
@app.route('/slack/actions', methods=['POST'])
def slack_actions():
    # ... existing code ...
    
    if action_id == "fix_interface":
        return handle_fix_interface(device, interface, response_url)
    elif action_id == "acknowledge":
        return handle_acknowledge(device, interface, response_url)
    elif action_id == "escalate":
        return handle_escalate(device, interface, response_url)
        
    return Response("Unknown action", status=400)
```

### Supporting Additional Cisco Commands

To add support for new Cisco device commands:

1. Add new methods to the CiscoDeviceManager class
2. Create appropriate notification functions in SlackNotifier
3. Update the compliance checks in ComplianceApplication

## Security Considerations

- **Credential Management**: Store credentials securely using environment variables
- **Slack Request Verification**: Implement signing secret verification for production
- **Network Device Access**: Use least privilege accounts for device access
- **API Security**: Validate all inputs and implement rate limiting
