"""
test_main.py - Tests voor main.py dispatch-logica
Dekt resolve_number() en de deduplicatie/fallback-lus in run().
"""

import sys
import os
from contextlib import ExitStack
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from main import resolve_number, warn_if_duplicate_test_numbers, assert_safe_test_customers


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


def test_excluded_number_is_reported_with_number():
    """Een volledig uitgesloten klant krijgt een duidelijke skip-reden."""
    customers = [
        _make_customer("Klant Exclude", "0612345678", ""),
    ]

    with ExitStack() as stack:
        stack.enter_context(patch("main.validate_config", return_value=[]))
        MockChecker = stack.enter_context(patch("main.HolidayChecker"))
        stack.enter_context(patch("main.get_customers_for_date", return_value=customers))
        stack.enter_context(patch("main.load_excluded", return_value={"+31612345678": {}}))
        stack.enter_context(patch("main.is_excluded", return_value=True))
        mock_send_whatsapp = stack.enter_context(patch("main.send_whatsapp"))
        stack.enter_context(patch("main.send_success_summary"))
        stack.enter_context(patch("main.send_failure_summary"))
        mock_completion = stack.enter_context(patch("main.send_completion_message"))
        stack.enter_context(patch("main.send_system_message"))
        stack.enter_context(patch("main.cleanup_old_logs"))
        stack.enter_context(patch("main.TEST_MODE", False))
        stack.enter_context(patch("main.MAX_CUTOFF_HOUR", 23))
        stack.enter_context(patch("main.MAX_CUTOFF_MINUTE", 59))
        mock_logger_info = stack.enter_context(patch("main.logger.info"))

        checker = MockChecker.return_value
        checker.is_nl_holiday.return_value = (False, "")
        checker.is_be_holiday.return_value = (False, "")
        checker.is_de_holiday.return_value = (False, "")
        checker.next_workday.return_value = __import__("datetime").date.today()

        import main as m
        m.run()

        mock_send_whatsapp.assert_not_called()
        mock_completion.assert_called_once()
        completion_kwargs = mock_completion.call_args.kwargs
        assert completion_kwargs["skipped_count"] == 1
        assert completion_kwargs["excluded_count"] == 1
        logged = "\n".join(str(call.args[0]) for call in mock_logger_info.call_args_list if call.args)
        assert "uitgesloten: +31612345678" in logged

    print("✅ test_excluded_number_is_reported_with_number geslaagd")


# ─── Cutoff check ────────────────────────────────────────────────────────────

class _AbortCalled(Exception):
    pass


def test_cutoff_skipped_in_test_mode():
    """In testmodus wordt de cutoff check overgeslagen, ook als cutoff al gepasseerd is."""
    from datetime import date, timedelta
    test_customers = [
        {
            **_make_customer("Test Klant", "0612345678", ""),
            "is_test_customer": True,
        },
    ]

    with ExitStack() as stack:
        stack.enter_context(patch("main.validate_config", return_value=[]))
        MockChecker = stack.enter_context(patch("main.HolidayChecker"))
        mock_get_customers_for_date = stack.enter_context(
            patch("main.get_customers_for_date")
        )
        mock_get_test_customers = stack.enter_context(
            patch("main._get_test_customers", return_value=test_customers)
        )
        stack.enter_context(patch("main.TEST_PHONE_NL", "+31612345678"))
        stack.enter_context(patch("main.TEST_PHONE_BE", "+32498123456"))
        stack.enter_context(patch("main.TEST_PHONE_DE", "+4917612345678"))
        stack.enter_context(patch("main.load_excluded", return_value=set()))
        stack.enter_context(patch("main.is_excluded", return_value=False))
        stack.enter_context(patch("main.register_failure", return_value=False))
        stack.enter_context(patch("main.register_success"))
        stack.enter_context(patch("main.get_failure_count", return_value=0))
        stack.enter_context(patch("main.send_whatsapp", return_value=(True, "ok")))
        stack.enter_context(patch("main.send_success_summary"))
        stack.enter_context(patch("main.send_failure_summary"))
        stack.enter_context(patch("main.send_completion_message"))
        stack.enter_context(patch("main.send_system_message"))
        stack.enter_context(patch("main.cleanup_old_logs"))
        stack.enter_context(patch("main.TEST_MODE", True))
        stack.enter_context(patch("main.MAX_CUTOFF_HOUR", 0))
        stack.enter_context(patch("main.MAX_CUTOFF_MINUTE", 1))
        stack.enter_context(
            patch("main.abort", side_effect=lambda r: (_ for _ in ()).throw(_AbortCalled(r)))
        )

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


