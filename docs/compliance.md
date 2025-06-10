# Cisco Interface Compliance Script Documentation

## Overview

The Cisco Interface Compliance script is a monitoring solution that checks for interface status on Cisco network devices and sends notifications when interfaces go down. It can be used as part of a LogZilla deployment or as a standalone solution.

## Components

The compliance monitoring system consists of:

- **ComplianceApplication**: Core application class that monitors Cisco device interfaces
- **CiscoDeviceManager**: Manages connections to Cisco devices using Netmiko
- **SlackNotifier**: Sends notifications to Slack with interactive buttons

## Configuration

The script is configured via `config.yaml` with the following key settings:

```yaml
# Cisco credentials
ciscoUsername: "admin"
ciscoPassword: "password"

# Device configuration
devices:
  - hostname: "cisco-switch-1"
    ipaddress: "10.0.0.1"

# Slack configuration  
slack:
  posturl: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
  channel: "#network-alerts"
  app_id: "A123456789"

# Slack interactive button settings
use_interactive_buttons: true
ngrok_url: "https://logzilla.ngrok.io"
```

## Deployment

The compliance script is deployed using Docker and can be managed with Docker Compose:

```bash
# Start the service
docker compose -f compose.yml up -d

# View logs
docker logs compliance-script-server

# Stop the service
docker compose -f compose.yml down
```

## Integration with LogZilla

The script integrates with LogZilla's script server infrastructure for execution management:

1. Place script files in LogZilla's script directory
2. Configure script_server.yaml for execution parameters
3. Schedule regular execution via LogZilla's UI

## Troubleshooting

Common issues:

- **Connection errors**: Verify device IP addresses and credentials
- **Slack notifications not sending**: Check webhook URL and permissions
- **Container startup issues**: Verify Docker and Docker Compose installation

## Logs

Logs are stored in:
- Container logs: Available via `docker logs compliance-script-server`
- Mounted log directory: `/var/log/logzilla/scripts/`
