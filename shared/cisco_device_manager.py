#!/usr/bin/env python3
"""
Cisco device management module for LogZilla Network Event Orchestrator.

Provides classes and functions for interacting with Cisco devices.
"""

import re
import socket
import logging
import subprocess
import traceback
from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException

# Constants
DEFAULT_TIMEOUT = 10

class CiscoDeviceManager:
    """Manage Cisco device connections and operations."""
    
    def __init__(self, username, password, timeout=DEFAULT_TIMEOUT):
        """
        Initialize with device credentials.
        
        Args:
            username (str): Cisco device username.
            password (str): Cisco device password.
            timeout (int): Connection timeout in seconds.
        """
        self.username = username
        self.password = password
        self.timeout = timeout
        self.device = None
    
    def connect(self, host):
        """
        Connect to a Cisco device.
        
        Args:
            host (str): Device IP address or hostname.
            
        Returns:
            bool: True if connection is successful, False otherwise.
            
        Raises:
            NetmikoTimeoutException: If connection times out.
            NetmikoAuthenticationException: If authentication fails.
        """
        logging.info(f"Attempting to connect to: {host}")
        
        device_params = {
            'device_type': 'cisco_ios',
            'host': host,
            'username': self.username,
            'password': self.password,
            'timeout': self.timeout
        }
        
        try:
            # Try to connect with Netmiko
            self.device = ConnectHandler(**device_params)
            return True
        except NetmikoTimeoutException as e:
            # Enhanced error detail - perform network diagnostics
            error_details = self._run_diagnostics(host)
            error_msg = f"TCP connection to device {host} failed: {str(e)}\n\n{error_details}"
            raise NetmikoTimeoutException(error_msg) from e
        except NetmikoAuthenticationException as e:
            error_msg = f"Authentication to device {host} failed: {str(e)}"
            raise NetmikoAuthenticationException(error_msg) from e
        except Exception as e:
            error_msg = f"Unknown connection error to {host}: {str(e)}"
            logging.error(error_msg)
            logging.error(traceback.format_exc())
            raise
    
    def _run_diagnostics(self, host):
        """
        Run network diagnostics on host to gather more information about connection failures.
        
        Args:
            host (str): Target host to diagnose
            
        Returns:
            str: Diagnostic information
        """
        diagnostic_info = ["Diagnostic Information:"]
        
        # Check if host is reachable with ping
        try:
            ping_result = subprocess.run(
                ["ping", "-c", "3", "-W", "2", host],
                capture_output=True,
                text=True,
                timeout=5
            )
            if ping_result.returncode == 0:
                diagnostic_info.append(f"✅ Host {host} is reachable via ICMP (ping)")
            else:
                diagnostic_info.append(f"❌ Host {host} is NOT reachable via ICMP (ping)")
                diagnostic_info.append(f"Ping output: {ping_result.stdout}")
        except Exception as e:
            diagnostic_info.append(f"⚠️ Unable to run ping test: {str(e)}")
        
        # Check if SSH port is open
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(3)
                result = s.connect_ex((host, 22))
                if result == 0:
                    diagnostic_info.append(f"✅ SSH port (22) on {host} is open")
                else:
                    diagnostic_info.append(f"❌ SSH port (22) on {host} is closed or filtered (error code: {result})")
        except Exception as e:
            diagnostic_info.append(f"⚠️ Unable to check SSH port: {str(e)}")
            
        # Check network route
        try:
            traceroute_result = subprocess.run(
                ["traceroute", "-n", "-w", "2", "-m", "10", host],
                capture_output=True,
                text=True,
                timeout=10
            )
            if traceroute_result.returncode == 0:
                route_output = traceroute_result.stdout.strip()
                diagnostic_info.append(f"Network route to {host}:\n{route_output}")
            else:
                diagnostic_info.append(f"❌ Traceroute to {host} failed")
        except Exception as e:
            diagnostic_info.append(f"⚠️ Unable to run traceroute: {str(e)}")
            
        return "\n".join(diagnostic_info)
    
    def disconnect(self):
        """Safely disconnect from the device if connected."""
        if self.device and self.device.is_alive():
            self.device.disconnect()
            
    def bring_interface_up(self, device, interface):
        """
        Connect to a device and bring up an interface.
        
        Args:
            device (str): Device hostname or IP address.
            interface (str): Interface name to bring up.
            
        Returns:
            bool: True if the operation was successful, False otherwise.
        """
        try:
            # Connect to the device
            if not self.connect(device):
                logging.error(f"Failed to connect to {device}")
                return False
                
            # Send the no shutdown command
            result = self.configure_interface(interface, "no shutdown")
            
            # Disconnect after the operation
            self.disconnect()
            
            return result
        except Exception as e:
            logging.error(f"Error bringing up interface {interface} on {device}: {e}")
            # Ensure we disconnect even if there was an error
            self.disconnect()
            return False
    
    def configure_interface(self, interface, command):
        """
        Configure an interface on the connected device.
        
        Args:
            interface (str): Interface name.
            command (str): Command to apply to the interface.
            
        Returns:
            bool: True if configuration was successful, False otherwise.
        """
        try:
            config_commands = [
                f"interface {interface}",
                command,
                "exit"
            ]
            output = self.device.send_config_set(config_commands)
            logging.info(f"Configuration output:\n{output}")
            return True
        except Exception as e:
            logging.error(f"Failed to configure interface: {str(e)}")
            return False
    
    def get_interface_description(self, interface):
        """
        Get the description of an interface.
        
        Args:
            interface (str): Interface name.
            
        Returns:
            str: Interface description or "No description found".
        """
        output = self.device.send_command(f"show interface {interface} | include Description")
        return self._extract_interface_description(output)
    
    def _extract_interface_description(self, output):
        """
        Extract description from interface output.
        
        Args:
            output (str): Command output.
            
        Returns:
            str: Description or empty string.
        """
        if not output:
            return ""
        
        # Try to match "Description: <text>" format
        match = re.search(r"Description: (.+)", output)
        if match:
            return match.group(1).strip()
            
        return ""
    
    @staticmethod
    def parse_interface_event(event_message):
        """
        Parse interface and state from an event message.
        
        Args:
            event_message (str): Event message to parse.
            
        Returns:
            tuple: (interface_name, state) or (None, None) if parsing fails.
        """
        if not event_message:
            return None, None
        
        logging.debug(f"Parsing event message: {event_message}")
        
        # Check if the interface is reported as down
        match_down = re.search(r"Interface (\S+), changed state to down", event_message)
        if match_down:
            return match_down.group(1), "down"
        
        # Check if the interface is reported as up
        match_up = re.search(r"Interface (\S+), changed state to up", event_message)
        if match_up:
            return match_up.group(1), "up"
        
        return None, None
