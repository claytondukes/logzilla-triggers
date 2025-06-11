#!/usr/bin/env python3
"""
Slack Interactive Button Handler for LogZilla Cisco Interface Compliance

This server handles Slack button interactions for bringing down interfaces back up.
It works alongside the main compliance.py script but focuses on the interactive part.

Version: 1.0.0
Author: LogZilla Team
"""

import os
import sys
import json
import yaml
import logging
import hmac
import hashlib
from flask import Flask, request, Response
from slack_notifier import SlackNotifier
from cisco_device_manager import CiscoDeviceManager

# Constants
CONFIG_FILE = os.getenv("CONFIG_FILE", "config.yaml")
DEFAULT_TIMEOUT = 10
SLACK_SUCCESS_COLOR = "#008000"  # Green
SLACK_ERROR_COLOR = "#9C1A22"    # Red
SLACK_VERIFY_TOKEN = os.getenv("SLACK_VERIFY_TOKEN", "")  # For simple verification

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Config file path
config_file = os.environ.get('CONFIG_FILE', 'config.yaml')
logger.info(f"Using config file: {config_file}")

# Load configuration
try:
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    logger.info(f"Configuration loaded successfully from {config_file}")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    config = {}

# Initialize SlackNotifier with proper parameters
slack_notifier = SlackNotifier(
    webhook_url=config.get('posturl', ''),
    timeout=config.get('timeout', DEFAULT_TIMEOUT),
    channel=config.get('default_channel', '#general')
)

# Initialize CiscoDeviceManager with proper parameters
cisco_manager = CiscoDeviceManager(
    username=config.get('ciscoUsername', ''),
    password=config.get('ciscoPassword', ''),
    timeout=config.get('timeout', DEFAULT_TIMEOUT)
)

# Configuration is already loaded above
# Using the imported CiscoDeviceManager instead of defining a custom class

# Using SlackNotifier to send responses back to Slack
# The post_update_to_slack method replaces the send_slack_response function

def verify_slack_request(request_data, timestamp, signature):
    """Verify the request is coming from Slack."""
    if not SLACK_VERIFY_TOKEN:
        logger.info("SLACK_VERIFY_TOKEN not configured, skipping verification")
        return True  # Skip verification if token not configured
    
    # Enhanced debugging to troubleshoot verification issues
    logger.info(f"SLACK_VERIFY_TOKEN (masked): {SLACK_VERIFY_TOKEN[:4]}...")
    logger.info(f"X-Slack-Request-Timestamp: {timestamp}")
    logger.info(f"X-Slack-Signature: {signature if signature else 'None'}")
    
    # This is a very basic verification method
    # For production use, implement proper Slack signing secret verification
    try:
        # Decode and log the request body (partial for security)
        body = request_data.decode('utf-8')
        safe_body = body[:100] + '...' if len(body) > 100 else body
        logger.info(f"Request body (truncated): {safe_body}")
        
        # Try to parse and find token in different formats
        if "token" in body:
            # Extract token from the body for debugging (don't log full token)
            import re
            token_match = re.search(r'token=([^&]+)', body)
            if token_match:
                token_value = token_match.group(1)
                logger.info(f"Found token in body (masked): {token_value[:4]}...")
                
                # More flexible token matching - could be URL encoded
                if SLACK_VERIFY_TOKEN in token_value or token_value in SLACK_VERIFY_TOKEN:
                    logger.info("Token verification succeeded!")
                    return True
            else:
                logger.warning("Token field found but couldn't extract value")
        else:
            logger.warning("No token field found in request body")
            
        # Try parsing as form data
        try:
            import urllib.parse
            form_data = urllib.parse.parse_qs(body)
            if 'payload' in form_data:
                payload = json.loads(form_data['payload'][0])
                if 'token' in payload:
                    token_in_payload = payload['token']
                    logger.info(f"Found token in payload (masked): {token_in_payload[:4]}...")
                    if token_in_payload == SLACK_VERIFY_TOKEN:
                        logger.info("Token verification via payload succeeded!")
                        return True
        except Exception as e:
            logger.warning(f"Error parsing potential form data: {e}")
            
        # As a fallback, check if the token is anywhere in the body
        if SLACK_VERIFY_TOKEN in body:
            logger.info("Token found in request body using fallback check")
            return True
            
    except Exception as e:
        logger.error(f"Error in token verification: {e}")
    
    logger.warning("All verification methods failed")
    return False

