import json
import logging
import os
import time
import uuid
from logging.handlers import RotatingFileHandler

from flask import g, request

SENSITIVE_KEYS = {'password', 'token', 'access_token', 'refresh_token', 'authorization', 'jwt'}


def _mask(data):
    if isinstance(data, dict):
        return {k: ('***' if k.lower() in SENSITIVE_KEYS else _mask(v)) for k, v in data.items()}
    if isinstance(data, list):
        return [_mask(item) for item in data]
    return data


def _build_logger(app):
    logger = logging.getLogger('request')
    if logger.handlers:
        return logger  # already configured (e.g. Flask reloader re-import)

    logs_dir = os.path.join(app.root_path, '..', 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'app.log'), maxBytes=2 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def init_request_logging(app):
    """Logs every request/response (method, path, status, duration) and any
    unhandled exception to logs/app.log + console, across the whole app."""
    logger = _build_logger(app)

    @app.before_request
    def _log_request():
        g.request_id = uuid.uuid4().hex[:8]
        g.request_start = time.time()
        body = request.get_json(silent=True)
        logger.info(
            '[%s] --> %s %s ip=%s body=%s',
            g.request_id, request.method, request.path, request.remote_addr,
            json.dumps(_mask(body)) if body is not None else '-',
        )

    @app.after_request
    def _log_response(response):
        duration_ms = int((time.time() - g.get('request_start', time.time())) * 1000)
        request_id = g.get('request_id', '-')
        level = logging.INFO if response.status_code < 400 else logging.WARNING
        log_body = '-'
        if response.status_code >= 400 and response.is_json:
            log_body = response.get_data(as_text=True)[:500]
        logger.log(
            level,
            '[%s] <-- %s %s status=%s duration=%sms body=%s',
            request_id, request.method, request.path, response.status_code, duration_ms, log_body,
        )
        return response

    @app.teardown_request
    def _log_exception(exc):
        if exc is not None:
            request_id = g.get('request_id', '-')
            logger.error(
                '[%s] !!! %s %s unhandled error: %s',
                request_id, request.method, request.path, exc, exc_info=exc,
            )
