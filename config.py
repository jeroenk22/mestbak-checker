"""
config.py - Configuratie en instellingen voor mestbak-checker
Alle instelbare variabelen staan hier. Pas dit aan naar wens.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ─── Tijdinstellingen ────────────────────────────────────────────────────────
SEND_HOUR = 13          # Uur waarop het script normaal draait (bepaalt dagdeel)
MAX_CUTOFF_HOUR = 16    # Maximaal uur waarop script nog mag starten
MAX_CUTOFF_MINUTE = 30  # Maximale minuut waarop script nog mag starten

# ─── Dagdeel grenzen ─────────────────────────────────────────────────────────
# Ochtend: 00:00 - 11:59
# Middag:  12:00 - 17:59
# Avond:   18:00 - 23:59
MIDDAG_START = 12
AVOND_START = 18

# ─── Vertraging tussen berichten (spam preventie) ────────────────────────────
DELAY_BETWEEN_MESSAGES = 4  # seconden tussen elk WhatsApp bericht

# ─── TextMeBot instellingen ──────────────────────────────────────────────────
TEXTMEBOT_API_KEY = os.getenv("TEXTMEBOT_API_KEY", "")
TEXTMEBOT_API_URL = "https://api.textmebot.com/send.php"
TEXTMEBOT_TIMEOUT = 10  # seconden timeout per API call

# ─── Eigen nummer voor samenvattingsberichten ────────────────────────────────
SUMMARY_PHONE = os.getenv("SUMMARY_PHONE", "")  # bijv. +31612345678

# ─── Database instellingen ───────────────────────────────────────────────────
DB_SERVER = os.getenv("DB_SERVER", "")
DB_NAME = os.getenv("DB_NAME", "")
DB_CLIENT_NO = int(os.getenv("DB_CLIENT_NO") or 0)
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

# ─── Bestandspaden ───────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
EXCLUDED_FILE = os.path.join(DATA_DIR, "excluded_numbers.json")
FAILURE_COUNTS_FILE = os.path.join(DATA_DIR, "failure_counts.json")

# ─── Auto-exclude drempel ────────────────────────────────────────────────────
MAX_FAILURES_BEFORE_EXCLUDE = 3  # aantal mislukkingen voor auto-exclude

# ─── Logbestanden bewaren ────────────────────────────────────────────────────
LOG_RETENTION_DAYS = 90  # aantal dagen logbestanden bewaren

# ─── Testmodus ───────────────────────────────────────────────────────────────
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
TEST_PHONE_NL = os.getenv("TEST_PHONE_NL", "")   # bijv. +31612345678
TEST_PHONE_BE = os.getenv("TEST_PHONE_BE", "")   # bijv. +32498123456
TEST_PHONE_DE = os.getenv("TEST_PHONE_DE", "")   # bijv. +4917612345678

# ─── Nager.Date API ──────────────────────────────────────────────────────────
NAGER_API_URL = "https://date.nager.at/api/v3/PublicHolidays"
NAGER_TIMEOUT = 10

# ─── Landen / regio's voor feestdagen ───────────────────────────────────────
HOLIDAY_COUNTRIES = {
    "NL": "NL",
    "BE": "BE",
    "DE_NRW": "DE",        # Nordrhein-Westfalen
    "DE_NDS": "DE",        # Niedersachsen
}

DE_REGIONS = ["DE-NW", "DE-NI"]  # NRW en Niedersachsen county codes bij Nager


def validate_config() -> list:
    """Controleer of alle verplichte configuratievariabelen aanwezig zijn.
    Geeft een lijst van ontbrekende variabelen terug."""
    missing = []
    if not TEXTMEBOT_API_KEY:
        missing.append("TEXTMEBOT_API_KEY")
    if not SUMMARY_PHONE:
        missing.append("SUMMARY_PHONE")
    if not DB_SERVER:
        missing.append("DB_SERVER")
    if TEST_MODE:
        if not TEST_PHONE_NL:
            missing.append("TEST_PHONE_NL")
        if not TEST_PHONE_BE:
            missing.append("TEST_PHONE_BE")
        if not TEST_PHONE_DE:
            missing.append("TEST_PHONE_DE")
    return missing
