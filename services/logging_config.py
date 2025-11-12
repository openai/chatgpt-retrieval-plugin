"""
Production-grade logging configuration
Replaces print() statements with structured logging
"""
import logging
import sys
import os
import json
from datetime import datetime
from typing import Any, Dict
from logging.handlers import RotatingFileHandler
import traceback


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    Makes logs easily parseable by log aggregation tools (ELK, Splunk, etc.)
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class ContextLogger(logging.LoggerAdapter):
    """
    Logger adapter that adds contextual information to all log messages
    Useful for tracking requests, user_id, ticket_id, etc.
    """

    def process(self, msg, kwargs):
        # Add context to extra fields
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        if not hasattr(kwargs["extra"], "extra_fields"):
            kwargs["extra"]["extra_fields"] = {}

        # Merge context into extra fields
        kwargs["extra"]["extra_fields"].update(self.extra)

        return msg, kwargs


def setup_logging(
    log_level: str = None,
    log_file: str = None,
    json_logs: bool = False,
    service_name: str = "retrieval-plugin"
) -> logging.Logger:
    """
    Set up application logging with console and optional file output

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (if None, logs only to console)
        json_logs: Whether to use JSON formatting (recommended for production)
        service_name: Name of the service for log context

    Returns:
        Configured root logger
    """
    # Get log level from environment or parameter
    level_name = log_level or os.getenv("LOG_LEVEL", "INFO")
    level = getattr(logging, level_name.upper(), logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers = []

    # Choose formatter
    if json_logs or os.getenv("JSON_LOGS", "false").lower() == "true":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file or os.getenv("LOG_FILE"):
        log_file_path = log_file or os.getenv("LOG_FILE")
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Log startup info
    root_logger.info(
        f"Logging initialized",
        extra={
            "extra_fields": {
                "service": service_name,
                "log_level": level_name,
                "json_logs": json_logs,
                "log_file": log_file
            }
        }
    )

    return root_logger


def get_logger(name: str, context: Dict[str, Any] = None) -> logging.Logger:
    """
    Get a logger with optional context

    Args:
        name: Logger name (usually __name__)
        context: Dictionary of contextual information to add to all logs

    Returns:
        Logger or ContextLogger with context
    """
    logger = logging.getLogger(name)

    if context:
        return ContextLogger(logger, context)

    return logger


class LoggerMiddleware:
    """
    FastAPI middleware for request/response logging
    """

    def __init__(self, app):
        self.app = app
        self.logger = get_logger(__name__)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # Generate request ID
        import uuid
        request_id = str(uuid.uuid4())

        # Log request
        self.logger.info(
            f"Request started: {scope['method']} {scope['path']}",
            extra={
                "extra_fields": {
                    "request_id": request_id,
                    "method": scope["method"],
                    "path": scope["path"],
                    "client": scope.get("client"),
                }
            }
        )

        # Time the request
        import time
        start_time = time.time()

        # Create a wrapper for send to capture status code
        status_code = None

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            self.logger.error(
                f"Request failed: {scope['method']} {scope['path']}",
                exc_info=True,
                extra={
                    "extra_fields": {
                        "request_id": request_id,
                        "method": scope["method"],
                        "path": scope["path"],
                        "error": str(e),
                    }
                }
            )
            raise
        finally:
            duration = time.time() - start_time
            self.logger.info(
                f"Request completed: {scope['method']} {scope['path']}",
                extra={
                    "extra_fields": {
                        "request_id": request_id,
                        "method": scope["method"],
                        "path": scope["path"],
                        "status_code": status_code,
                        "duration_ms": round(duration * 1000, 2),
                    }
                }
            )


# Convenience functions for common logging patterns
def log_metric(logger: logging.Logger, metric_name: str, value: float, unit: str = None, **kwargs):
    """Log a metric value"""
    extra = {
        "metric_name": metric_name,
        "metric_value": value,
    }
    if unit:
        extra["metric_unit"] = unit
    extra.update(kwargs)

    logger.info(
        f"Metric: {metric_name}={value}{unit or ''}",
        extra={"extra_fields": extra}
    )


def log_query(logger: logging.Logger, query: str, results_count: int, duration_ms: float, **kwargs):
    """Log a search query"""
    logger.info(
        f"Query executed: '{query[:50]}...' returned {results_count} results in {duration_ms}ms",
        extra={
            "extra_fields": {
                "query": query,
                "results_count": results_count,
                "duration_ms": duration_ms,
                **kwargs
            }
        }
    )


def log_api_call(logger: logging.Logger, api_name: str, endpoint: str, duration_ms: float, success: bool, **kwargs):
    """Log an external API call"""
    logger.info(
        f"API call: {api_name} {endpoint} - {'success' if success else 'failed'} ({duration_ms}ms)",
        extra={
            "extra_fields": {
                "api_name": api_name,
                "endpoint": endpoint,
                "duration_ms": duration_ms,
                "success": success,
                **kwargs
            }
        }
    )
