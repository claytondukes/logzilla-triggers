#!/usr/bin/env python3
"""
Main application module for Cisco interface compliance.

Provides the ComplianceApplication class that orchestrates the entire workflow.
Includes Flask server for Slack interactive buttons.
"""

import os
import sys
import logging
import json
import threading
from flask import Flask, request, Response

# Import from local modules
from utils import LoggingConfigurator, ConfigLoader, NetworkUtils
from slack_notifier import SlackNotifier, SLACK_COLOR_DANGER, SLACK_COLOR_SUCCESS
from slack_notifier import SLACK_EMOJI_DOWN, SLACK_EMOJI_UP, STATUS_DOWN, STATUS_UP
from cisco_device_manager import CiscoDeviceManager, DEFAULT_TIMEOUT
from netmiko import NetmikoTimeoutException, NetmikoAuthenticationException

# Constants for Slack verification
SLACK_VERIFY_TOKEN = os.getenv("SLACK_VERIFY_TOKEN", "")  # For simple verification

# Initialize Flask app
app = Flask(__name__)

# Global reference to the ComplianceApplication instance
# (will be set in the main block)
compliance_app = None


class ComplianceApplication:
    """Main application class for Cisco interface compliance."""
    
    def __init__(self):
        """Initialize the application."""
        # Set up logging
        LoggingConfigurator.setup_logging()
        
        # Optionally print environment variables for debugging
        if logging.getLogger().getEffectiveLevel() <= logging.DEBUG:
            self._print_environment_variables()
        
        # Load configuration
        self.config = ConfigLoader.load_config('/scripts/config.yaml')
        
        # Initialize components
        self.slack = SlackNotifier(
            webhook_url=self.config['posturl'],
            timeout=self.config.get('timeout', DEFAULT_TIMEOUT),
            channel=self.config.get('default_channel', '#general')
        )
        
        self.cisco_manager = CiscoDeviceManager(
            username=self.config['ciscoUsername'],
            password=self.config['ciscoPassword'],
            timeout=self.config.get('timeout', DEFAULT_TIMEOUT)
        )
    
    def _print_environment_variables(self):
        """Print all EVENT_ environment variables if debugging is enabled."""
        logging.debug("Incoming Event Variables:")
        for key, value in os.environ.items():
            if key.startswith("EVENT"):
                logging.debug(f"{key} = {value}")
    
    def run(self):
        """Run the main application logic."""
        event_host_ip = None
        try:
            # Get and resolve hostname
            event_host = os.environ.get('EVENT_HOST', self.config.get('EVENT_HOST', ''))
            logging.debug(f"Original EVENT_HOST: {event_host}")
            
            # Resolve hostname to IP
            event_host_ip = NetworkUtils.resolve_host(event_host, self.config)
            
            # Connect to the device
            self.cisco_manager.connect(event_host_ip)
            
            # Process the event message
            event_message = os.environ.get('EVENT_MESSAGE', '')
            interface, state = self.cisco_manager.parse_interface_event(event_message)
            
            if not interface:
                logging.error("Unable to obtain interface name from event message")
                sys.exit(1)
            
            logging.debug(f"Detected interface: {interface}, state: {state}")
            
            # Get interface description
            description = self.cisco_manager.get_interface_description(interface)
            logging.debug(f"Interface Description: {description}")
            
            # Handle interface state
            self._handle_interface_state(
                event_host, 
                interface, 
                state, 
                description, 
                event_message
            )
            
        except (NetmikoTimeoutException, NetmikoAuthenticationException) as e:
            logging.error(f"Netmiko error occurred: {str(e)}")
            logging.exception("Exception details:")
            
            # Send enhanced error notification with more details
            error_message = str(e)
            formatted_error = f"ERROR: {error_message}\n\nDevice settings: {event_host_ip}:{self.config.get('port', '22')}"
            
            self.slack.send_error_notification(event_host, formatted_error)
            
        finally:
            # Ensure we disconnect cleanly
            self.cisco_manager.disconnect()
    
    def _handle_interface_state(self, event_host, interface, state, description, event_message):
        """
        Handle interface state changes.
        
        Args:
            event_host (str): Device hostname.
            interface (str): Interface name.
            state (str): Interface state ("up" or "down").
            description (str): Interface description.
            event_message (str): Original event message.
        """
        mnemonic = os.environ.get('EVENT_CISCO_MNEMONIC', '')
        
        if state == "down":
            # Check if we should add interactive buttons
            use_interactive_buttons = self.config.get('use_interactive_buttons', False)
            ngrok_url = self.config.get('ngrok_url', '')
            
            # Send notification that the interface is down
            self.slack.send_interface_notification(
                event_host, interface, "down", description, event_message,
                STATUS_DOWN, SLACK_EMOJI_DOWN, SLACK_COLOR_DANGER, mnemonic,
                use_interactive_buttons=use_interactive_buttons,
                ngrok_url=ngrok_url
            )
            
            # Bring the interface back up if configured to do so and not using buttons
            if self.config.get('bring_interface_up', True) and not use_interactive_buttons:
                logging.info(f"Action: Bringing interface {interface} back up")
                if self.cisco_manager.configure_interface(interface, "no shutdown"):
                    logging.info(f"Success: Interface {interface} should be coming back up")
                
        elif state == "up":
            # Send notification that the interface is up
            self.slack.send_interface_notification(
                event_host, interface, "up", description, event_message,
                STATUS_UP, SLACK_EMOJI_UP, SLACK_COLOR_SUCCESS, mnemonic
            )


