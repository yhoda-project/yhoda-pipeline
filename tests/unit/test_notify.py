"""Unit tests for yhovi_pipeline.utils.notify.

Tests cover deduplication, rate limiting, and the send logic including
suppression conditions and email structure.  smtplib.SMTP is patched
throughout so no real network connection is made.
"""

from __future__ import annotations

import base64
import email as stdlib_email
from unittest.mock import MagicMock, patch

import pytest

import yhovi_pipeline.utils.notify as notify_module
from yhovi_pipeline.utils.notify import (
    _RATE_LIMIT_WINDOW_SECONDS,
    Severity,
    _dedup_key,
    _is_duplicate,
    _is_rate_limited,
    send_failure_alert,
    send_info_alert,
    send_success_alert,
    send_warning_alert,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_module_state() -> None:
    """Reset module-level dedup cache and rate limit counters before each test."""
    notify_module._dedup_cache.clear()
    notify_module._rate_window_start = 0.0
    notify_module._rate_count = 0


@pytest.fixture
def smtp_settings() -> MagicMock:
    """Mock Settings with SMTP credentials configured."""
    settings = MagicMock()
    settings.smtp_username = MagicMock()
    settings.smtp_username.get_secret_value.return_value = "sender@sheffield.ac.uk"
    settings.smtp_password = MagicMock()
    settings.smtp_password.get_secret_value.return_value = "app-password"
    settings.alert_group_email = "recipient@sheffield.ac.uk"
    settings.alert_success_enabled = True
    return settings


@pytest.fixture
def no_smtp_settings() -> MagicMock:
    """Mock Settings with no SMTP credentials."""
    settings = MagicMock()
    settings.smtp_username = None
    settings.smtp_password = None
    settings.alert_group_email = None
    settings.alert_success_enabled = False
    return settings


def _capture_sendmail(smtp_settings: MagicMock) -> tuple[MagicMock, dict]:
    """Return a patched SMTP class and a dict that will hold the captured sendmail args."""
    captured: dict = {}

    mock_server = MagicMock()
    mock_server.__enter__ = MagicMock(return_value=mock_server)
    mock_server.__exit__ = MagicMock(return_value=False)

    def fake_sendmail(sender: str, recipients: list, msg_str: str) -> None:
        captured["sender"] = sender
        captured["recipients"] = recipients
        captured["msg"] = msg_str

    mock_server.sendmail.side_effect = fake_sendmail
    mock_smtp_class = MagicMock(return_value=mock_server)

    return mock_smtp_class, captured


def _decode_body(msg_str: str) -> str:
    """Return the decoded plain-text body from a MIME message string."""
    parsed = stdlib_email.message_from_string(msg_str)
    payload = parsed.get_payload()
    if parsed.get("Content-Transfer-Encoding", "").lower() == "base64":
        return base64.b64decode(payload.strip()).decode("utf-8")
    return str(payload)


# ---------------------------------------------------------------------------
# _dedup_key
# ---------------------------------------------------------------------------


class TestDedupKey:
    def test_same_inputs_produce_same_key(self) -> None:
        k1 = _dedup_key("flow-a", "error msg", Severity.ERROR)
        k2 = _dedup_key("flow-a", "error msg", Severity.ERROR)
        assert k1 == k2

    def test_different_flow_names_produce_different_keys(self) -> None:
        k1 = _dedup_key("flow-a", "error", Severity.ERROR)
        k2 = _dedup_key("flow-b", "error", Severity.ERROR)
        assert k1 != k2

    def test_message_whitespace_normalised(self) -> None:
        k1 = _dedup_key("flow", "  error  ", Severity.ERROR)
        k2 = _dedup_key("flow", "error", Severity.ERROR)
        assert k1 == k2

    def test_message_case_normalised(self) -> None:
        k1 = _dedup_key("flow", "Error", Severity.ERROR)
        k2 = _dedup_key("flow", "error", Severity.ERROR)
        assert k1 == k2

    def test_different_severities_produce_different_keys(self) -> None:
        k1 = _dedup_key("flow", "msg", Severity.ERROR)
        k2 = _dedup_key("flow", "msg", Severity.WARNING)
        assert k1 != k2


# ---------------------------------------------------------------------------
# _is_duplicate
# ---------------------------------------------------------------------------


class TestIsDuplicate:
    def test_first_call_returns_false(self) -> None:
        key = _dedup_key("flow", "msg", Severity.ERROR)
        assert _is_duplicate(key) is False

    def test_second_call_with_same_key_returns_true(self) -> None:
        key = _dedup_key("flow", "msg", Severity.ERROR)
        _is_duplicate(key)
        assert _is_duplicate(key) is True

    def test_different_keys_are_independent(self) -> None:
        k1 = _dedup_key("flow-a", "msg", Severity.ERROR)
        k2 = _dedup_key("flow-b", "msg", Severity.ERROR)
        _is_duplicate(k1)
        assert _is_duplicate(k2) is False

    def test_expired_entries_pruned_and_treated_as_new(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        key = _dedup_key("flow", "msg", Severity.ERROR)
        notify_module._dedup_cache[key] = 0.0  # plant a stale entry at epoch
        monkeypatch.setattr(notify_module, "_DEDUP_WINDOW_SECONDS", 0)
        assert _is_duplicate(key) is False


# ---------------------------------------------------------------------------
# _is_rate_limited
# ---------------------------------------------------------------------------


class TestIsRateLimited:
    def test_first_ten_calls_not_limited(self) -> None:
        for _ in range(10):
            assert _is_rate_limited() is False

    def test_eleventh_call_is_limited(self) -> None:
        for _ in range(10):
            _is_rate_limited()
        assert _is_rate_limited() is True

    def test_resets_after_window_expires(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for _ in range(11):
            _is_rate_limited()
        monkeypatch.setattr(notify_module, "_rate_window_start", -(_RATE_LIMIT_WINDOW_SECONDS + 1))
        assert _is_rate_limited() is False


# ---------------------------------------------------------------------------
# _send_alert - suppression conditions
# ---------------------------------------------------------------------------


class TestSendAlertSuppression:
    def test_info_severity_never_sends_email(self, smtp_settings: MagicMock) -> None:
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP") as mock_smtp,
        ):
            send_info_alert("flow", "routine log")
        mock_smtp.assert_not_called()

    def test_missing_smtp_config_silently_returns(self, no_smtp_settings: MagicMock) -> None:
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=no_smtp_settings),
            patch("smtplib.SMTP") as mock_smtp,
        ):
            send_failure_alert("flow", "error")
        mock_smtp.assert_not_called()

    def test_success_not_sent_when_disabled(self, smtp_settings: MagicMock) -> None:
        smtp_settings.alert_success_enabled = False
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP") as mock_smtp,
        ):
            send_success_alert("flow", "done")
        mock_smtp.assert_not_called()

    def test_success_sent_when_enabled(self, smtp_settings: MagicMock) -> None:
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP") as mock_smtp,
        ):
            send_success_alert("flow", "done")
        mock_smtp.assert_called_once()

    def test_duplicate_alert_suppressed(self, smtp_settings: MagicMock) -> None:
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP") as mock_smtp,
        ):
            send_failure_alert("flow", "error")
            send_failure_alert("flow", "error")
        assert mock_smtp.call_count == 1

    def test_rate_limit_blocks_after_ten_emails(self, smtp_settings: MagicMock) -> None:
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP") as mock_smtp,
        ):
            for i in range(15):
                send_failure_alert("flow", f"unique error {i}")
        assert mock_smtp.call_count == 10

    def test_smtp_error_does_not_raise(self, smtp_settings: MagicMock) -> None:
        mock_server = MagicMock()
        mock_server.__enter__ = MagicMock(return_value=mock_server)
        mock_server.__exit__ = MagicMock(return_value=False)
        mock_server.sendmail.side_effect = Exception("connection refused")

        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP", return_value=mock_server),
        ):
            send_failure_alert("flow", "error")  # must not raise


