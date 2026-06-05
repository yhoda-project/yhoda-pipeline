"""Pipeline email notification alerts via Gmail SMTP."""

from __future__ import annotations

import hashlib
import logging
import smtplib
import ssl
import time
from datetime import UTC, datetime
from email.mime.text import MIMEText
from enum import StrEnum
from typing import Any

from yhovi_pipeline.config import get_settings

_logger = logging.getLogger(__name__)

_DEDUP_WINDOW_SECONDS = 1800  # suppress identical alerts within 30 minutes
_RATE_LIMIT_MAX = 10  # max emails per minute
_RATE_LIMIT_WINDOW_SECONDS = 60

_dedup_cache: dict[str, float] = {}
_rate_window_start: float = 0.0
_rate_count: int = 0


class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


def _dedup_key(flow_name: str, message: str, severity: Severity) -> str:
    raw = f"{flow_name}|{message.strip().lower()}|{severity.value}"
    return hashlib.md5(raw.encode()).hexdigest()


def _is_duplicate(key: str) -> bool:
    now = time.monotonic()
    stale = [k for k, t in _dedup_cache.items() if now - t > _DEDUP_WINDOW_SECONDS]
    for k in stale:
        del _dedup_cache[k]
    if key in _dedup_cache:
        return True
    _dedup_cache[key] = now
    return False


def _is_rate_limited() -> bool:
    global _rate_window_start, _rate_count
    now = time.monotonic()
    if now - _rate_window_start > _RATE_LIMIT_WINDOW_SECONDS:
        _rate_window_start = now
        _rate_count = 0
    _rate_count += 1
    return _rate_count > _RATE_LIMIT_MAX


def _send_alert(
    flow_name: str,
    message: str,
    severity: Severity,
    metadata: dict[str, Any] | None = None,
) -> None:
    if severity == Severity.INFO:
        _logger.info("[INFO] %s - %s", flow_name, message)
        return

    settings = get_settings()
    if not settings.smtp_username or not settings.smtp_password or not settings.alert_group_email:
        return

    if severity == Severity.SUCCESS and not settings.alert_success_enabled:
        return

    key = _dedup_key(flow_name, message, severity)
    if _is_duplicate(key):
        _logger.warning("Suppressed duplicate [%s] alert for %s", severity.value, flow_name)
        return

    if _is_rate_limited():
        _logger.warning(
            "Rate limit reached - suppressing [%s] alert for %s", severity.value, flow_name
        )
        return

    sender = settings.smtp_username.get_secret_value()
    recipients = [r.strip() for r in settings.alert_group_email.split(",") if r.strip()]
    timestamp = datetime.now(UTC).strftime("%d %B %Y at %H:%M UTC")

    lines = [
        f"Flow:      {flow_name}",
        f"Severity:  {severity.value}",
        f"Time:      {timestamp}",
        f"Message:   {message}",
    ]

    if metadata:
        lines.append("")
        lines.append("Details:")
        for k, v in metadata.items():
            lines.append(f"  {k}: {v}")

    if severity == Severity.ERROR:
        lines += [
            "",
            "No action is needed from you right now. The pipeline will retry automatically on its next scheduled run.",
            "If this issue keeps happening, please contact the YHODA technical team.",
        ]

    msg = MIMEText("\n".join(lines), "plain", "utf-8")
    msg["Subject"] = f"[{severity.value}] YHODA Pipeline: {flow_name}"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Reply-To"] = sender

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(sender, settings.smtp_password.get_secret_value())
            server.sendmail(sender, recipients, msg.as_string())
        _logger.info("Sent [%s] alert for %s", severity.value, flow_name)
    except Exception:
        _logger.exception("Failed to send [%s] alert for %s", severity.value, flow_name)


def send_failure_alert(flow_name: str, error: str, metadata: dict[str, Any] | None = None) -> None:
    _send_alert(flow_name, error, Severity.ERROR, metadata)


def send_warning_alert(
    flow_name: str, message: str, metadata: dict[str, Any] | None = None
) -> None:
    _send_alert(flow_name, message, Severity.WARNING, metadata)


def send_success_alert(
    flow_name: str, message: str = "Completed successfully.", metadata: dict[str, Any] | None = None
) -> None:
    _send_alert(flow_name, message, Severity.SUCCESS, metadata)


def send_info_alert(flow_name: str, message: str) -> None:
    _send_alert(flow_name, message, Severity.INFO)
