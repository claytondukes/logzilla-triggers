#!/usr/bin/env python3
"""
Slack notification module for LogZilla Network Event Orchestrator.

Provides classes and functions for sending notifications to Slack.
"""

import os
import json
import time
import logging
import requests

# Constants
SLACK_COLOR_DANGER = "#9C1A22"  # Red color for down status
SLACK_COLOR_SUCCESS = "#008000"  # Green color for up status
SLACK_EMOJI_DOWN = "🔴"
SLACK_EMOJI_UP = "🟢"
STATUS_DOWN = "DOWN"
STATUS_UP = "RECOVERED"
DEFAULT_TIMEOUT = 10

class SlackNotifier:
    """Send notifications to Slack."""
    
    def __init__(self, webhook_url, timeout=DEFAULT_TIMEOUT, channel=None):
        """
        Initialize with Slack webhook URL or bot token.
        
        Args:
            webhook_url (str): Slack webhook URL or bot token.
            timeout (int): Request timeout in seconds.
            channel (str): Default channel to post to when using bot tokens.
        """
        self.webhook_url = webhook_url
        self.timeout = timeout
        self.channel = channel
        
        # Determine if using bot token or webhook URL
        self.using_bot_token = webhook_url.startswith('xoxb-') if webhook_url else False
        
        if self.using_bot_token:
            logging.info("Using Slack Bot token for notifications (supports interactive components)")
        else:
            logging.info("Using Slack webhook URL for notifications (limited interactivity support)")
    
    def send_interface_notification(self, event_host, interface, state, 
                           description, event_message, status, 
                           emoji, color, mnemonic, 
                           use_interactive_buttons=False, ngrok_url="",
                           user_tags=None):
        """
        Send interface status notification to Slack.
        
        Args:
            event_host (str): Device hostname.
            interface (str): Interface name.
            state (str): Interface state (up/down).
            description (str): Interface description.
            event_message (str): Original event message.
            status (str): Status string for the message (UP/DOWN).
            emoji (str): Emoji to use in the message.
            color (str): Color for the Slack attachment.
            mnemonic (str): Cisco mnemonic associated with the event.
            use_interactive_buttons (bool): Whether to include interactive buttons.
            ngrok_url (str): URL for ngrok tunnel for button callbacks.
            user_tags (dict): Dictionary of user-defined tags with additional metadata.
        
        Returns:
            bool: True if notification was sent successfully, False otherwise.
        """
        logging.info(f"Sending notification for {interface} {state} on {event_host}")
        
        # Format the timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Get the severity if available
        severity = os.environ.get('EVENT_SEVERITY', '5')
        severity_text = f"Severity {severity}" if severity else ""
        
        # Enhanced header with status badge
        status_display = f"{emoji} {status}"
        
        # Initialize user_tags if None
        if user_tags is None:
            user_tags = {}
            
        # Extract key device information from user_tags
        device_role = user_tags.get('Device-Role', '')
        device_type = user_tags.get('Device-Type', '')
        device_id = user_tags.get('DeviceID', '')
        criticality = user_tags.get('Criticality', '')
        location = user_tags.get('Location', '')
        mgmt_ip = user_tags.get('Management-IP', '')
        model = user_tags.get('Model', '')
        software = user_tags.get('Software-Version', '')
        contact = user_tags.get('Contact', '')
        contact_phone = user_tags.get('Contact-Phone', '')
        zone = user_tags.get('Zone', '')
        
        # Professional device type icons
        device_icon_map = {
            'Router': ':desktop_computer:',
            'Switch': ':control_knobs:',
            'Firewall': ':fire_extinguisher:',
            'WAP': ':antenna_bars:',
            'Edge': ':electric_plug:',
            'Core': ':globe_with_meridians:'
        }
        
        # Get appropriate device icon
        device_icon = device_icon_map.get(device_type, ':network:') 
        if device_role:
            device_icon = device_icon_map.get(device_role, device_icon)
        
        # Status colors
        status_color = color
        
        # Set criticality indicator - only for down events
        criticality_indicator = ""
        if state == "down":
            if criticality == "Critical":
                criticality_indicator = " :bangbang: *CRITICAL* :bangbang:"
            elif criticality == "High":
                criticality_indicator = " :warning: *HIGH PRIORITY*"
        
        # Create professional blocks for the message
        blocks = [
            # Professional header with device and interface info
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Interface Alert: {event_host}{criticality_indicator}",
                    "emoji": True
                }
            },
            
            # Clean divider
            {"type": "divider"},
            
            # Primary alert information in a cleaner format
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Status:* {emoji} *{status}*\n*Interface:* `{interface}`\n*Event:* {mnemonic}"
                }
            }
        ]
        
        # Device information section - more structured
        device_info = []
        
        if device_type or model:
            device_type_text = f"*Device Type:* {device_type + ' ' + model if device_type and model else device_type or model}"
            device_info.append({
                "type": "mrkdwn",
                "text": device_type_text
            })
            
        if software:
            device_info.append({
                "type": "mrkdwn",
                "text": f"*Software:* {software}"
            })
            
        if location or zone:
            location_text = f"*Location:* {location + ' / ' + zone if location and zone else location or zone}"
            device_info.append({
                "type": "mrkdwn",
                "text": location_text
            })
            
        if mgmt_ip:
            device_info.append({
                "type": "mrkdwn",
                "text": f"*Management IP:* `{mgmt_ip}`"
            })
            
        # Add device info section if we have any data
        if device_info:
            blocks.append({
                "type": "section",
                "fields": device_info
            })
        
        # Contact information if available
        contact_info = []
        
        if contact:
            contact_info.append({
                "type": "mrkdwn",
                "text": f"*Contact:* {contact}"
            })
            
        if contact_phone:
            contact_info.append({
                "type": "mrkdwn",
                "text": f"*Phone:* {contact_phone}"
            })
        
        # Add a severity indicator
        if severity:
            severity_level = int(severity)
            # Professional severity indicator
            if severity_level <= 3:
                severity_block = f"*Severity:* :red_circle: {severity}/10 (Critical)"
            elif severity_level <= 5:
                severity_block = f"*Severity:* :large_yellow_circle: {severity}/10 (Warning)"
            else:
                severity_block = f"*Severity:* :large_blue_circle: {severity}/10 (Info)"
                
            contact_info.append({
                "type": "mrkdwn",
                "text": severity_block
            })
        
        # Add contact section if we have data
        if contact_info:
            blocks.append({
                "type": "section",
                "fields": contact_info
            })
        
        # Add the event message section with enterprise styling
        blocks.append({"type": "divider"})
        
        # Format event message cleanly
        formatted_message = event_message.strip()
        # Remove any unwanted special characters if needed
        formatted_message = formatted_message.replace('%', '').replace(':', ': ') if '%' in formatted_message else formatted_message

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Event Details*\n```{formatted_message}```"
            }
        })
        
        # Add additional device details if available from user_tags
        additional_tags = []
        for key, value in user_tags.items():
            # Skip keys we've already used in specific fields
            if key not in ['Device-Role', 'Device-Type', 'DeviceID', 'Criticality', 
                           'Location', 'Management-IP', 'Model', 'Software-Version', 
                           'Contact', 'Contact-Phone', 'Zone']:
                if key in ['BGP', 'OSPF', 'VRF', 'Source-Interface', 'Wan-Interface']:
                    # Network routing information is important - highlight it
                    additional_tags.append({
                        "type": "mrkdwn", 
                        "text": f"*{key}:* `{value}`"
                    })
        
        # Add additional tags if available
        if additional_tags:
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "fields": additional_tags[:10] # Limit to 10 fields per section
            })
        
        # Add interactive buttons with professional styling if requested
        if use_interactive_buttons and state == "down" and ngrok_url:
            # Make sure the ngrok URL ends with a slash
            if not ngrok_url.endswith("/"):
                ngrok_url += "/"
            
            # Add action section with clear purpose
            blocks.append({"type": "divider"})
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Remediation Options*"
                }
            })
                
            # Add sleek, professional action buttons
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Remediate Interface",
                            "emoji": True
                        },
                        "style": "primary",
                        "value": f"{event_host}|{interface}",
                        "action_id": "fix_interface",
                        "confirm": {
                            "title": {
                                "type": "plain_text",
                                "text": "Confirm Interface Remediation"
                            },
                            "text": {
                                "type": "mrkdwn",
                                "text": f"Are you sure you want to bring up interface `{interface}` on `{event_host}`?"
                            },
                            "confirm": {
                                "type": "plain_text",
                                "text": "Yes, Remediate"
                            },
                            "deny": {
                                "type": "plain_text",
                                "text": "Cancel"
                            },
                            "style": "primary"
                        }
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Acknowledge",
                            "emoji": True
                        },
                        "value": f"{event_host}|{interface}",
                        "action_id": "acknowledge"
                    }
                ]
            })
            
            logging.info(f"Added interactive buttons with ngrok URL: {ngrok_url}slack/actions")
        
        # Add metadata footer with clean styling
        blocks.append({"type": "divider"})
        
        # Create cleaner footer with event metadata and timestamp
        footer_elements = [
            {
                "type": "mrkdwn",
                "text": f"*Timestamp:* {timestamp}"
            }
        ]
        
        if mnemonic:
            footer_elements.append({
                "type": "mrkdwn",
                "text": f"*Event Type:* {mnemonic}"
            })
            
        if device_id:
            footer_elements.append({
                "type": "mrkdwn",
                "text": f"*Device ID:* {device_id}"
            })
        
        blocks.append({
            "type": "context",
            "elements": footer_elements
        })
        
        # Professional LogZilla branding
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "*Powered by LogZilla Network Event Orchestrator*"
                }
            ]
        })
        
        # Prepare the payload with the enhanced blocks
        payload = {
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks
                }
            ]
        }
        
        return self._send_payload(payload)
    
    def send_error_notification(self, event_host, error_message):
        """
        Send error notification to Slack.
        
        Args:
            event_host (str): Device hostname.
            error_message (str): Error message.
            
        Returns:
            bool: True if notification was sent successfully, False otherwise.
        """
        logging.info(f"Sending error notification for {event_host}")
        
        # Format the timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Get troubleshooting tips
        tips = self._get_troubleshooting_tips(error_message)
        
        # Create blocks for the message with enhanced formatting
        blocks = [
            # Header
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"⚠️ Error connecting to {event_host}"
                }
            },
            
            # Divider
            {"type": "divider"},
            
            # Error information
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error Message:*\n```{error_message}```"
                }
            }
        ]
        
        # Add troubleshooting tips if available
        if tips:
            blocks.append({
                "type": "section", 
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Troubleshooting Tips:*\n{tips}"
                }
            })
        
        # Add timestamp in a footer
        blocks.append({"type": "divider"})
        
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"🕒 *Time:* {timestamp}"
                }
            ]
        })
        
        # Prepare the payload
        payload = {
            "attachments": [
                {
                    "color": SLACK_COLOR_DANGER,
                    "blocks": blocks
                }
            ]
        }
        
        return self._send_payload(payload)
    
    def _get_troubleshooting_tips(self, error_message):
        """
        Generate troubleshooting tips based on the error message.
        
        Args:
            error_message (str): The error message to analyze
            
        Returns:
            str: Relevant troubleshooting tips
        """
        tips = []
        
        # Check for common error patterns and add tips
        if "timed out" in error_message.lower():
            tips.append("• Check if the device is reachable (ping)")
            tips.append("• Verify SSH service is running on the device")
            tips.append("• Check network connectivity and firewall rules")
            
        elif "authentication failed" in error_message.lower():
            tips.append("• Verify username and password are correct")
            tips.append("• Check if the account is locked or disabled")
            
        elif "connection refused" in error_message.lower():
            tips.append("• Verify SSH service is running on port 22")
            tips.append("• Check firewall settings on the device")
            
        # Always include these general tips if we don't have specific ones
        if not tips:
            tips.append("• Verify network connectivity to the device")
            tips.append("• Check credentials in the configuration")
            tips.append("• Ensure SSH access is enabled on the device")
            
        return "\n".join(tips)
    
    def post_update_to_slack(self, response_url, message=None, success=True, replace_original=True, payload=None):
        """
        Post an update to Slack using response_url from interactive button actions.
        
        Args:
            response_url (str): Slack response URL for interactive messages
            message (str, optional): Text message to send
            success (bool, optional): Whether this represents a success (changes color)
            replace_original (bool, optional): Whether to replace the original message
            payload (dict, optional): Custom message payload if provided
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            # If a custom payload wasn't provided, create one based on the parameters
            if payload is None and message:
                color = SLACK_COLOR_SUCCESS if success else SLACK_COLOR_DANGER
                payload = {
                    "text": message,
                    "replace_original": replace_original,
                    "attachments": [
                        {
                            "color": color,
                            "text": message
                        }
                    ]
                }
            elif payload is None:
                payload = {"text": "Update from LogZilla"}
            
            # Ensure replace_original is set if not in payload already
            if isinstance(payload, dict) and "replace_original" not in payload:
                payload["replace_original"] = replace_original
            
            response = requests.post(
                response_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                logging.error(
                    f"Request to Slack response URL returned an error {response.status_code}, "
                    f"the response is:\n{response.text}"
                )
                return False
            
            logging.info("Successfully posted update to Slack")
            return True
            
        except Exception as e:
            logging.error(f"Error posting update to Slack: {str(e)}")
            logging.exception("Exception details:")
            return False
    
    def _send_payload(self, payload):
        """
        Send payload to Slack using either webhook URL or bot token.
        
        Args:
            payload (dict): Message payload.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            if self.using_bot_token:
                # When using a bot token, we need to use the Slack Web API
                # Get the channel from the config or use default
                channel = payload.get('channel', self.channel or '#general')
                
                # Prepare the headers for Slack Web API
                headers = {
                    'Content-Type': 'application/json; charset=utf-8',
                    'Authorization': f'Bearer {self.webhook_url}'
                }
                
                # Extract blocks and attachments from the payload
                api_payload = {
                    'channel': channel,
                    'text': payload.get('text', 'Notification from LogZilla')
                }
                
                # Add attachments if present
                if 'attachments' in payload:
                    api_payload['attachments'] = payload['attachments']
                
                # Send to the Slack chat.postMessage API endpoint
                response = requests.post(
                    'https://slack.com/api/chat.postMessage',
                    json=api_payload,
                    headers=headers,
                    timeout=self.timeout,
                    verify=True
                )
                
                response_data = response.json()
                if not response_data.get('ok', False):
                    logging.error(
                        f"Request to Slack API returned an error: "
                        f"{response_data.get('error', 'Unknown error')}"
                    )
                    return False
            else:
                # Traditional webhook approach
                response = requests.post(
                    self.webhook_url, 
                    json=payload, 
                    timeout=self.timeout, 
                    verify=True
                )
                
                if response.status_code != 200:
                    logging.error(
                        f"Request to Slack webhook returned an error {response.status_code}, "
                        f"the response is:\n{response.text}"
                    )
                    return False
            
            logging.info("Successfully posted to Slack")
            logging.debug(json.dumps(payload))
            return True
            
        except Exception as e:
            logging.error(f"Error sending notification to Slack: {str(e)}")
            logging.exception("Exception details:")
            return False
