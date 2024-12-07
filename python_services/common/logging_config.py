# logging_config.py

import logging
import sys

def configure_logging():
    """
    Configures the logging system to output to stdout with appropriate formatting.
    """
    logging.basicConfig(
        level=logging.INFO,  # Set the minimum logging level
        format='%(asctime)s - %(levelname)s - %(message)s'  # Define the log format
    )

def setup_logger(service_name: str) -> logging.Logger:
    """
    @brief Sets up and returns a logger for the specified service.
    
    @param service_name The name of the service.
    @return Configured Logger instance.
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.DEBUG)  # Capture all log levels

    # Prevent adding multiple handlers to the logger
    if not logger.handlers:
        # Create a StreamHandler to output logs to stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        # Define formatter with service name prefix
        formatter = logging.Formatter(
            '%(asctime)s - {service} - %(levelname)s - %(message)s'.format(service=service_name)
        )
        console_handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(console_handler)

        # Prevent log messages from being propagated to the root logger
        logger.propagate = False

    return logger

configure_logging()
