"""Custom logging configuration with BRT timezone support."""

import logging
import pytz
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

class BRTFormatter(logging.Formatter):
    """Custom formatter that uses BRT (Brasília) timezone."""
    
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        # BRT = UTC-3 (Brasília)
        self.brt_tz = pytz.timezone('America/Sao_Paulo')
    
    def formatTime(self, record, datefmt=None):
        """Format time in BRT timezone."""
        # Convert timestamp to BRT
        dt = datetime.fromtimestamp(record.created, self.brt_tz)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")

def setup_logging_with_brt(name, level=logging.INFO, log_file=None):
    """Setup logging with BRT timezone.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional log file path
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter with BRT timezone
    formatter = BRTFormatter(
        fmt="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        # Use TimedRotatingFileHandler for rotation every 12 hours
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='H',           # Rotate by hours
            interval=12,          # Every 12 hours
            backupCount=10,      # Keep 10 backup files
            encoding='utf-8',
            delay=False,
            utc=False            # Use local time for rotation
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger