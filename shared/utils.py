#!/usr/bin/env python3
"""
Utility modules for LogZilla Network Event Orchestrator.

Provides utility classes for logging, configuration loading, and network operations.
"""

import os
import sys
import yaml
import socket
import logging
import ipaddress
import urllib3

# Constants
REQUIRED_CONFIG_KEYS = ["ciscoUsername", "ciscoPassword", "posturl"]

class LoggingConfigurator:
    """Configure logging settings for the application."""
    
    @staticmethod
    def setup_logging():
        """Set up logging to stdout/stderr with level from environment variable."""
        # Get log level from environment variable or default to INFO
        log_level_name = os.environ.get('LOG_LEVEL', 'INFO')
        log_level = getattr(logging, log_level_name.upper(), logging.INFO)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Set third-party loggers to a higher level to reduce noise
        logging.getLogger('paramiko').setLevel(logging.WARNING)
        logging.getLogger('netmiko').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        # Suppress InsecureRequestWarning for Slack API calls with proper verification
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        logging.debug(f"Log level set to: {log_level_name}")


class ConfigLoader:
    """Load and validate configuration from YAML files."""
    
    @staticmethod
    def load_config(config_file):
        """
        Load configuration from a YAML file.
        
        Args:
            config_file (str): Path to the YAML configuration file.
            
        Returns:
            dict: Configuration as a dictionary.
            
        Raises:
            SystemExit: If the file is not found, contains invalid YAML,
                or is missing required configuration keys.
        """
        try:
            with open(config_file, 'r') as file:
                config = yaml.safe_load(file)
                
            # Validate required configuration keys
            missing_keys = [key for key in REQUIRED_CONFIG_KEYS if key not in config]
            if missing_keys:
                logging.error(f"Missing required configuration keys: {', '.join(missing_keys)}")
                sys.exit(1)
                
            return config
        except FileNotFoundError:
            logging.error(f"Configuration file {config_file} not found.")
            sys.exit(1)
        except yaml.YAMLError as e:
            logging.error(f"Error parsing configuration file: {e}")
            sys.exit(1)


class NetworkUtils:
    """Network-related utility functions."""
    
    @staticmethod
    def is_valid_ip(ip_string):
        """
        Check if a string is a valid IP address.
        
        Args:
            ip_string (str): The string to check.
            
        Returns:
            bool: True if the string is a valid IP address, False otherwise.
        """
        try:
            ipaddress.ip_address(ip_string)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def resolve_host(hostname, config):
        """
        Resolve hostname to IP address.
        
        Args:
            hostname (str): Hostname to resolve.
            config (dict): Configuration dictionary that may contain a fallback IP.
            
        Returns:
            str: IP address if resolution is successful.
            
        Raises:
            SystemExit: If resolution fails and no fallback IP is available.
        """
        # If hostname is already an IP, return it
        if NetworkUtils.is_valid_ip(hostname):
            logging.debug(f"{hostname} is already an IP address")
            return hostname
        
        # Try to resolve hostname
        try:
            logging.debug(f"Attempting to resolve hostname: {hostname}")
            ip = socket.gethostbyname(hostname)
            logging.debug(f"Resolved {hostname} to {ip}")
            return ip
        except socket.gaierror as e:
            logging.error(f"Unable to resolve {hostname}: {str(e)}")
            
            # Check if fallback IP is available
            fallback_ip = config.get('fallback_ip')
            if fallback_ip:
                logging.warning(f"Using fallback IP address: {fallback_ip}")
                return fallback_ip
            
            logging.error("No fallback IP available - cannot continue")
            sys.exit(1)
