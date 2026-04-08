"""
test_messaging.py - Live berichten test naar eigen nummers
Stuurt alle berichtvarianten naar de testnummers uit .env.
Gebruik: python tests/test_messaging.py

WAARSCHUWING: Dit stuurt echte WhatsApp berichten!
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from dotenv import load_dotenv
load_dotenv()

from config import TEST_PHONE_NL, TEST_PHONE_BE, TEST_PHONE_DE, DELAY_BETWEEN_MESSAGES
from messaging import send_whatsapp
from message_builder import build_message
from holidays import HolidayChecker


# Mock feestdagendata voor tests (zelfde als in test_holidays.py)
NL_HOLIDAYS = [
    {"date": "2026-04-27", "localName": "Koningsdag", "types": ["Public"], "counties": None},
    {"date": "2026-04-06", "localName": "Paasmaandag", "types": ["Public"], "counties": None},
    {"date": "2026-12-25", "localName": "Eerste Kerstdag", "types": ["Public"], "counties": None},
]
BE_HOLIDAYS = [
    {"date": "2026-07-21", "localName": "Nationale feestdag", "types": ["Public"], "counties": None},
    {"date": "2026-04-06", "localName": "Paasmaandag", "types": ["Public"], "counties": None},
    {"date": "2026-11-11", "localName": "Wapenstilstand", "types": ["Public"], "counties": None},
]
DE_HOLIDAYS = [
    {"date": "2026-10-03", "localName": "Tag der Deutschen Einheit", "types": ["Public"], "counties": None},
    {"date": "2026-11-01", "localName": "Allerheiligen", "types": ["Public"], "counties": ["DE-NW", "DE-BY", "DE-BW", "DE-RP", "DE-SL"]},
    {"date": "2026-04-06", "localName": "Ostermontag", "types": ["Public"], "counties": ["DE-NW", "DE-NI", "DE-BY", "DE-BW"]},
]


def make_mock_checker():
    checker = HolidayChecker()
    checker._cache = {
        "NL_2026": NL_HOLIDAYS,
        "NL_2027": [],
        "BE_2026": BE_HOLIDAYS,
        "BE_2027": [],
        "DE_2026": DE_HOLIDAYS,
        "DE_2027": [],
    }
    return checker


def send_test(label: str, phone: str, language: str, scenario: dict,
              today: date, hour: int = 13) -> bool:
    """Stuur één testbericht en rapporteer resultaat."""
    message = build_message(language, scenario, today, hour=hour)

    print(f"\n{'─' * 50}")
    print(f"TEST: {label}")
    print(f"Naar: {phone}")
    print(f"Bericht:\n{message}")
    print(f"{'─' * 50}")

    success, detail = send_whatsapp(phone, message, skip_delay=False)
    if success:
        print(f"✅ Verstuurd")
    else:
        print(f"❌ Mislukt: {detail}")
    return success


def run_live_tests():
    """Voer alle live berichttests uit naar eigen nummers."""
    if not TEST_PHONE_NL or not TEST_PHONE_BE or not TEST_PHONE_DE:
        print("❌ TEST_PHONE_NL, TEST_PHONE_BE en TEST_PHONE_DE moeten ingesteld zijn in .env")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("LIVE BERICHTENTEST — Mestbak-checker")
    print("=" * 60)
    print(f"NL testnum: {TEST_PHONE_NL}")
    print(f"BE testnum: {TEST_PHONE_BE}")
    print(f"DE testnum: {TEST_PHONE_DE}")
    print("\n⚠️  Dit stuurt echte WhatsApp berichten!")
    confirm = input("Doorgaan? (ja/nee): ").strip().lower()
    if confirm != "ja":
        print("Geannuleerd.")
        sys.exit(0)

    checker = make_mock_checker()
    results = []
    passed = 0
    failed = 0

    # Basisdata
    monday = date(2026, 4, 7)       # Normale maandag
    friday = date(2026, 4, 3)       # Vrijdag
    before_koningsdag = date(2026, 4, 26)   # Dag voor Koningsdag
    before_21_juli = date(2026, 7, 20)      # Dag voor BE nationale feestdag
    before_de_unity = date(2026, 10, 1)     # Donderdag voor 2 okt (vrij voor 3 okt weekend)
    before_pasen = date(2026, 4, 5)         # Dag voor Paasmaandag

    tests = [
        # ── NL scenarios ────────────────────────────────────────────────────
        ("NL - Normaal werkdag (morgen)", TEST_PHONE_NL, "NL",
         checker.get_holiday_scenario(monday, "NL"), monday),

        ("NL - Vrijdag → maandag", TEST_PHONE_NL, "NL",
         checker.get_holiday_scenario(friday, "NL"), friday),

        ("NL - Dag voor Koningsdag", TEST_PHONE_NL, "NL",
         checker.get_holiday_scenario(before_koningsdag, "NL"), before_koningsdag),

        ("NL - Dag voor Paasmaandag (gedeelde feestdag)", TEST_PHONE_NL, "NL",
         checker.get_holiday_scenario(before_pasen, "NL"), before_pasen),

        # ── BE scenarios ────────────────────────────────────────────────────
        ("BE - Normaal werkdag (morgen)", TEST_PHONE_BE, "BE",
         checker.get_holiday_scenario(monday, "BE"), monday),

        ("BE - Dag voor Koningsdag (NL feestdag, BE werkdag)", TEST_PHONE_BE, "BE",
         checker.get_holiday_scenario(before_koningsdag, "BE"), before_koningsdag),

        ("BE - Dag voor Nationale Feestdag (21 juli)", TEST_PHONE_BE, "BE",
         checker.get_holiday_scenario(before_21_juli, "BE"), before_21_juli),

        ("BE - Dag voor Paasmaandag (beide landen feestdag)", TEST_PHONE_BE, "BE",
         checker.get_holiday_scenario(before_pasen, "BE"), before_pasen),

        # ── DE scenarios ────────────────────────────────────────────────────
        ("DE - Normaal werkdag (morgen)", TEST_PHONE_DE, "DE",
         checker.get_holiday_scenario(monday, "DE"), monday),

        ("DE - Vrijdag → maandag", TEST_PHONE_DE, "DE",
         checker.get_holiday_scenario(friday, "DE"), friday),

        ("DE - Dag voor Koningsdag (NL feestdag, DE werkdag)", TEST_PHONE_DE, "DE",
         checker.get_holiday_scenario(before_koningsdag, "DE"), before_koningsdag),

        ("DE - 2 okt (vrijdag voor 3-okt-weekend)", TEST_PHONE_DE, "DE",
         checker.get_holiday_scenario(before_de_unity, "DE"), before_de_unity),

        ("DE - Dag voor Paasmaandag (beide landen feestdag)", TEST_PHONE_DE, "DE",
         checker.get_holiday_scenario(before_pasen, "DE"), before_pasen),

        # ── Speciale tekens test ─────────────────────────────────────────────
        ("DE - Speciale tekens (ü, ä, ö, ß, é)", TEST_PHONE_DE, "DE",
         checker.get_holiday_scenario(monday, "DE"), monday),
    ]

    for label, phone, language, scenario, today in tests:
        success = send_test(label, phone, language, scenario, today)
        results.append((label, success))
        if success:
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTAAT: {passed} verstuurd, {failed} mislukt")
    print("=" * 60)
    for label, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {label}")

    return failed == 0


if __name__ == "__main__":
    success = run_live_tests()
    sys.exit(0 if success else 1)
