"""
test_main.py - Tests voor main.py dispatch-logica
Dekt resolve_number() en de deduplicatie/fallback-lus in run().
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from main import resolve_number


# ─── resolve_number ───────────────────────────────────────────────────────────

def test_resolve_both_valid():
    """Beide nummers geldig → mobile eerst, dan phone."""
    result = resolve_number("0612345678", "0201234567")
    types = [r[0] for r in result]
    assert types == ["mobile", "phone"]
    assert result[0][2] == "+31612345678"
    assert result[1][2] == "+31201234567"
    print("✅ test_resolve_both_valid geslaagd")


def test_resolve_only_mobile():
    """Alleen mobile geldig."""
    result = resolve_number("0612345678", "")
    assert len(result) == 1
    assert result[0][0] == "mobile"
    print("✅ test_resolve_only_mobile geslaagd")


def test_resolve_only_phone():
    """Alleen phone geldig."""
    result = resolve_number("", "0201234567")
    assert len(result) == 1
    assert result[0][0] == "phone"
    print("✅ test_resolve_only_phone geslaagd")


def test_resolve_nul_notatie_mobile_falls_back_to_phone():
    """Nul-notatie op mobile → mobile overgeslagen, phone wordt teruggegeven."""
    result = resolve_number("nul-zes 43091465", "0201234567")
    assert len(result) == 1
    assert result[0][0] == "phone"
    assert result[0][2] == "+31201234567"
    print("✅ test_resolve_nul_notatie_mobile_falls_back_to_phone geslaagd")


def test_resolve_alleen_spoed_phone():
    """'Alleen spoed' notatie op phone → phone overgeslagen."""
    result = resolve_number("0612345678", "0201234567 (alleen spoed)")
    assert len(result) == 1
    assert result[0][0] == "mobile"
    print("✅ test_resolve_alleen_spoed_phone geslaagd")


def test_resolve_invalid_mobile_falls_back_to_phone():
    """Ongeldig mobiel nummer → phone wordt als enige teruggegeven."""
    result = resolve_number("12345", "0201234567")
    assert len(result) == 1
    assert result[0][0] == "phone"
    print("✅ test_resolve_invalid_mobile_falls_back_to_phone geslaagd")


def test_resolve_both_invalid():
    """Beide nummers ongeldig → lege lijst."""
    result = resolve_number("12345", "abcde")
    assert result == []
    print("✅ test_resolve_both_invalid geslaagd")


def test_resolve_both_empty():
    """Beide nummers leeg → lege lijst."""
    result = resolve_number("", "")
    assert result == []
    print("✅ test_resolve_both_empty geslaagd")


def test_resolve_both_nul_notatie():
    """Beide nul-notatie → lege lijst."""
    result = resolve_number("nul-zes 43091465", "nul6-27856048")
    assert result == []
    print("✅ test_resolve_both_nul_notatie geslaagd")


# ─── Deduplicatie/fallback lus ────────────────────────────────────────────────

def _make_customer(name, mobile, phone, country="NL"):
    return {
        "order_id": 1,
        "sj_order_id": "TEST",
        "name": name,
        "street": "",
        "zip": "",
        "city": "",
        "country": country,
        "mobile": mobile,
        "phone": phone,
        "moment_rta": None,
    }


def _run_with_customers(customers, send_results):
    """
    Voer run() uit met gemockte afhankelijkheden.
    send_results: lijst van (success, detail) die send_whatsapp achtereenvolgens teruggeeft.
    Geeft (successes, failures, skipped) terug.
    """
    send_iter = iter(send_results)

    with patch("main.validate_config", return_value=[]), \
         patch("main.HolidayChecker") as MockChecker, \
         patch("main.get_customers_for_date", return_value=customers), \
         patch("main.load_excluded", return_value=set()), \
         patch("main.is_excluded", return_value=False), \
         patch("main.register_failure", return_value=False), \
         patch("main.register_success"), \
         patch("main.get_failure_count", return_value=0), \
         patch("main.send_whatsapp", side_effect=lambda *a, **kw: next(send_iter)), \
         patch("main.send_success_summary"), \
         patch("main.send_failure_summary"), \
         patch("main.send_completion_message"), \
         patch("main.send_system_message"), \
         patch("main.cleanup_old_logs"), \
         patch("main.TEST_MODE", False), \
         patch("main.MAX_CUTOFF_HOUR", 23), \
         patch("main.MAX_CUTOFF_MINUTE", 59):

        checker = MockChecker.return_value
        checker.is_nl_holiday.return_value = (False, "")
        checker.is_be_holiday.return_value = (False, "")
        checker.is_de_holiday.return_value = (False, "")

        from datetime import date, timedelta
        tomorrow = date.today() + timedelta(days=1)
        checker.get_holiday_scenario.return_value = {
            "scenario": "normal",
            "next_workday": tomorrow,
            "nl_holiday_name": "",
            "tomorrow_is_weekend": False,
        }

        successes = []
        failures = []
        skipped = []

        # Patch de lokale lijsten in run() door run() opnieuw te importeren
        # en de resultaten via de summary-calls te onderscheppen.
        captured = {}

        def capture_success(s, *a, **kw):
            captured["successes"] = s

        def capture_failure(f, *a, **kw):
            captured["failures"] = f

        with patch("main.send_success_summary", side_effect=capture_success), \
             patch("main.send_failure_summary", side_effect=capture_failure):
            import main as m
            m.run()

        return (
            captured.get("successes", []),
            captured.get("failures", []),
        )


def test_dedup_mobile_falls_back_to_phone():
    """
    Klant A: mobile X → success → seen_phones bevat X.
    Klant B: mobile X (zelfde), phone Y → mobile overgeslagen door dedup,
             fallback naar phone Y → bericht verstuurd naar Y.
    """
    mobile_a = "0612345678"   # → +31612345678
    phone_b  = "0201234567"   # → +31201234567  (uniek nummer)

    customers = [
        _make_customer("Klant A", mobile_a, ""),
        _make_customer("Klant B", mobile_a, phone_b),
    ]

    # Klant A mobile succeeds, Klant B phone succeeds
    successes, failures = _run_with_customers(customers, [
        (True, "ok"),   # Klant A mobile
        (True, "ok"),   # Klant B phone (fallback)
    ])

    assert len(successes) == 2, f"Verwacht 2 successen, kreeg {len(successes)}"
    nums_used = {s["phone_used"] for s in successes}
    assert "+31612345678" in nums_used
    assert "+31201234567" in nums_used
    print("✅ test_dedup_mobile_falls_back_to_phone geslaagd")


def test_dedup_duplicate_record_no_double_send():
    """
    Zelfde klant komt twee keer voor in de query (zelfde mobile én phone).
    Verwacht: slechts 1 verstuurd bericht, tweede record volledig overgeslagen.
    """
    mobile = "0612345678"
    phone  = "0201234567"

    customers = [
        _make_customer("Klant A", mobile, phone),
        _make_customer("Klant A", mobile, phone),  # duplicate record
    ]

    successes, failures = _run_with_customers(customers, [
        (True, "ok"),   # Klant A (eerste record)
        # Tweede record: beide nummers in seen_phones → geen send_whatsapp aanroep
    ])

    assert len(successes) == 1, f"Verwacht 1 succes, kreeg {len(successes)}"
    assert len(failures) == 0
    print("✅ test_dedup_duplicate_record_no_double_send geslaagd")


def test_mobile_failure_fallback_to_phone():
    """
    Mobile mislukt → fallback naar phone → succes.
    """
    customers = [
        _make_customer("Klant A", "0612345678", "0201234567"),
    ]

    successes, failures = _run_with_customers(customers, [
        (False, "timeout"),  # mobile mislukt
        (True,  "ok"),       # phone slaagt
    ])

    assert len(successes) == 1
    assert successes[0]["num_type"] == "phone"
    assert successes[0]["note"] == "via LocPhone (fallback)"
    assert len(failures) == 1   # mobile failure blijft geregistreerd
    print("✅ test_mobile_failure_fallback_to_phone geslaagd")


# ─── Cutoff check ────────────────────────────────────────────────────────────

class _AbortCalled(Exception):
    pass


def test_cutoff_skipped_in_test_mode():
    """In testmodus wordt de cutoff check overgeslagen, ook als cutoff al gepasseerd is."""
    from datetime import date, timedelta
    test_customers = [
        _make_customer("Test Klant", "0612345678", ""),
    ]

    with patch("main.validate_config", return_value=[]), \
         patch("main.HolidayChecker") as MockChecker, \
         patch("main.get_customers_for_date") as mock_get_customers_for_date, \
         patch("main._get_test_customers", return_value=test_customers) as mock_get_test_customers, \
         patch("main.load_excluded", return_value=set()), \
         patch("main.is_excluded", return_value=False), \
         patch("main.register_failure", return_value=False), \
         patch("main.register_success"), \
         patch("main.get_failure_count", return_value=0), \
         patch("main.send_whatsapp", return_value=(True, "ok")), \
         patch("main.send_success_summary"), \
         patch("main.send_failure_summary"), \
         patch("main.send_completion_message"), \
         patch("main.send_system_message"), \
         patch("main.cleanup_old_logs"), \
         patch("main.TEST_MODE", True), \
         patch("main.MAX_CUTOFF_HOUR", 0), \
         patch("main.MAX_CUTOFF_MINUTE", 1), \
         patch("main.abort", side_effect=lambda r: (_ for _ in ()).throw(_AbortCalled(r))):

        checker = MockChecker.return_value
        checker.is_nl_holiday.return_value = (False, "")
        checker.is_be_holiday.return_value = (False, "")
        checker.is_de_holiday.return_value = (False, "")

        tomorrow = date.today() + timedelta(days=1)
        checker.get_holiday_scenario.return_value = {
            "scenario": "normal",
            "next_workday": tomorrow,
            "nl_holiday_name": "",
            "tomorrow_is_weekend": False,
        }

        try:
            import main as m
            m.run()
        except _AbortCalled as e:
            assert False, f"Cutoff abort onverwacht getriggerd: {e}"

        mock_get_test_customers.assert_called_once()
        mock_get_customers_for_date.assert_not_called()

    print("✅ test_cutoff_skipped_in_test_mode geslaagd")


def test_cutoff_enforced_outside_test_mode():
    """Buiten testmodus wordt de cutoff wél gehandhaafd als die gepasseerd is."""
    with patch("main.TEST_MODE", False), \
         patch("main.MAX_CUTOFF_HOUR", 0), \
         patch("main.MAX_CUTOFF_MINUTE", 1), \
         patch("main.validate_config", return_value=[]), \
         patch("main.cleanup_old_logs"), \
         patch("main.abort", side_effect=lambda r: (_ for _ in ()).throw(_AbortCalled(r))):
        try:
            import main as m
            m.run()
            assert False, "Verwacht een cutoff abort, maar run() liep gewoon door"
        except _AbortCalled as e:
            assert "te laat" in str(e).lower(), f"Onverwachte abort reden: {e}"

    print("✅ test_cutoff_enforced_outside_test_mode geslaagd")


# ─── Runner ──────────────────────────────────────────────────────────────────

def run_all_tests():
    print("\n" + "=" * 60)
    print("TESTS: main.py (dispatch-logica)")
    print("=" * 60)
    tests = [
        test_resolve_both_valid,
        test_resolve_only_mobile,
        test_resolve_only_phone,
        test_resolve_nul_notatie_mobile_falls_back_to_phone,
        test_resolve_alleen_spoed_phone,
        test_resolve_invalid_mobile_falls_back_to_phone,
        test_resolve_both_invalid,
        test_resolve_both_empty,
        test_resolve_both_nul_notatie,
        test_dedup_mobile_falls_back_to_phone,
        test_dedup_duplicate_record_no_double_send,
        test_mobile_failure_fallback_to_phone,
        test_cutoff_skipped_in_test_mode,
        test_cutoff_enforced_outside_test_mode,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} MISLUKT: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test.__name__} FOUT: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"Resultaat: {passed} geslaagd, {failed} mislukt")
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    success = run_all_tests()
    sys.exit(0 if success else 1)