# Flask routes for Slack interactive buttons
@app.route('/slack/actions', methods=['POST'])
def slack_actions():
    """Handle Slack interactive button actions."""
    request_body = request.get_data()
    logging.info(f"Received Slack action request: {request_body}")
    
    # Simple token verification (can be enhanced with signing secrets)
    if SLACK_VERIFY_TOKEN and request.headers.get('X-Slack-Verification-Token') != SLACK_VERIFY_TOKEN:
        logging.warning("Invalid Slack verification token")
        return Response("Unauthorized", status=401)
    
    # Parse the payload
    try:
        payload = json.loads(request.form.get('payload', '{}'))
        logging.info(f"Parsed payload: {payload}")
    except Exception as e:
        logging.error(f"Failed to parse payload: {e}")
        return Response("Invalid payload format", status=400)
    
    # Extract action data
    actions = payload.get('actions', [])
    if not actions:
        logging.error("No action found in payload")
        return Response("No action found", status=400)
    
    action = actions[0]
    action_id = action.get('action_id', '')
    value = action.get('value', '')
    response_url = payload.get('response_url', '')
    
    logging.info(f"Processing action_id: {action_id}, value: {value}")
    
    # Validate value format
    try:
        device, interface = value.split('|')
    except ValueError:
        logging.error(f"Invalid value format: {value}")
        return Response("Invalid value format", status=400)
    
    # Handle different action types
    if action_id == "fix_interface":
        return handle_fix_interface(device, interface, response_url)
    elif action_id == "acknowledge":
        return handle_acknowledge(device, interface, response_url)
    
    return Response("Unknown action", status=400)


def handle_fix_interface(device, interface, response_url):
    """Handle fix interface action."""
    logging.info(f"Fixing interface {interface} on {device}")
    
    try:
        # Get IP address for device
        device_ip = NetworkUtils.resolve_host(device, compliance_app.config)
        
        # Connect to the device
        cisco_manager = compliance_app.cisco_manager
        cisco_manager.connect(device_ip)
        
        # Configure the interface
        success = cisco_manager.configure_interface(interface, "no shutdown")
        
        # Send response back to Slack
        if success:
            message = f"✅ Successfully brought interface {interface} up on {device}"
            response = {
                "text": message,
                "replace_original": False,
                "response_type": "in_channel"
            }
            compliance_app.slack.post_update_to_slack(response_url, response)
        else:
            message = f"❌ Failed to bring interface {interface} up on {device}"
            response = {
                "text": message,
                "replace_original": False,
                "response_type": "in_channel"
            }
            compliance_app.slack.post_update_to_slack(response_url, response)
            
        return Response("Processing", status=200)
        
    except Exception as e:
        logging.error(f"Error fixing interface: {e}")
        error_response = {
            "text": f"❌ Error fixing interface {interface} on {device}: {str(e)}",
            "replace_original": False,
            "response_type": "in_channel"
        }
        compliance_app.slack.post_update_to_slack(response_url, error_response)
        return Response("Error processing", status=500)


def handle_acknowledge(device, interface, response_url):
    """Handle acknowledge action."""
    logging.info(f"Acknowledging interface {interface} issue on {device}")
    
    try:
        message = f"👍 Alert for interface {interface} on {device} has been acknowledged"
        response = {
            "text": message,
            "replace_original": False,
            "response_type": "in_channel"
        }
        compliance_app.slack.post_update_to_slack(response_url, response)
        return Response("Acknowledged", status=200)
    except Exception as e:
        logging.error(f"Error acknowledging alert: {e}")
        return Response("Error processing", status=500)


def run_flask_server():
    """Run the Flask server in a separate thread."""
    port = int(os.environ.get('PORT', 8000))  
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    logging.info(f"Starting Flask server on port {port} for Slack interactive buttons")
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    # Initialize the compliance application
    compliance_app = ComplianceApplication()
    
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask_server)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Log the Flask server startup
    port = int(os.environ.get('PORT', 8000))
    logging.info(f"Starting Flask server on port {port}")
    
    # Run the main compliance application
    compliance_app.run()
