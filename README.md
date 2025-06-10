# Cisco Interface Compliance with Slack Integration

YThis repo provides an example of an advanced trigger for logzilla that will add a button to the generated slack message allowing users to decide whether or not to fix the downed interface

## general process

The solution consists of two main components that operate independently:

```mermaid
flowchart LR
    A[Compliance Script] -->|Sends Alerts| B[Slack]
    B -->|Button Clicks| C[Slack Interactive Server]
    C -->|Recovery Actions| D[Cisco Devices]
    A -->|Monitors| D
    E[LogZilla] -->|Triggers| A
    F[shared code] -->|Used by| A
    F -->|Used by| C
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Slack workspace with permissions to create apps
- ngrok account (free tier works for testing)


