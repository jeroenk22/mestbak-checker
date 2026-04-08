"""
logger.py - Logging configuratie voor mestbak-checker
Dagelijkse rotating logfiles met automatische opruiming.
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from config import LOGS_DIR, LOG_RETENTION_DAYS

# Zorg dat logs map bestaat
os.makedirs(LOGS_DIR, exist_ok=True)


def setup_logger() -> logging.Logger:
    """Stel de logger in met dagelijkse rotating logfile en console output."""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOGS_DIR, f"mestbak-checker-{today}.log")

    logger = logging.getLogger("mestbak-checker")
    logger.setLevel(logging.DEBUG)

    # Voorkom dubbele handlers bij herhaalde aanroep
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Bestand handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler — forceer UTF-8 zodat emoji/speciale tekens niet als
    # mojibake verschijnen in een Windows cp1252 terminal of Task Scheduler log.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def cleanup_old_logs():
    """Verwijder logbestanden ouder dan LOG_RETENTION_DAYS dagen."""
    logger = logging.getLogger("mestbak-checker")
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)

    for filename in os.listdir(LOGS_DIR):
        if not filename.startswith("mestbak-checker-") or not filename.endswith(".log"):
            continue
        filepath = os.path.join(LOGS_DIR, filename)
        try:
            # Datum uit bestandsnaam halen: mestbak-checker-YYYY-MM-DD.log
            date_str = filename.replace("mestbak-checker-", "").replace(".log", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff:
                os.remove(filepath)
                logger.info(f"Oud logbestand verwijderd: {filename}")
        except (ValueError, OSError) as e:
            logger.warning(f"Kon logbestand niet verwerken: {filename} — {e}")


# Globale logger instantie
logger = setup_logger()
