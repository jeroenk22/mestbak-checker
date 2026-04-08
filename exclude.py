"""
exclude.py - Beheer van uitgesloten telefoonnummers
Auto-exclude na MAX_FAILURES_BEFORE_EXCLUDE mislukkingen.
"""

import json
import os
from datetime import datetime
from logger import logger
from config import EXCLUDED_FILE, FAILURE_COUNTS_FILE, MAX_FAILURES_BEFORE_EXCLUDE, DATA_DIR

# Zorg dat data map bestaat
os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(filepath: str, default) -> dict | list:
    """Laad JSON bestand, geef default terug als het niet bestaat."""
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Fout bij laden {filepath}: {e}")
        return default


def _save_json(filepath: str, data: dict | list):
    """Sla data op als JSON bestand."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError as e:
        logger.error(f"Fout bij opslaan {filepath}: {e}")


def load_excluded() -> dict:
    """Laad de excludelijst. Geeft dict terug: {nummer: {info}}."""
    return _load_json(EXCLUDED_FILE, {})


def load_failure_counts() -> dict:
    """Laad de failure tellers. Geeft dict terug: {nummer: {count, last_failure, ...}}."""
    return _load_json(FAILURE_COUNTS_FILE, {})


def is_excluded(phone: str) -> bool:
    """Controleer of een nummer op de excludelijst staat."""
    excluded = load_excluded()
    return phone in excluded


def register_failure(phone: str, customer_info: dict) -> bool:
    """
    Registreer een mislukte verzending voor een nummer.
    Geeft True terug als het nummer nu automatisch is uitgesloten.
    """
    counts = load_failure_counts()

    if phone not in counts:
        counts[phone] = {
            "count": 0,
            "first_failure": datetime.now().isoformat(),
            "last_failure": None,
            "customer_info": customer_info,
        }

    counts[phone]["count"] += 1
    counts[phone]["last_failure"] = datetime.now().isoformat()
    counts[phone]["customer_info"] = customer_info  # Altijd bijwerken

    _save_json(FAILURE_COUNTS_FILE, counts)

    logger.info(
        f"Failure geregistreerd voor {phone} "
        f"({counts[phone]['count']}/{MAX_FAILURES_BEFORE_EXCLUDE})"
    )

    # Auto-exclude bij drempel
    if counts[phone]["count"] >= MAX_FAILURES_BEFORE_EXCLUDE:
        auto_exclude(phone, customer_info, counts[phone]["count"])
        return True

    return False


def auto_exclude(phone: str, customer_info: dict, failure_count: int):
    """Voeg een nummer automatisch toe aan de excludelijst."""
    excluded = load_excluded()

    excluded[phone] = {
        "auto_excluded": True,
        "excluded_at": datetime.now().isoformat(),
        "failure_count": failure_count,
        "sj_order_id": customer_info.get("sj_order_id", ""),
        "name": customer_info.get("name", ""),
        "street": customer_info.get("street", ""),
        "zip": customer_info.get("zip", ""),
        "city": customer_info.get("city", ""),
        "country": customer_info.get("country", ""),
        # Commentaar voor leesbaarheid
        "_comment": (
            f"{customer_info.get('name', '')} | "
            f"{customer_info.get('street', '')} | "
            f"{customer_info.get('zip', '')} "
            f"{customer_info.get('city', '')} | "
            f"{customer_info.get('country', '')}"
        ),
    }

    _save_json(EXCLUDED_FILE, excluded)

    logger.warning(
        f"AUTO-EXCLUDE: {phone} na {failure_count} mislukkingen | "
        f"{customer_info.get('name', '')} | "
        f"{customer_info.get('city', '')}"
    )


def register_success(phone: str):
    """Reset de failure teller bij succesvolle verzending."""
    counts = load_failure_counts()
    if phone in counts:
        old_count = counts[phone]["count"]
        counts[phone]["count"] = 0
        counts[phone]["last_success"] = datetime.now().isoformat()
        _save_json(FAILURE_COUNTS_FILE, counts)
        if old_count > 0:
            logger.info(f"Failure teller gereset voor {phone} (was {old_count})")


def get_failure_count(phone: str) -> int:
    """Geef het huidige aantal failures voor een nummer."""
    counts = load_failure_counts()
    return counts.get(phone, {}).get("count", 0)


def manually_exclude(phone: str, customer_info: dict, reason: str = "Handmatig uitgesloten"):
    """Voeg een nummer handmatig toe aan de excludelijst."""
    excluded = load_excluded()
    excluded[phone] = {
        "auto_excluded": False,
        "excluded_at": datetime.now().isoformat(),
        "reason": reason,
        "sj_order_id": customer_info.get("sj_order_id", ""),
        "name": customer_info.get("name", ""),
        "street": customer_info.get("street", ""),
        "zip": customer_info.get("zip", ""),
        "city": customer_info.get("city", ""),
        "country": customer_info.get("country", ""),
        "_comment": (
            f"{customer_info.get('name', '')} | "
            f"{customer_info.get('street', '')} | "
            f"{customer_info.get('zip', '')} "
            f"{customer_info.get('city', '')} | "
            f"{customer_info.get('country', '')}"
        ),
    }
    _save_json(EXCLUDED_FILE, excluded)
    logger.info(f"Handmatig uitgesloten: {phone} | {reason}")