@app.route('/slack/actions', methods=['POST'])
def slack_actions():
    """Handle Slack interactive button actions."""
    # Get request data
    request_body = request.get_data()
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')
    
    # Verify request is from Slack (basic verification)
    if not verify_slack_request(request_body, timestamp, signature):
        logger.warning("Failed to verify Slack request")
        return Response("Verification failed", status=403)
    
    # Parse the request payload
    try:
        form_data = request.form
        payload_str = form_data.get('payload', '{}')
        payload = json.loads(payload_str)
        
        # Extract action data
        actions = payload.get('actions', [])
        if not actions:
            return Response("No action found", status=400)
            
        action = actions[0]
        action_id = action.get('action_id', '')
        action_value = action.get('value', '')
        
        # Get callback URL for responding to Slack
        response_url = payload.get('response_url', '')
        
        # Parse the action value (expected format: "device|interface")
        if '|' not in action_value:
            logger.error(f"Invalid action value format: {action_value}")
            slack_notifier.post_update_to_slack(response_url, "Invalid action format", success=False)
            return Response("Invalid action format", status=400)
            
        device, interface = action_value.split('|', 1)
        
    except Exception as e:
        logger.error(f"Error parsing Slack payload: {e}")
        return Response(f"Error: {str(e)}", status=400)
    
    # Process the action
    if action_id == "fix_interface":
        return handle_fix_interface(device, interface, response_url)
    
    return Response("Unknown action", status=400)

def handle_fix_interface(device, interface, response_url):
    """Handle the 'fix interface' button action."""
    logger.info(f"Received request to fix interface {interface} on device {device}")
    
    # Send immediate acknowledgement
    slack_notifier.post_update_to_slack(
        response_url,
        f"Attempting to bring up interface {interface} on {device}...",
        success=True,
        replace_original=False
    )
    
    # Connect to the device and bring up the interface
    if not config:
        logger.error("Configuration not loaded")
        slack_notifier.post_update_to_slack(
            response_url,
            f"Failed to bring up interface {interface}: Configuration error",
            success=False
        )
        return Response("Configuration error", status=500)
    
    # Using the already initialized cisco_manager
    
    try:
        # Connect to the device and bring interface up
        result = cisco_manager.bring_interface_up(device, interface)
        
        if result:
            logger.info(f"Successfully brought up interface {interface} on {device}")
            slack_notifier.post_update_to_slack(
                response_url,
                f"✅ Successfully brought up interface {interface} on {device}",
                success=True
            )
        else:
            logger.error(f"Failed to bring up interface {interface} on {device}")
            slack_notifier.post_update_to_slack(
                response_url,
                f"Failed to bring up interface {interface} on {device}",
                success=False
            )
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        slack_notifier.post_update_to_slack(
            response_url,
            f"Error processing request: {str(e)}",
            success=False
        )
        return Response(f"Error: {str(e)}", status=500)
    
    return Response("Processing", status=200)

if __name__ == "__main__":
    # Check if config loaded successfully
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        sys.exit(1)
    
    # Display loaded configuration (omitting sensitive data)
    logger.info(f"Loaded configuration from {config_file}")
    logger.info(f"Interactive buttons enabled: {config.get('use_interactive_buttons', False)}")
    logger.info(f"Using ngrok URL: {config.get('ngrok_url', 'Not set')}")
    
    # Verify critical configuration
    if not config.get('use_interactive_buttons', False):
        logger.warning("Interactive buttons are disabled in config. This server may not receive callbacks.")
    
    if not config.get('ngrok_url'):
        logger.warning("No ngrok URL set in config. Slack interactive buttons will not work properly.")
    
    # Start the Flask server    
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    
    logger.info(f"Starting Slack Interactive Button Server on port {port}")
    logger.info(f"Server will be accessible via ngrok at {config.get('ngrok_url', 'unknown URL')}/slack/actions")
    app.run(host='0.0.0.0', port=port, debug=debug)
