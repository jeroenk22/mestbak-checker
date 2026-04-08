"""
test_holidays.py - Tests voor feestdagenlogica
Simuleert alle feestdagscenario's zonder echte API calls.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from unittest.mock import patch, MagicMock
from holidays import HolidayChecker, _is_holiday_for_date, get_public_holidays


# ─── Mock feestdagendata ─────────────────────────────────────────────────────

NL_HOLIDAYS_2026 = [
    {"date": "2026-01-01", "localName": "Nieuwjaarsdag", "name": "New Year's Day",
     "types": ["Public"], "counties": None},
    {"date": "2026-04-06", "localName": "Paasmaandag", "name": "Easter Monday",
     "types": ["Public"], "counties": None},
    {"date": "2026-04-27", "localName": "Koningsdag", "name": "King's Day",
     "types": ["Public"], "counties": None},
    {"date": "2026-05-14", "localName": "Hemelvaartsdag", "name": "Ascension Day",
     "types": ["Public"], "counties": None},
    {"date": "2026-05-25", "localName": "Pinkstermaandag", "name": "Whit Monday",
     "types": ["Public"], "counties": None},
    {"date": "2026-12-25", "localName": "Eerste Kerstdag", "name": "Christmas Day",
     "types": ["Public"], "counties": None},
    {"date": "2026-12-26", "localName": "Tweede Kerstdag", "name": "Second Day of Christmas",
     "types": ["Public"], "counties": None},
]

BE_HOLIDAYS_2026 = [
    {"date": "2026-01-01", "localName": "Nieuwjaarsdag", "name": "New Year's Day",
     "types": ["Public"], "counties": None},
    {"date": "2026-04-06", "localName": "Paasmaandag", "name": "Easter Monday",
     "types": ["Public"], "counties": None},
    {"date": "2026-05-01", "localName": "Dag van de Arbeid", "name": "Labour Day",
     "types": ["Public"], "counties": None},
    {"date": "2026-05-14", "localName": "O.L.H. Hemelvaart", "name": "Ascension Day",
     "types": ["Public"], "counties": None},
    {"date": "2026-05-25", "localName": "Pinkstermaandag", "name": "Whit Monday",
     "types": ["Public"], "counties": None},
    {"date": "2026-07-21", "localName": "Nationale feestdag", "name": "National Day",
     "types": ["Public"], "counties": None},
    {"date": "2026-11-11", "localName": "Wapenstilstand", "name": "Armistice Day",
     "types": ["Public"], "counties": None},
    {"date": "2026-12-25", "localName": "Kerstmis", "name": "Christmas Day",
     "types": ["Public"], "counties": None},
]

DE_HOLIDAYS_2026 = [
    {"date": "2026-01-01", "localName": "Neujahr", "name": "New Year's Day",
     "types": ["Public"], "counties": None},  # Heel Duitsland
    {"date": "2026-04-06", "localName": "Ostermontag", "name": "Easter Monday",
     "types": ["Public"], "counties": ["DE-NW", "DE-NI", "DE-BY", "DE-BW"]},
    {"date": "2026-05-01", "localName": "Tag der Arbeit", "name": "Labour Day",
     "types": ["Public"], "counties": None},
    {"date": "2026-10-03", "localName": "Tag der Deutschen Einheit",
     "name": "German Unity Day", "types": ["Public"], "counties": None},
    {"date": "2026-12-25", "localName": "Erster Weihnachtstag", "name": "Christmas Day",
     "types": ["Public"], "counties": None},
    {"date": "2026-12-26", "localName": "Zweiter Weihnachtstag",
     "name": "Second Day of Christmas", "types": ["Public"], "counties": None},
    # NRW-specifieke feestdag
    {"date": "2026-11-01", "localName": "Allerheiligen", "name": "All Saints' Day",
     "types": ["Public"], "counties": ["DE-NW", "DE-BY", "DE-BW", "DE-RP", "DE-SL"]},
]


def make_mock_checker():
    """Maak een HolidayChecker met gemockte API data."""
    checker = HolidayChecker()
    checker._cache = {
        "NL_2026": NL_HOLIDAYS_2026,
        "BE_2026": BE_HOLIDAYS_2026,
        "DE_2026": DE_HOLIDAYS_2026,
    }
    return checker


# ─── Tests ───────────────────────────────────────────────────────────────────

def test_nl_holiday_detection():
    """Test detectie van Nederlandse feestdagen."""
    checker = make_mock_checker()
    is_hol, name = checker.is_nl_holiday(date(2026, 4, 27))
    assert is_hol, "Koningsdag moet herkend worden"
    assert "Koningsdag" in name

    is_hol, _ = checker.is_nl_holiday(date(2026, 4, 28))
    assert not is_hol, "28 april is geen feestdag"
    print("✅ test_nl_holiday_detection geslaagd")


def test_be_holiday_detection():
    """Test detectie van Belgische feestdagen."""
    checker = make_mock_checker()
    is_hol, name = checker.is_be_holiday(date(2026, 7, 21))
    assert is_hol, "21 juli moet herkend worden"

    is_hol, _ = checker.is_be_holiday(date(2026, 4, 27))
    assert not is_hol, "Koningsdag is geen BE feestdag"
    print("✅ test_be_holiday_detection geslaagd")


def test_de_holiday_detection_national():
    """Test detectie van nationale Duitse feestdagen (heel Duitsland)."""
    checker = make_mock_checker()
    is_hol, name = checker.is_de_holiday(date(2026, 10, 3))
    assert is_hol, "Dag van de Duitse Eenheid moet herkend worden"
    print("✅ test_de_holiday_detection_national geslaagd")


def test_de_holiday_detection_regional():
    """Test detectie van regionale DE feestdagen (NRW/Nds)."""
    checker = make_mock_checker()
    is_hol, name = checker.is_de_holiday(date(2026, 11, 1))
    assert is_hol, "Allerheiligen (NRW) moet herkend worden"
    print("✅ test_de_holiday_detection_regional geslaagd")


def test_scenario_normal():
    """Test normaal scenario - morgen gewone werkdag."""
    checker = make_mock_checker()
    today = date(2026, 4, 6)   # Maandag (zelf Paasmaandag maar test scenario)
    # Gebruik een gewone dag
    today = date(2026, 4, 7)   # Dinsdag
    sc = checker.get_holiday_scenario(today, "NL")
    assert sc["scenario"] == "normal"
    assert sc["next_workday"] == date(2026, 4, 8)
    print("✅ test_scenario_normal geslaagd")


def test_scenario_nl_holiday_nl_customer():
    """Test scenario dag voor Koningsdag voor NL klant."""
    checker = make_mock_checker()
    today = date(2026, 4, 26)  # Dag voor Koningsdag
    sc = checker.get_holiday_scenario(today, "NL")
    assert sc["scenario"] == "nl_holiday"
    assert sc["next_workday"] == date(2026, 4, 28)  # Dinsdag na Koningsdag
    assert "Koningsdag" in sc["nl_holiday_name"]
    print("✅ test_scenario_nl_holiday_nl_customer geslaagd")


def test_scenario_nl_holiday_be_customer():
    """Test scenario dag voor Koningsdag voor BE klant."""
    checker = make_mock_checker()
    today = date(2026, 4, 26)
    sc = checker.get_holiday_scenario(today, "BE")
    assert sc["scenario"] == "nl_holiday"  # NL feestdag, BE werkdag
    assert "Koningsdag" in sc["nl_holiday_name"]
    print("✅ test_scenario_nl_holiday_be_customer geslaagd")


def test_scenario_be_holiday_only():
    """Test scenario dag voor Belgische Nationale Feestdag (NL werkdag)."""
    checker = make_mock_checker()
    today = date(2026, 7, 20)  # Dag voor 21 juli
    sc = checker.get_holiday_scenario(today, "BE")
    assert sc["scenario"] == "country_holiday"
    print("✅ test_scenario_be_holiday_only geslaagd")


def test_scenario_de_holiday_only():
    """Test scenario dag voor Dag van de Duitse Eenheid (NL werkdag)."""
    checker = make_mock_checker()
    # 3 oktober 2026 = zaterdag → weekend scenario
    today = date(2026, 10, 1)  # Donderdag
    sc = checker.get_holiday_scenario(today, "DE")
    # Morgen (2 okt) is vrijdag, gewone werkdag voor DE
    assert sc["scenario"] == "normal"
    print("✅ test_scenario_de_holiday_only geslaagd (2 okt = normale vrijdag)")


def test_scenario_both_holiday():
    """Test scenario dag voor feestdag in zowel NL als BE (Paasmaandag)."""
    checker = make_mock_checker()
    today = date(2026, 4, 5)   # Zondag voor Paasmaandag
    sc = checker.get_holiday_scenario(today, "BE")
    assert sc["scenario"] == "both_holiday"
    assert sc["next_workday"] == date(2026, 4, 7)  # Dinsdag
    print("✅ test_scenario_both_holiday geslaagd")


def test_scenario_weekend():
    """Test scenario waarbij morgen weekend is."""
    checker = make_mock_checker()
    today = date(2026, 4, 10)  # Vrijdag
    sc = checker.get_holiday_scenario(today, "NL")
    assert sc["scenario"] == "normal"
    assert sc["tomorrow_is_weekend"] is True
    assert sc["next_workday"] == date(2026, 4, 13)  # Maandag
    print("✅ test_scenario_weekend geslaagd")


def test_scenario_de_unity_day_weekend():
    """Test 3 oktober als het in het weekend valt (DE feestdag)."""
    checker = make_mock_checker()
    # In 2026 valt 3 oktober op zaterdag
    today = date(2026, 10, 2)  # Vrijdag
    sc = checker.get_holiday_scenario(today, "DE")
    # Morgen = zaterdag = weekend, dus gewoon standaard bericht
    assert sc["tomorrow_is_weekend"] is True
    assert sc["scenario"] == "normal"
    print("✅ test_scenario_de_unity_day_weekend geslaagd")


def test_next_workday():
    """Test berekening eerstvolgende werkdag."""
    checker = make_mock_checker()
    # Vrijdag → Maandag
    assert checker.next_workday(date(2026, 4, 10), "NL") == date(2026, 4, 13)
    # Dag voor Koningsdag (maandag 26 apr) → dag erna (dinsdag 28 apr)
    assert checker.next_workday(date(2026, 4, 27), "NL") == date(2026, 4, 28)
    print("✅ test_next_workday geslaagd")


def test_get_public_holidays_filters_types():
    """get_public_holidays() behoudt alleen Public-feestdagen, filtert Bank/School weg."""
    raw = [
        {"date": "2026-01-01", "localName": "Nieuwjaarsdag", "types": ["Public"], "counties": None},
        {"date": "2026-12-26", "localName": "Tweede Kerstdag", "types": ["Bank"], "counties": None},
        {"date": "2026-09-01", "localName": "Schooldag", "types": ["School"], "counties": None},
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = raw
    mock_response.raise_for_status.return_value = None

    with patch("holidays.requests.get", return_value=mock_response):
        result = get_public_holidays("NL", 2026)

    assert len(result) == 1
    assert result[0]["localName"] == "Nieuwjaarsdag"
    print("✅ test_get_public_holidays_filters_types geslaagd")


def test_get_public_holidays_regional_counties():
    """get_public_holidays() geeft counties ongewijzigd terug; _is_holiday_for_date filtert op DE-XX."""
    raw = [
        {"date": "2026-11-01", "localName": "Allerheiligen", "types": ["Public"],
         "counties": ["DE-NW", "DE-BY", "DE-BW"]},   # NRW wel, Niedersachsen niet
        {"date": "2026-10-31", "localName": "Reformationstag", "types": ["Public"],
         "counties": ["DE-BY"]},                       # Geen NRW of NI
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = raw
    mock_response.raise_for_status.return_value = None

    with patch("holidays.requests.get", return_value=mock_response):
        holidays = get_public_holidays("DE", 2026)

    from config import DE_REGIONS  # ["DE-NW", "DE-NI"]
    # Allerheiligen: DE-NW matcht → feestdag voor onze regio
    is_hol, name = _is_holiday_for_date(date(2026, 11, 1), holidays, regions=DE_REGIONS)
    assert is_hol, "Allerheiligen (DE-NW) moet herkend worden"
    assert name == "Allerheiligen"

    # Reformationstag: alleen DE-BY, niet NRW/NI → geen feestdag voor onze regio
    is_hol2, _ = _is_holiday_for_date(date(2026, 10, 31), holidays, regions=DE_REGIONS)
    assert not is_hol2, "Reformationstag (alleen DE-BY) mag niet herkend worden"
    print("✅ test_get_public_holidays_regional_counties geslaagd")


def test_get_public_holidays_national_null_counties():
    """Feestdag met counties=None geldt landelijk, ook bij regiofilter."""
    raw = [
        {"date": "2026-10-03", "localName": "Tag der Deutschen Einheit",
         "types": ["Public"], "counties": None},
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = raw
    mock_response.raise_for_status.return_value = None

    with patch("holidays.requests.get", return_value=mock_response):
        holidays = get_public_holidays("DE", 2026)

    from config import DE_REGIONS
    is_hol, name = _is_holiday_for_date(date(2026, 10, 3), holidays, regions=DE_REGIONS)
    assert is_hol, "Nationale feestdag (counties=None) moet altijd matchen"
    assert name == "Tag der Deutschen Einheit"
    print("✅ test_get_public_holidays_national_null_counties geslaagd")


def run_all_tests():
    print("\n" + "=" * 60)
    print("TESTS: holidays.py")
    print("=" * 60)
    tests = [
        test_nl_holiday_detection,
        test_be_holiday_detection,
        test_de_holiday_detection_national,
        test_de_holiday_detection_regional,
        test_scenario_normal,
        test_scenario_nl_holiday_nl_customer,
        test_scenario_nl_holiday_be_customer,
        test_scenario_be_holiday_only,
        test_scenario_de_holiday_only,
        test_scenario_both_holiday,
        test_scenario_weekend,
        test_scenario_de_unity_day_weekend,
        test_next_workday,
        test_get_public_holidays_filters_types,
        test_get_public_holidays_regional_counties,
        test_get_public_holidays_national_null_counties,
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
