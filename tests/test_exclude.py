"""
test_exclude.py - Tests voor handmatige en automatische nummer-excludes.
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exclude import is_excluded, manually_exclude


def test_is_excluded_matches_normalized_database_variants():
    """Een nette +31 entry matcht verschillende DB-schrijfwijzen."""
    excluded = {
        "+31612345678": {
            "auto_excluded": False,
            "reason": "Handmatig uitgesloten",
        }
    }

    with patch("exclude.load_excluded", return_value=excluded):
        assert is_excluded("+31612345678") is True
        assert is_excluded("0612345678") is True
        assert is_excluded("06-12345678") is True
        assert is_excluded("06 12 34 5678") is True

    print("✅ test_is_excluded_matches_normalized_database_variants geslaagd")


def test_is_excluded_normalizes_excludelist_keys_too():
    """Ook rommelige keys in excluded_numbers.json worden genormaliseerd vergeleken."""
    excluded = {
        "06 12 34 5678": {
            "auto_excluded": False,
            "reason": "Handmatig uitgesloten",
        }
    }

    with patch("exclude.load_excluded", return_value=excluded):
        assert is_excluded("+31612345678") is True

    print("✅ test_is_excluded_normalizes_excludelist_keys_too geslaagd")


def test_manually_exclude_stores_normalized_number():
    """Handmatig toevoegen bewaart het nummer genormaliseerd als JSON-key."""
    saved = {}

    def capture_save(_filepath, data):
        saved.update(data)

    with patch("exclude.load_excluded", return_value={}), \
         patch("exclude._save_json", side_effect=capture_save):
        manually_exclude(
            "06 12 34 5678",
            {"name": "Klant", "city": "Aalten"},
            reason="Niet appen",
        )

    assert "+31612345678" in saved
    assert "06 12 34 5678" not in saved
    assert saved["+31612345678"]["reason"] == "Niet appen"

    print("✅ test_manually_exclude_stores_normalized_number geslaagd")


def run_all_tests():
    print("\n" + "=" * 60)
    print("TESTS: exclude.py")
    print("=" * 60)
    tests = [
        test_is_excluded_matches_normalized_database_variants,
        test_is_excluded_normalizes_excludelist_keys_too,
        test_manually_exclude_stores_normalized_number,
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
