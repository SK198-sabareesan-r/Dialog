"""
Comprehensive Logging System for BDA Pipeline Backend
Monitors all activities with structured logging to console and file
"""

import logging
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import traceback

# Logging configuration
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = os.getenv('LOG_FORMAT', 'detailed')  # detailed, json, simple
MAX_BYTES = 10 * 1024 * 1024  # 10MB per log file
BACKUP_COUNT = 5  # Keep 5 backup files

# Create logs directory if it doesn't exist
LOG_DIR.mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']

        # Color the level name
        record.levelname = f"{color}{record.levelname}{reset}"

        return super().format(record)


def get_logger(
    name: str,
    log_to_file: bool = True,
    log_to_console: bool = True,
    extra_data: Optional[Dict[str, Any]] = None
) -> logging.Logger:
    """
    Get a configured logger instance with comprehensive monitoring

    Args:
        name: Logger name (usually __name__)
        log_to_file: Whether to log to file
        log_to_console: Whether to log to console
        extra_data: Additional context data to include in logs

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        logger.propagate = False

        # Console Handler with colors
        if log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)

            if LOG_FORMAT == 'json':
                console_formatter = JSONFormatter()
            elif LOG_FORMAT == 'simple':
                console_formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            else:  # detailed
                console_formatter = ColoredFormatter(
                    '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )

            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

        # File Handler - Rotating by size
        if log_to_file:
            # Application log file (all logs)
            app_log_file = LOG_DIR / 'application.log'
            file_handler = RotatingFileHandler(
                app_log_file,
                maxBytes=MAX_BYTES,
                backupCount=BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)

            if LOG_FORMAT == 'json':
                file_formatter = JSONFormatter()
            else:
                file_formatter = logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )

            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

            # Error log file (only errors and critical)
            error_log_file = LOG_DIR / 'errors.log'
            error_handler = RotatingFileHandler(
                error_log_file,
                maxBytes=MAX_BYTES,
                backupCount=BACKUP_COUNT,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            logger.addHandler(error_handler)

            # Activity log file (time-based rotation - daily)
            activity_log_file = LOG_DIR / 'activity.log'
            activity_handler = TimedRotatingFileHandler(
                activity_log_file,
                when='midnight',
                interval=1,
                backupCount=30,  # Keep 30 days
                encoding='utf-8'
            )
            activity_handler.setLevel(logging.INFO)
            activity_handler.setFormatter(file_formatter)
            logger.addHandler(activity_handler)

    # Add extra data if provided
    if extra_data:
        logger = LoggerAdapter(logger, extra_data)

    return logger


class LoggerAdapter(logging.LoggerAdapter):
    """Adapter to add extra context data to all log messages"""

    def process(self, msg, kwargs):
        # Add extra data to the log record
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra']['extra_data'] = self.extra
        return msg, kwargs


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    user_id: Optional[str] = None,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None
):
    """Log API request with structured data"""
    extra_data = {
        'type': 'api_request',
        'method': method,
        'path': path,
        'user_id': user_id,
        'status_code': status_code,
        'duration_ms': duration_ms
    }

    logger.info(
        f"API {method} {path} - Status: {status_code} - Duration: {duration_ms}ms",
        extra={'extra_data': extra_data}
    )


def log_s3_operation(
    logger: logging.Logger,
    operation: str,
    bucket: str,
    key: str,
    success: bool,
    error: Optional[str] = None
):
    """Log S3 operation"""
    extra_data = {
        'type': 's3_operation',
        'operation': operation,
        'bucket': bucket,
        'key': key,
        'success': success,
        'error': error
    }

    level = logging.INFO if success else logging.ERROR
    message = f"S3 {operation} - {bucket}/{key} - {'Success' if success else f'Failed: {error}'}"

    logger.log(level, message, extra={'extra_data': extra_data})


def log_kb_operation(
    logger: logging.Logger,
    operation: str,
    kb_id: str,
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    error: Optional[str] = None
):
    """Log Knowledge Base operation"""
    extra_data = {
        'type': 'kb_operation',
        'operation': operation,
        'kb_id': kb_id,
        'job_id': job_id,
        'status': status,
        'error': error
    }

    level = logging.ERROR if error else logging.INFO
    message = f"KB {operation} - ID: {kb_id}"
    if job_id:
        message += f" - Job: {job_id}"
    if status:
        message += f" - Status: {status}"
    if error:
        message += f" - Error: {error}"

    logger.log(level, message, extra={'extra_data': extra_data})


def log_upload(
    logger: logging.Logger,
    filename: str,
    user_id: str,
    file_size: int,
    source: str,
    success: bool,
    s3_key: Optional[str] = None,
    error: Optional[str] = None
):
    """Log file upload activity"""
    extra_data = {
        'type': 'upload',
        'filename': filename,
        'user_id': user_id,
        'file_size': file_size,
        'source': source,
        'success': success,
        's3_key': s3_key,
        'error': error
    }

    level = logging.INFO if success else logging.ERROR
    message = f"Upload - {filename} ({file_size} bytes) by {user_id} from {source}"
    if success:
        message += f" - S3: {s3_key}"
    else:
        message += f" - Failed: {error}"

    logger.log(level, message, extra={'extra_data': extra_data})


def log_query(
    logger: logging.Logger,
    query: str,
    user_id: str,
    results_count: int,
    duration_ms: float,
    filters: Optional[Dict[str, Any]] = None
):
    """Log knowledge base query"""
    extra_data = {
        'type': 'query',
        'query': query,
        'user_id': user_id,
        'results_count': results_count,
        'duration_ms': duration_ms,
        'filters': filters
    }

    logger.info(
        f"Query - '{query}' by {user_id} - {results_count} results in {duration_ms}ms",
        extra={'extra_data': extra_data}
    )


def log_metadata_extraction(
    logger: logging.Logger,
    filename: str,
    extracted_fields: Dict[str, Any],
    success: bool,
    error: Optional[str] = None
):
    """Log metadata extraction"""
    extra_data = {
        'type': 'metadata_extraction',
        'filename': filename,
        'extracted_fields': extracted_fields,
        'success': success,
        'error': error
    }

    level = logging.INFO if success else logging.WARNING
    message = f"Metadata Extraction - {filename} - {len(extracted_fields)} fields"
    if error:
        message += f" - Warning: {error}"

    logger.log(level, message, extra={'extra_data': extra_data})


def log_sync_job(
    logger: logging.Logger,
    job_type: str,
    files_count: int,
    success: bool,
    duration_s: Optional[float] = None,
    error: Optional[str] = None
):
    """Log sync job activity"""
    extra_data = {
        'type': 'sync_job',
        'job_type': job_type,
        'files_count': files_count,
        'success': success,
        'duration_s': duration_s,
        'error': error
    }

    level = logging.INFO if success else logging.ERROR
    message = f"Sync Job - {job_type} - {files_count} files"
    if duration_s:
        message += f" in {duration_s:.2f}s"
    if error:
        message += f" - Failed: {error}"

    logger.log(level, message, extra={'extra_data': extra_data})


# Create a default logger for the application
app_logger = get_logger('bda_pipeline')


def setup_logging():
    """Initialize logging system - call this at application startup"""
    app_logger.info("=" * 80)
    app_logger.info("BDA Pipeline Logging System Initialized")
    app_logger.info(f"Log Directory: {LOG_DIR.absolute()}")
    app_logger.info(f"Log Level: {LOG_LEVEL}")
    app_logger.info(f"Log Format: {LOG_FORMAT}")
    app_logger.info("=" * 80)