def test_run_queries_next_workday_on_friday():
    """Op vrijdag wordt de DB-query voor de eerstvolgende NL-werkdag gedaan."""
    from datetime import date as real_date

    class FrozenDate(real_date):
        @classmethod
        def today(cls):
            return cls(2026, 4, 10)  # Vrijdag

    query_date = real_date(2026, 4, 13)  # Maandag

    with ExitStack() as stack:
        stack.enter_context(patch("main.date", FrozenDate))
        stack.enter_context(patch("main.validate_config", return_value=[]))
        MockChecker = stack.enter_context(patch("main.HolidayChecker"))
        mock_get_customers_for_date = stack.enter_context(
            patch("main.get_customers_for_date", return_value=[])
        )
        mock_send_system_message = stack.enter_context(
            patch("main.send_system_message")
        )
        stack.enter_context(patch("main.cleanup_old_logs"))
        stack.enter_context(patch("main.TEST_MODE", False))
        stack.enter_context(patch("main.MAX_CUTOFF_HOUR", 23))
        stack.enter_context(patch("main.MAX_CUTOFF_MINUTE", 59))
        stack.enter_context(
            patch(
                "main.get_runtime_config_diagnostics",
                return_value={
                    "dotenv_path": "C:\\repo\\.env",
                    "test_mode_source": "dotenv",
                    "test_mode_raw": "false",
                    "dotenv_test_mode_raw": "false",
                },
            )
        )

        checker = MockChecker.return_value
        checker.is_nl_holiday.return_value = (False, "")
        checker.is_be_holiday.return_value = (False, "")
        checker.is_de_holiday.return_value = (False, "")
        checker.next_workday.return_value = query_date

        try:
            import main as m
            m.run()
            assert False, "Verwacht sys.exit(0) als er geen klanten zijn"
        except SystemExit as e:
            assert e.code == 0

        checker.next_workday.assert_called_once_with(real_date(2026, 4, 10), "NL")
        mock_get_customers_for_date.assert_called_once_with(query_date)
        mock_send_system_message.assert_called_once()
        assert "2026-04-13" in mock_send_system_message.call_args[0][0]

    print("✅ test_run_queries_next_workday_on_friday geslaagd")


def test_run_logs_config_diagnostics():
    """Startup logt uit welke bron TEST_MODE is afgeleid."""
    test_customers = [
        {
            **_make_customer("Test Klant", "0612345678", ""),
            "is_test_customer": True,
        },
    ]

    with ExitStack() as stack:
        stack.enter_context(patch("main.validate_config", return_value=[]))
        MockChecker = stack.enter_context(patch("main.HolidayChecker"))
        stack.enter_context(
            patch("main._get_test_customers", return_value=test_customers)
        )
        stack.enter_context(patch("main.TEST_PHONE_NL", "+31612345678"))
        stack.enter_context(patch("main.TEST_PHONE_BE", "+32498123456"))
        stack.enter_context(patch("main.TEST_PHONE_DE", "+4917612345678"))
        stack.enter_context(patch("main.load_excluded", return_value=set()))
        stack.enter_context(patch("main.is_excluded", return_value=False))
        stack.enter_context(patch("main.register_failure", return_value=False))
        stack.enter_context(patch("main.register_success"))
        stack.enter_context(patch("main.get_failure_count", return_value=0))
        stack.enter_context(patch("main.send_whatsapp", return_value=(True, "ok")))
        stack.enter_context(patch("main.send_success_summary"))
        stack.enter_context(patch("main.send_failure_summary"))
        stack.enter_context(patch("main.send_completion_message"))
        stack.enter_context(patch("main.send_system_message"))
        stack.enter_context(patch("main.cleanup_old_logs"))
        stack.enter_context(patch("main.TEST_MODE", True))
        mock_diagnostics = stack.enter_context(
            patch(
                "main.get_runtime_config_diagnostics",
                return_value={
                    "dotenv_path": "C:\\repo\\.env",
                    "test_mode_source": "process-env",
                    "test_mode_raw": "true",
                    "dotenv_test_mode_raw": "false",
                },
            )
        )
        mock_logger_info = stack.enter_context(patch("main.logger.info"))

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

        import main as m
        m.run()

        mock_diagnostics.assert_called_once()
        mock_logger_info.assert_any_call(
            "Config bron: .env=%s | TEST_MODE raw=%s | bron=%s | .env TEST_MODE=%s",
            "C:\\repo\\.env",
            "true",
            "process-env",
            "false",
        )

    print("✅ test_run_logs_config_diagnostics geslaagd")


