import os
import logging
import sys
from logging.handlers import RotatingFileHandler

# Create a logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Define log level
LOG_LEVEL = logging.INFO

# Create a custom log format
log_format = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s"
)

# Configure the root logger
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)

# Configure the console logger (stdout)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)

# Configure the file logger
file_handler = RotatingFileHandler(
    "logs/chatgpt_retrieval_plugin.log",
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5,
)
file_handler.setFormatter(log_format)
logger.addHandler(file_handler)
