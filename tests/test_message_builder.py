"""
test_message_builder.py - Tests voor berichtopbouw
Test alle scenario's voor NL, BE en DE.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from message_builder import build_message, detect_language, get_greeting, format_date_nl, format_date_de


def test_greetings():
    """Test dagdeel begroetingen op basis van uur."""
    assert get_greeting("NL", 8) == "Goedemorgen"
    assert get_greeting("NL", 11) == "Goedemorgen"
    assert get_greeting("NL", 12) == "Goedemiddag"
    assert get_greeting("NL", 13) == "Goedemiddag"
    assert get_greeting("NL", 17) == "Goedemiddag"
    assert get_greeting("NL", 18) == "Goedenavond"
    assert get_greeting("NL", 22) == "Goedenavond"
    assert get_greeting("BE", 13) == "Goedemiddag"
    assert get_greeting("DE", 8) == "Guten Morgen"
    assert get_greeting("DE", 13) == "Guten Mittag"
    assert get_greeting("DE", 20) == "Guten Abend"
    print("✅ test_greetings geslaagd")


def test_date_formatting():
    """Test datumopmaak per land."""
    d = date(2026, 4, 7)
    assert format_date_nl(d) == "07-04"
    assert format_date_de(d) == "07.04.2026"

    d2 = date(2026, 12, 25)
    assert format_date_nl(d2) == "25-12"
    assert format_date_de(d2) == "25.12.2026"
    print("✅ test_date_formatting geslaagd")


def test_language_detection():
    """Test taaldetectie op basis van telefoonnummer en landcode."""
    assert detect_language("+31612345678") == "NL"
    assert detect_language("+32498123456") == "BE"
    assert detect_language("+4917612345678") == "DE"
    assert detect_language("", "NL") == "NL"
    assert detect_language("", "BE") == "BE"
    assert detect_language("", "DE") == "DE"
    assert detect_language("", "NEDERLAND") == "NL"
    assert detect_language("", "DEUTSCHLAND") == "DE"
    assert detect_language("", "") == "NL"  # Standaard NL
    print("✅ test_language_detection geslaagd")


def test_normal_scenario_nl():
    """Test normaal bericht NL - morgen gewone werkdag."""
    today = date(2026, 4, 6)  # Maandag
    tomorrow = date(2026, 4, 7)  # Dinsdag
    scenario = {
        "scenario": "normal",
        "next_workday": tomorrow,
        "nl_holiday_name": "",
        "tomorrow_is_weekend": False,
    }
    msg = build_message("NL", scenario, today, hour=13)
    assert "Goedemiddag" in msg
    assert "morgen (07-04)" in msg
    assert "mestbakken" in msg
    assert "Miedema" in msg
    print(f"✅ test_normal_scenario_nl geslaagd\n   Bericht: {repr(msg[:80])}")


def test_normal_scenario_friday_nl():
    """Test normaal bericht NL - vrijdag → maandag."""
    today = date(2026, 4, 3)   # Vrijdag
    monday = date(2026, 4, 6)  # Maandag
    scenario = {
        "scenario": "normal",
        "next_workday": monday,
        "nl_holiday_name": "",
        "tomorrow_is_weekend": True,
    }
    msg = build_message("NL", scenario, today, hour=13)
    assert "maandag (06-04)" in msg
    assert "morgen" not in msg
    print(f"✅ test_normal_scenario_friday_nl geslaagd\n   Bericht: {repr(msg[:80])}")


def test_nl_holiday_nl_customer():
    """Test NL feestdag bericht voor NL klant (Koningsdag)."""
    today = date(2026, 4, 26)   # Zondag voor Koningsdag
    next_wd = date(2026, 4, 28) # Dinsdag na Koningsdag
    scenario = {
        "scenario": "nl_holiday",
        "next_workday": next_wd,
        "nl_holiday_name": "Koningsdag",
        "tomorrow_is_weekend": False,
    }
    msg = build_message("NL", scenario, today, hour=13)
    assert "dinsdag (28-04)" in msg
    assert "mestbakken" in msg
    print(f"✅ test_nl_holiday_nl_customer geslaagd\n   Bericht: {repr(msg[:100])}")


def test_nl_holiday_be_customer():
    """Test NL feestdag bericht voor BE klant (Koningsdag)."""
    today = date(2026, 4, 26)
    next_wd = date(2026, 4, 28)
    scenario = {
        "scenario": "nl_holiday",
        "next_workday": next_wd,
        "nl_holiday_name": "Koningsdag",
        "tomorrow_is_weekend": False,
    }
    msg = build_message("BE", scenario, today, hour=13)
    assert "Koningsdag" in msg
    assert "rijden wij morgen niet" in msg
    assert "dinsdag (28-04)" in msg
    print(f"✅ test_nl_holiday_be_customer geslaagd\n   Bericht: {repr(msg[:120])}")


def test_nl_holiday_de_customer():
    """Test NL feestdag bericht voor DE klant (Koningsdag) - Duits."""
    today = date(2026, 4, 26)
    next_wd = date(2026, 4, 28)
    scenario = {
        "scenario": "nl_holiday",
        "next_workday": next_wd,
        "nl_holiday_name": "Koningsdag",
        "tomorrow_is_weekend": False,
    }
    msg = build_message("DE", scenario, today, hour=13)
    assert "Koningsdag" in msg
    assert "fahren wir morgen nicht" in msg
    assert "Dienstag (28.04.2026)" in msg
    assert "Kisten" in msg
    print(f"✅ test_nl_holiday_de_customer geslaagd\n   Bericht: {repr(msg[:120])}")


def test_country_holiday_be():
    """Test BE feestdag bericht zonder naam (bijv. 21 juli)."""
    today = date(2026, 7, 20)
    scenario = {
        "scenario": "country_holiday",
        "next_workday": date(2026, 7, 21),
        "nl_holiday_name": "",
        "country_holiday_name": "",
        "tomorrow_is_weekend": False,
    }
    msg = build_message("BE", scenario, today, hour=13)
    assert "i.v.m. feestdag?" in msg
    assert "Heeft u morgen mestbakken" in msg
    assert "Miedema" in msg
    print(f"✅ test_country_holiday_be geslaagd\n   Bericht: {repr(msg[:120])}")


def test_country_holiday_be_with_name():
    """Test BE feestdag bericht met feestdagnaam (Allerheiligen)."""
    today = date(2026, 10, 31)
    scenario = {
        "scenario": "country_holiday",
        "next_workday": date(2026, 11, 1),
        "nl_holiday_name": "",
        "country_holiday_name": "Allerheiligen",
        "tomorrow_is_weekend": False,
    }
    msg = build_message("BE", scenario, today, hour=13)
    assert "feestdag (Allerheiligen)" in msg
    assert "Heeft u morgen mestbakken" in msg
    print(f"✅ test_country_holiday_be_with_name geslaagd\n   Bericht: {repr(msg[:120])}")


def test_country_holiday_de():
    """Test DE feestdag bericht zonder naam."""
    today = date(2026, 10, 2)
    scenario = {
        "scenario": "country_holiday",
        "next_workday": date(2026, 10, 3),
        "nl_holiday_name": "",
        "country_holiday_name": "",
        "tomorrow_is_weekend": False,
    }
    msg = build_message("DE", scenario, today, hour=13)
    assert "Feiertags?" in msg
    assert "Kisten" in msg
    assert "Miedema" in msg
    print(f"✅ test_country_holiday_de geslaagd\n   Bericht: {repr(msg[:120])}")


def test_country_holiday_de_with_name():
    """Test DE feestdag bericht met feestdagnaam (Fronleichnam)."""
    today = date(2026, 6, 3)
    scenario = {
        "scenario": "country_holiday",
        "next_workday": date(2026, 6, 4),
        "nl_holiday_name": "",
        "country_holiday_name": "Fronleichnam",
        "tomorrow_is_weekend": False,
    }
    msg = build_message("DE", scenario, today, hour=13)
    assert "Feiertags (Fronleichnam)?" in msg
    assert "Kisten" in msg
    print(f"✅ test_country_holiday_de_with_name geslaagd\n   Bericht: {repr(msg[:120])}")


def test_both_holiday_nl():
    """Test beide landen feestdag - NL klant (bijv. Paasmaandag)."""
    today = date(2026, 4, 5)   # Zondag voor Paasmaandag
    next_wd = date(2026, 4, 7) # Dinsdag
    scenario = {
        "scenario": "both_holiday",
        "next_workday": next_wd,
        "nl_holiday_name": "Paasmaandag",
        "tomorrow_is_weekend": False,
    }
    msg = build_message("NL", scenario, today, hour=13)
    assert "dinsdag (07-04)" in msg
    assert "mestbakken" in msg
    print(f"✅ test_both_holiday_nl geslaagd\n   Bericht: {repr(msg[:100])}")


def test_special_characters():
    """Test dat speciale tekens correct in het bericht zitten."""
    today = date(2026, 4, 6)
    tomorrow = date(2026, 4, 7)
    scenario = {
        "scenario": "normal",
        "next_workday": tomorrow,
        "nl_holiday_name": "",
        "tomorrow_is_weekend": False,
    }
    # NL bericht moet mestbakken bevatten
    msg_nl = build_message("NL", scenario, today, hour=13)
    assert "mestbakken" in msg_nl
    assert "vriendelijke groet" in msg_nl
    # DE bericht bevat Grüßen (ü en ß)
    msg_de = build_message("DE", scenario, today, hour=13)
    assert "Grüßen" in msg_de
    assert "Kisten" in msg_de
    # BE feestdag bericht bevat i.v.m.
    scenario_hol = {
        "scenario": "country_holiday",
        "next_workday": tomorrow,
        "nl_holiday_name": "",
        "tomorrow_is_weekend": False,
    }
    msg_be = build_message("BE", scenario_hol, today, hour=13)
    assert "i.v.m." in msg_be
    print("✅ test_special_characters geslaagd")


def test_weekend_scenario():
    """Test dat weekend correct afgehandeld wordt (morgen = zaterdag)."""
    today = date(2026, 4, 3)   # Vrijdag
    monday = date(2026, 4, 6)  # Maandag
    scenario = {
        "scenario": "normal",
        "next_workday": monday,
        "nl_holiday_name": "",
        "tomorrow_is_weekend": True,
    }
    # 3 oktober 2026 = zaterdag, feestdag DE maar weekend
    msg = build_message("DE", scenario, today, hour=13)
    assert "Montag (06.04.2026)" in msg
    assert "Feiertag" not in msg  # Geen feestdagvariant want weekend
    print(f"✅ test_weekend_scenario geslaagd\n   Bericht: {repr(msg[:100])}")


def run_all_tests():
    print("\n" + "=" * 60)
    print("TESTS: message_builder.py")
    print("=" * 60)
    tests = [
        test_greetings,
        test_date_formatting,
        test_language_detection,
        test_normal_scenario_nl,
        test_normal_scenario_friday_nl,
        test_nl_holiday_nl_customer,
        test_nl_holiday_be_customer,
        test_nl_holiday_de_customer,
        test_country_holiday_be,
        test_country_holiday_be_with_name,
        test_country_holiday_de,
        test_country_holiday_de_with_name,
        test_both_holiday_nl,
        test_special_characters,
        test_weekend_scenario,
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
