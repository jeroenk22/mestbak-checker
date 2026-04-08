"""
test_utils.py - Tests voor telefoonnummer normalisatie
Test alle NL, BE en DE nummerformaten.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import normalize_phone, get_country_from_phone


def test_nl_mobiel():
    """Test Nederlandse mobiele nummers."""
    assert normalize_phone("0612345678") == "+31612345678"
    assert normalize_phone("06 12 34 56 78") == "+31612345678"
    assert normalize_phone("06-12-34-56-78") == "+31612345678"
    assert normalize_phone("+31612345678") == "+31612345678"
    assert normalize_phone("0031612345678") == "+31612345678"
    assert normalize_phone("316xxxxxxxx") == ""  # Te kort
    print("✅ test_nl_mobiel geslaagd")


def test_nl_vast():
    """Test Nederlandse vaste nummers inclusief 085/088."""
    assert normalize_phone("0850001234") == "+31850001234"
    assert normalize_phone("0880001234") == "+31880001234"
    assert normalize_phone("0101234567") == "+31101234567"
    assert normalize_phone("0201234567") == "+31201234567"
    print("✅ test_nl_vast geslaagd")


def test_be_mobiel():
    """Test Belgische mobiele nummers."""
    assert normalize_phone("0498123456") == "+32498123456"
    assert normalize_phone("+32498123456") == "+32498123456"
    assert normalize_phone("0032498123456") == "+32498123456"
    assert normalize_phone("32498123456") == "+32498123456"
    print("✅ test_be_mobiel geslaagd")


def test_be_vast():
    """Test Belgische vaste nummers."""
    assert normalize_phone("092123456") == "+3292123456"
    assert normalize_phone("021234567") == "+3221234567"
    print("✅ test_be_vast geslaagd")


def test_de_mobiel():
    """Test Duitse mobiele nummers."""
    assert normalize_phone("01512345678") == "+491512345678"
    assert normalize_phone("01612345678") == "+491612345678"
    assert normalize_phone("01712345678") == "+491712345678"
    assert normalize_phone("+4917612345678") == "+4917612345678"
    assert normalize_phone("004917612345678") == "+4917612345678"
    print("✅ test_de_mobiel geslaagd")


def test_de_vast():
    """Test Duitse vaste nummers."""
    assert normalize_phone("02161234567") == "+492161234567"
    assert normalize_phone("02511234567") == "+492511234567"
    print("✅ test_de_vast geslaagd")


def test_apostrof_prefix():
    """Test dat apostrof prefix (uit SQL query) correct gestript wordt."""
    assert normalize_phone("'0612345678") == "+31612345678"
    assert normalize_phone("'0498123456") == "+32498123456"
    assert normalize_phone("'+31612345678") == "+31612345678"
    print("✅ test_apostrof_prefix geslaagd")


def test_ongeldige_nummers():
    """Test dat ongeldige nummers lege string geven."""
    assert normalize_phone("") == ""
    assert normalize_phone(None) == ""
    assert normalize_phone("12345") == ""  # Te kort
    assert normalize_phone("abcdefghij") == ""
    print("✅ test_ongeldige_nummers geslaagd")


def test_country_detection():
    """Test landdetectie op basis van genormaliseerd nummer."""
    assert get_country_from_phone("+31612345678") == "NL"
    assert get_country_from_phone("+32498123456") == "BE"
    assert get_country_from_phone("+4917612345678") == "DE"
    assert get_country_from_phone("+31850001234") == "NL"  # 085 = NL
    assert get_country_from_phone("") == "NL"  # Standaard NL
    print("✅ test_country_detection geslaagd")


def test_spaties_en_speciale_tekens():
    """Test nummers met spaties, streepjes en haakjes."""
    assert normalize_phone("06 12 34 56 78") == "+31612345678"
    assert normalize_phone("06-12-34-56-78") == "+31612345678"
    assert normalize_phone("+31 6 12 34 56 78") == "+31612345678"
    print("✅ test_spaties_en_speciale_tekens geslaagd")


def test_excluded_notation():
    """Test herkenning van uitsluitingsnotaties."""
    from utils import is_excluded_notation

    # nul-notatie
    excl, reden = is_excluded_notation("nul-zes 43091465")
    assert excl and reden == "nul-notatie"

    excl, reden = is_excluded_notation("nul6-27856048")
    assert excl and reden == "nul-notatie"

    excl, reden = is_excluded_notation("NUL-ZES 12345678")
    assert excl and reden == "nul-notatie"

    # alleen spoed
    excl, reden = is_excluded_notation("0031653301960 (alleen spoed)")
    assert excl and reden == "alleen spoed"

    excl, reden = is_excluded_notation("06123456 (Alleen Spoed)")
    assert excl and reden == "alleen spoed"

    # Geldige nummers
    excl, _ = is_excluded_notation("0612345678")
    assert not excl

    excl, _ = is_excluded_notation("+31612345678")
    assert not excl

    excl, _ = is_excluded_notation("")
    assert not excl

    print("✅ test_excluded_notation geslaagd")


def run_all_tests():
    print("\n" + "=" * 60)
    print("TESTS: utils.py (telefoonnummer normalisatie)")
    print("=" * 60)
    tests = [
        test_nl_mobiel,
        test_nl_vast,
        test_be_mobiel,
        test_be_vast,
        test_de_mobiel,
        test_de_vast,
        test_apostrof_prefix,
        test_ongeldige_nummers,
        test_country_detection,
        test_spaties_en_speciale_tekens,
        test_excluded_notation,
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
