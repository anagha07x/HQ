"""Logging utilities."""

import logging
import sys
from datetime import datetime


class AppLogger:
    """Application logger setup."""
    
    @staticmethod
    def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
        """Setup and configure logger.
        
        Args:
            name: Logger name
            level: Logging level
            
        Returns:
            Configured logger
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        return logger
    
    @staticmethod
    def log_error(logger: logging.Logger, error: Exception, context: str = ""):
        """Log error with context.
        
        Args:
            logger: Logger instance
            error: Exception object
            context: Additional context
        """
        logger.error(f"{context}: {str(error)}", exc_info=True)
    
    @staticmethod
    def log_performance(logger: logging.Logger, operation: str, duration: float):
        """Log performance metrics.
        
        Args:
            logger: Logger instance
            operation: Operation name
            duration: Duration in seconds
        """
        logger.info(f"Performance - {operation}: {duration:.3f}s")