def test_test_mode_rejects_unmarked_customer_records():
    """Testmodus moet afbreken als een record niet expliciet als testrecord gemarkeerd is."""
    customers = [
        _make_customer("Echte klant uit DB", "0612345678", ""),
    ]

    with patch("main.TEST_PHONE_NL", "+31612345678"), \
         patch("main.TEST_PHONE_BE", "+32498123456"), \
         patch("main.TEST_PHONE_DE", "+4917612345678"), \
         patch("main.abort", side_effect=lambda r: (_ for _ in ()).throw(_AbortCalled(r))):
        try:
            assert_safe_test_customers(customers)
            assert False, "Verwacht abort voor ongemarkeerd record in testmodus"
        except _AbortCalled as e:
            assert "niet-gemarkeerde records" in str(e)

    print("✅ test_test_mode_rejects_unmarked_customer_records geslaagd")


def test_test_mode_rejects_numbers_outside_test_allowlist():
    """Testmodus moet afbreken als een testrecord een ander nummer dan TEST_PHONE_* gebruikt."""
    customers = [
        {
            **_make_customer("Onveilig testrecord", "0612345678", ""),
            "is_test_customer": True,
        },
    ]

    with patch("main.TEST_PHONE_NL", "+31699999999"), \
         patch("main.TEST_PHONE_BE", "+32498123456"), \
         patch("main.TEST_PHONE_DE", "+4917612345678"), \
         patch("main.abort", side_effect=lambda r: (_ for _ in ()).throw(_AbortCalled(r))):
        try:
            assert_safe_test_customers(customers)
            assert False, "Verwacht abort voor nummer buiten test allowlist"
        except _AbortCalled as e:
            assert "niet-toegestaan nummer" in str(e)

    print("✅ test_test_mode_rejects_numbers_outside_test_allowlist geslaagd")


# ─── Runner ──────────────────────────────────────────────────────────────────

def test_warn_if_duplicate_test_numbers_logs_warning():
    """Dubbele genormaliseerde testnummers geven een waarschuwing."""
    with patch("main.TEST_PHONE_NL", "+31612345678"), \
         patch("main.TEST_PHONE_BE", "0612345678"), \
         patch("main.TEST_PHONE_DE", "+4917612345678"), \
         patch("main.logger.warning") as mock_warning:
        warn_if_duplicate_test_numbers()

    mock_warning.assert_called_once()
    warning_text = mock_warning.call_args[0][0]
    assert "TEST_PHONE_NL" in warning_text
    assert "TEST_PHONE_BE" in warning_text
    print("âœ… test_warn_if_duplicate_test_numbers_logs_warning geslaagd")


def test_warn_if_duplicate_test_numbers_unique_is_silent():
    """Unieke testnummers geven geen waarschuwing."""
    with patch("main.TEST_PHONE_NL", "+31612345678"), \
         patch("main.TEST_PHONE_BE", "+32498123456"), \
         patch("main.TEST_PHONE_DE", "+4917612345678"), \
         patch("main.logger.warning") as mock_warning:
        warn_if_duplicate_test_numbers()

    mock_warning.assert_not_called()
    print("âœ… test_warn_if_duplicate_test_numbers_unique_is_silent geslaagd")


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
        test_excluded_number_is_reported_with_number,
        test_cutoff_skipped_in_test_mode,
        test_cutoff_enforced_outside_test_mode,
        test_run_queries_next_workday_on_friday,
        test_run_logs_config_diagnostics,
        test_test_mode_rejects_unmarked_customer_records,
        test_test_mode_rejects_numbers_outside_test_allowlist,
        test_warn_if_duplicate_test_numbers_logs_warning,
        test_warn_if_duplicate_test_numbers_unique_is_silent,
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
