"""
Tests voor summary.py berichtopbouw.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch

from summary import send_completion_message, send_skipped_summary


def _customer():
    return {
        "name": "Loonbedrijf Hartmann",
        "street": "Voorbeeldstraat 1",
        "zip": "1234 AB",
        "city": "Reusel",
        "country": "NL",
        "sj_order_id": "199037",
    }


def test_send_skipped_summary_lists_customer_and_reason():
    sent_messages = []

    with patch("summary.send_system_message", side_effect=sent_messages.append):
        send_skipped_summary([
            {
                "customer": _customer(),
                "reason": "Geen geldig nummer; LocPhone genegeerd (alleen spoed)",
            }
        ], "2026-04-10 15:04")

    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert "OVERGESLAGEN" in msg
    assert "1 klant(en) niet benaderd" in msg
    assert "Loonbedrijf Hartmann" in msg
    assert "Geen geldig nummer" in msg
    assert "LocPhone genegeerd (alleen spoed)" in msg


def test_send_skipped_summary_is_silent_without_skips():
    with patch("summary.send_system_message") as mock_send:
        send_skipped_summary([], "2026-04-10 15:04")

    mock_send.assert_not_called()


def test_completion_message_separates_skipped_customers_from_ignored_numbers():
    sent_messages = []

    with patch("summary.send_system_message", side_effect=sent_messages.append):
        send_completion_message(
            run_date="2026-04-10 15:04",
            sent_count=15,
            failed_count=1,
            skipped_count=0,
            excluded_count=0,
            ignored_number_count=1,
            duration_seconds=160,
        )

    assert len(sent_messages) == 1
    msg = sent_messages[0]
    assert "Verstuurd:    15" in msg
    assert "Mislukt:" in msg
    assert "Klanten overgeslagen: 0" in msg
    assert "Nummers genegeerd: 1" in msg
    assert "Duur:" in msg
