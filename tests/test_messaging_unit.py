"""
Unit tests voor messaging.py throttling en systeemberichten.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock, patch

import requests

import messaging


def test_send_whatsapp_waits_before_next_message():
    """Tweede bericht wacht het resterende throttle-interval af."""
    response = Mock(status_code=200, text="ok")

    with patch("messaging.TEXTMEBOT_API_KEY", "test-key"), \
         patch("messaging.DELAY_BETWEEN_MESSAGES", 1), \
         patch("messaging.TEXTMEBOT_TIMEOUT", 10), \
         patch("messaging.requests.get", return_value=response), \
         patch("messaging.time.sleep") as mock_sleep, \
         patch("messaging.time.monotonic", side_effect=[100.0, 102.0, 103.0, 103.0]):

        messaging._last_send_time = 0.0

        success_1, _ = messaging.send_whatsapp("+31612345678", "eerste")
        success_2, _ = messaging.send_whatsapp("+31612345678", "tweede")

    assert success_1 is True
    assert success_2 is True
    mock_sleep.assert_called_once_with(6.0)


def test_send_whatsapp_skip_delay_bypasses_wait():
    """skip_delay=True slaat de throttle-wachttijd over."""
    response = Mock(status_code=200, text="ok")

    with patch("messaging.TEXTMEBOT_API_KEY", "test-key"), \
         patch("messaging.DELAY_BETWEEN_MESSAGES", 1), \
         patch("messaging.TEXTMEBOT_TIMEOUT", 10), \
         patch("messaging.requests.get", return_value=response), \
         patch("messaging.time.sleep") as mock_sleep, \
         patch("messaging.time.monotonic", side_effect=[100.0, 103.0]):

        messaging._last_send_time = 100.0

        success, _ = messaging.send_whatsapp("+31612345678", "zonder wachten", skip_delay=True)

    assert success is True
    mock_sleep.assert_not_called()


def test_send_whatsapp_http_error_updates_last_send_time():
    """Ook na een HTTP-fout wordt het laatste verzendmoment bijgewerkt."""
    response = Mock(status_code=403, text="rate limit")

    with patch("messaging.TEXTMEBOT_API_KEY", "test-key"), \
         patch("messaging.TEXTMEBOT_TIMEOUT", 10), \
         patch("messaging.requests.get", return_value=response), \
         patch("messaging.time.monotonic", return_value=250.0):

        messaging._last_send_time = 0.0
        success, detail = messaging.send_whatsapp("+31612345678", "bericht")

    assert success is False
    assert "HTTP 403" in detail
    assert messaging._last_send_time == 250.0


def test_send_whatsapp_timeout_updates_last_send_time():
    """Timeouts tellen ook mee voor throttling van volgende berichten."""
    with patch("messaging.TEXTMEBOT_API_KEY", "test-key"), \
         patch("messaging.TEXTMEBOT_TIMEOUT", 10), \
         patch("messaging.requests.get", side_effect=requests.exceptions.Timeout), \
         patch("messaging.time.monotonic", return_value=400.0):

        messaging._last_send_time = 0.0
        success, detail = messaging.send_whatsapp("+31612345678", "bericht")

    assert success is False
    assert detail == "Timeout"
    assert messaging._last_send_time == 400.0


def test_send_system_message_uses_same_throttle_path():
    """Systeemberichten lopen via send_whatsapp met delay aan."""
    with patch("config.SUMMARY_PHONE", "+31600000000"), \
         patch("messaging.send_whatsapp", return_value=(True, "ok")) as mock_send:
        success = messaging.send_system_message("samenvatting")

    assert success is True
    mock_send.assert_called_once_with("+31600000000", "samenvatting", skip_delay=False)
