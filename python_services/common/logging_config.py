# logging_config.py

import logging

def configure_logging():
    """
    Configures the logging system to output to stdout with appropriate formatting.
    """
    logging.basicConfig(
        level=logging.DEBUG,  # Set the minimum logging level
        format='%(asctime)s - %(levelname)s - %(message)s'  # Define the log format
    )
