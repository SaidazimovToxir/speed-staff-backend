import logging
from logging.handlers import RotatingFileHandler
import os

# Create logs directory if it doesn't exist
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "app.log")

# Setup logger
logger = logging.getLogger("speed_staff")
logger.setLevel(logging.INFO)

# Formatter defines how the log lines look
formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 1. Console Handler (for viewing in terminal)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 2. File Handler (with rotation: e.g. 5 MB limit per file, keep last 5 files)
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=5,
    encoding="utf-8"
)
file_handler.setFormatter(formatter)

# Attach handlers to the logger
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