# ---------------------------------------------------------------------------
# _send_alert - email content
# ---------------------------------------------------------------------------


class TestSendAlertContent:
    def test_error_subject_line(self, smtp_settings: MagicMock) -> None:
        mock_smtp, captured = _capture_sendmail(smtp_settings)
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP", mock_smtp),
        ):
            send_failure_alert("economy-earnings", "something broke")
        assert "[ERROR] YHODA Pipeline: economy-earnings" in captured["msg"]

    def test_warning_subject_line(self, smtp_settings: MagicMock) -> None:
        mock_smtp, captured = _capture_sendmail(smtp_settings)
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP", mock_smtp),
        ):
            send_warning_alert("society-health", "low row count")
        assert "[WARNING] YHODA Pipeline: society-health" in captured["msg"]

    def test_error_body_contains_retry_message(self, smtp_settings: MagicMock) -> None:
        mock_smtp, captured = _capture_sendmail(smtp_settings)
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP", mock_smtp),
        ):
            send_failure_alert("flow", "something broke")
        assert "retry automatically" in _decode_body(captured["msg"])

    def test_warning_body_does_not_contain_retry_message(self, smtp_settings: MagicMock) -> None:
        mock_smtp, captured = _capture_sendmail(smtp_settings)
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP", mock_smtp),
        ):
            send_warning_alert("flow", "low row count")
        assert "retry automatically" not in _decode_body(captured["msg"])

    def test_metadata_included_in_body(self, smtp_settings: MagicMock) -> None:
        mock_smtp, captured = _capture_sendmail(smtp_settings)
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP", mock_smtp),
        ):
            send_failure_alert("flow", "error", metadata={"rows": 0, "source": "nomis"})
        body = _decode_body(captured["msg"])
        assert "Details:" in body
        assert "rows: 0" in body
        assert "source: nomis" in body

    def test_comma_separated_recipients_split_correctly(self, smtp_settings: MagicMock) -> None:
        smtp_settings.alert_group_email = "a@sheffield.ac.uk, b@sheffield.ac.uk"
        mock_smtp, captured = _capture_sendmail(smtp_settings)
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP", mock_smtp),
        ):
            send_failure_alert("flow", "error")
        assert captured["recipients"] == ["a@sheffield.ac.uk", "b@sheffield.ac.uk"]

    def test_single_recipient_sent_as_list(self, smtp_settings: MagicMock) -> None:
        mock_smtp, captured = _capture_sendmail(smtp_settings)
        with (
            patch("yhovi_pipeline.utils.notify.get_settings", return_value=smtp_settings),
            patch("smtplib.SMTP", mock_smtp),
        ):
            send_failure_alert("flow", "error")
        assert captured["recipients"] == ["recipient@sheffield.ac.uk"]
