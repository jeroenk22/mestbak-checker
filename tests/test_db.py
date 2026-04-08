"""
tests/test_db.py - Tests voor de SQL query laadlogica in db.py
Geen echte database verbinding nodig.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import _load_query


class TestLoadQuery(unittest.TestCase):

    def setUp(self):
        self.query = _load_query()

    def test_declare_datum_stripped(self):
        """DECLARE @Datum mag niet in de query zitten."""
        self.assertNotIn("DECLARE @Datum", self.query)

    def test_set_datum_stripped(self):
        """SET @Datum mag niet in de query zitten."""
        self.assertNotIn("SET @Datum", self.query)

    def test_declare_clientno_stripped(self):
        """DECLARE @ClientNo mag niet in de query zitten."""
        self.assertNotIn("DECLARE @ClientNo", self.query)

    def test_set_clientno_stripped(self):
        """SET @ClientNo mag niet in de query zitten."""
        self.assertNotIn("SET @ClientNo", self.query)

    def test_placeholders_present(self):
        """Drie ? placeholders verwacht: @Datum (2x) en @ClientNo (1x)."""
        self.assertEqual(self.query.count("?"), 3)

    def test_no_at_datum(self):
        """@Datum moet volledig vervangen zijn door ?."""
        self.assertNotIn("@Datum", self.query)

    def test_no_at_clientno(self):
        """@ClientNo moet volledig vervangen zijn door ?."""
        self.assertNotIn("@ClientNo", self.query)

    def test_no_hardcoded_database_name(self):
        """Geen hardcoded databasenaam in de query - verbinding regelt dit al."""
        self.assertNotIn("HARDCODED_DB_NAME", self.query)

    def test_no_hardcoded_client_number(self):
        """Geen hardcoded clientnummer 3582 in de query."""
        self.assertNotIn("3582", self.query)

    def test_select_present(self):
        """Query bevat een SELECT statement."""
        self.assertIn("SELECT", self.query)

    def test_order_by_present(self):
        """Query bevat ORDER BY."""
        self.assertIn("ORDER BY", self.query)

    def test_sj_order_id_filter(self):
        """Query filtert op SjOrderId (alleen vaste herhalende klanten)."""
        self.assertIn("SjOrderId IS NOT NULL", self.query)


def run_all_tests():
    print("\n" + "=" * 60)
    print("TESTS: db.py (SQL query laden)")
    print("=" * 60)

    passed = 0
    failed = 0

    suite = unittest.TestLoader().loadTestsFromTestCase(TestLoadQuery)
    for test in suite:
        name = test._testMethodName
        try:
            test.setUp()
            getattr(test, name)()
            print(f"✅ {name} geslaagd")
            passed += 1
        except AssertionError as e:
            print(f"❌ {name} MISLUKT: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {name} FOUT: {e}")
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
