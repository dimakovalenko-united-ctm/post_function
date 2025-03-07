#!/usr/bin/env python
# common/logging_utils.py
import os
import logging
import json
from typing import Any, Dict, List, Optional, Union
from google.cloud import logging as cloud_logging
from colorama import init, Fore, Style

# Initialize colorama for colored console output
init(autoreset=True)

def detect_environment() -> str:
        """
        Detect the current runtime environment.
        
        Returns:
            str: The detected environment ('gcp' or 'local')
        """
        # Check for Cloud Functions environment
        if os.environ.get('FUNCTION_TARGET'):
            return 'gcp'
        
        # Check for Cloud Run environment
        if os.environ.get('K_SERVICE'):
            return 'gcp'
        
        # Check for App Engine environment
        if os.environ.get('GAE_ENV'):
            return 'gcp'
        
        # Check for GKE (Kubernetes Engine) environment
        if os.path.exists('/var/run/secrets/kubernetes.io/serviceaccount/token'):
            return 'gcp'
        
        # Check for specific GCP metadata server
        try:
            import requests
            response = requests.get(
                'http://metadata.google.internal.', 
                timeout=1
            )
            return 'gcp'
        except (requests.ConnectionError, requests.Timeout):
            pass
        
        # If none of the above, assume local environment
        return 'local'

class CloudLogger:
    """Custom logger that supports both Google Cloud Logging and local console logging."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = None
        self.log_name = os.environ.get("LOG_FILE_NAME", "default-log")
        self.service_name = os.environ.get("LOG_SERVICE_NAME", "unknown-service")
        self.function_name = os.environ.get("LOG_FUNCTION_NAME", "unknown-function")
        self.environment = os.environ.get("ENVIRONMENT", "cloud")
        
        # Configure the logger based on environment
        if detect_environment() == "local" or self.environment.lower() == "local":
            self._setup_local_logger()
        else:
            self._setup_cloud_logger()
    
    def _setup_cloud_logger(self):
        """Setup Google Cloud Logging client."""
        self.client = cloud_logging.Client()
        self.client.setup_logging()
        self.cloud_logger = self.client.logger(self.log_name)
    
    def _setup_local_logger(self):
        """Setup local console logger with colors."""
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)
    
    def _format_message(self, message: Any) -> str:
        """Format message based on its type."""
        if isinstance(message, (dict, list)):
            return json.dumps(message)
        return str(message)
    
    def _get_labels(self, audit_log: bool = False) -> Dict[str, str]:
        """Get labels for the log entry."""
        labels = {
            "service": self.service_name,
            "function": self.function_name
        }
        if audit_log:
            labels["audit-log"] = "true"
        return labels
    
    def _log_local(self, level: str, message: Any, audit_log: bool = False):
        """Log to local console with color coding."""
        formatted_message = self._format_message(message)
        labels_str = f"[service={self.service_name}, function={self.function_name}"
        if audit_log:
            labels_str += ", audit-log=true"
        labels_str += "] "
        
        # Apply color based on log level
        if level == "ERROR":
            colored_message = f"{Fore.RED}{labels_str}{formatted_message}"
        elif level == "WARNING":
            colored_message = f"{Fore.YELLOW}{labels_str}{formatted_message}"
        elif level == "AUDIT":
            colored_message = f"{Fore.LIGHTBLACK_EX}{labels_str}{formatted_message}"
        elif level == "EXCEPTION":
            colored_message = f"{Fore.RED}{labels_str}{formatted_message}"
        elif level == "DEBUG":
            colored_message = f"{Fore.CYAN}{labels_str}{formatted_message}"    
        else:
            colored_message = f"{labels_str}{formatted_message}"
            
        # Log with the appropriate level
        if level == "ERROR":
            self.logger.error(colored_message)
        elif level == "WARNING":
            self.logger.warning(colored_message)
        elif level == "INFO" or level == "AUDIT":
            self.logger.info(colored_message)
        elif level == "DEBUG":
            self.logger.debug(colored_message)
        elif level == "EXCEPTION":
            self.logger.exception(colored_message)
    
    def _log_cloud(self, severity: str, message: Any, audit_log: bool = False):
        """Log to Google Cloud Logging."""
        structured_message = {
            "message": self._format_message(message),
            "labels": self._get_labels(audit_log)
        }
        
        # Map our severity levels to Google Cloud Logging severity
        severity_map = {
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "WARNING": "WARNING",
            "ERROR": "ERROR",
            "EXCEPTION": "ERROR",
            "AUDIT": "INFO"  # Audit logs are INFO level with a special label
        }
        
        self.cloud_logger.log_struct(
            structured_message,
            severity=severity_map.get(severity, "DEFAULT")
        )
    
    def _log(self, severity: str, message: Any, audit_log: bool = False):        
        """Log the message to the appropriate destination based on environment."""
        if detect_environment() == "local" or self.environment.lower() == "local":
            self._log_local(severity, message, audit_log)
        else:
            self._log_cloud(severity, message, audit_log)
    
    def info(self, message: Any):
        """Log an info message."""
        self._log("INFO", message)
    
    def warning(self, message: Any):
        """Log a warning message."""
        self._log("WARNING", message)
    
    def error(self, message: Any):
        """Log an error message."""
        self._log("ERROR", message)
    
    def debug(self, message: Any):
        """Log a debug message."""
        self._log("DEBUG", message)
    
    def exception(self, message: Any):
        """Log an exception message."""
        self._log("EXCEPTION", message)
    
    def audit(self, message: Any):
        """Log an audit message with the audit-log label."""
        self._log("AUDIT", message, audit_log=True)

# Create a singleton instance
logger = CloudLogger()

# Convenience functions
def info(message: Any):
    """Log an info message."""
    logger.info(message)

def warning(message: Any):
    """Log a warning message."""
    logger.warning(message)

def error(message: Any):
    """Log an error message."""
    logger.error(message)

def debug(message: Any):
    """Log a debug message."""
    logger.debug(message)

def exception(message: Any):
    """Log an exception message."""
    logger.exception(message)

def audit(message: Any):
    """Log an audit message."""
    logger.audit(message)