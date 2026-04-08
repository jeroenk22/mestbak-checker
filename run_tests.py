"""
run_tests.py - Voer alle unit tests uit (zonder live berichten)
Gebruik: python run_tests.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows cp1252 consoles kunnen geen Unicode-emoji's afdrukken — forceer UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Zorg voor lege .env als die niet bestaat (voor tests zonder echte config)
if not os.path.exists(".env"):
    print("⚠️  Geen .env gevonden, gebruik .env.example voor tests")

from tests.test_message_builder import run_all_tests as test_messages
from tests.test_holidays import run_all_tests as test_holidays
from tests.test_messaging_unit import (
    test_send_system_message_uses_same_throttle_path,
    test_send_whatsapp_http_error_updates_last_send_time,
    test_send_whatsapp_skip_delay_bypasses_wait,
    test_send_whatsapp_timeout_updates_last_send_time,
    test_send_whatsapp_waits_before_next_message,
)
from tests.test_utils import run_all_tests as test_utils
from tests.test_main import run_all_tests as test_main
from tests.test_db import run_all_tests as test_db


def test_messaging():
    print("\n" + "=" * 60)
    print("TESTS: messaging.py (throttling)")
    print("=" * 60)
    tests = [
        test_send_whatsapp_waits_before_next_message,
        test_send_whatsapp_skip_delay_bypasses_wait,
        test_send_whatsapp_http_error_updates_last_send_time,
        test_send_whatsapp_timeout_updates_last_send_time,
        test_send_system_message_uses_same_throttle_path,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__} geslaagd")
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
    print("\n" + "=" * 60)
    print("MESTBAK-CHECKER — Alle unit tests")
    print("=" * 60)

    results = []

    results.append(("Utils (telefoonnummers)", test_utils()))
    results.append(("Message Builder (berichten)", test_messages()))
    results.append(("Holidays (feestdagen)", test_holidays()))
    results.append(("Messaging (throttling)", test_messaging()))
    results.append(("Main dispatch (resolve + dedup)", test_main()))
    results.append(("DB query laden (sql/query.sql)", test_db()))

    print("\n" + "=" * 60)
    print("EINDRESULTAAT")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✅ Alle tests geslaagd!")
        print("Volgende stap: python tests/test_messaging.py (live berichten)")
    else:
        print("\n❌ Sommige tests mislukt — controleer de output hierboven")

    sys.exit(0 if all_passed else 1)
