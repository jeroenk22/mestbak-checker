"""
utils.py - Hulpfuncties voor mestbak-checker
Telefoonnummer normalisatie en overige utilities.
"""

import re
from logger import logger


def is_excluded_notation(number: str) -> tuple[bool, str]:
    """
    Controleer of een nummer een bewuste uitsluitingsnotatie is.
    Geeft (is_excluded, reden) terug.

    Uitsluitingsnotaties:
    - Begint met 'nul' (bijv. 'nul-zes 43091465', 'nul6-27856048')
    - Bevat '(alleen spoed)'
    """
    if not number:
        return False, ""

    normalized_lower = number.strip().lower()

    if normalized_lower.startswith("nul"):
        return True, "nul-notatie"

    if "alleen spoed" in normalized_lower:
        return True, "alleen spoed"

    return False, ""


def normalize_phone(number: str) -> str:
    """
    Normaliseer een telefoonnummer naar E.164 formaat (+31612345678).
    Ondersteunt NL, BE en DE nummers.
    Geeft lege string terug bij ongeldig nummer.
    """
    if not number:
        return ""

    # Strip apostrof prefix (uit SQL query voor Excel) en witruimte
    number = number.strip().lstrip("'").strip()

    # Verwijder alles behalve cijfers en leading +
    cleaned = re.sub(r"[^\d+]", "", number)
    # Verwijder + uit het midden, behoud alleen leading +
    if cleaned.startswith("+"):
        cleaned = "+" + cleaned[1:].replace("+", "")
    else:
        cleaned = cleaned.replace("+", "")

    # ── Belgische nummers ────────────────────────────────────────────────────
    if cleaned.startswith("+32"):
        return cleaned
    if cleaned.startswith("0032"):
        return "+32" + cleaned[4:]
    if cleaned.startswith("32") and len(cleaned) >= 10:
        return "+" + cleaned
    # BE mobiel: 04xx xxxxxxx (10 cijfers)
    if re.match(r"^04\d{8}$", cleaned):
        return "+32" + cleaned[1:]
    # BE vast: 0[2-9]xxxxxxx (9 cijfers)
    if re.match(r"^0[2-9]\d{7}$", cleaned):
        return "+32" + cleaned[1:]

    # ── Nederlandse nummers ──────────────────────────────────────────────────
    if cleaned.startswith("+31"):
        return cleaned  # Al in E.164
    if cleaned.startswith("0031"):
        return "+31" + cleaned[4:]
    if cleaned.startswith("316") and len(cleaned) >= 11:
        return "+" + cleaned
    if cleaned.startswith("06") and len(cleaned) == 10:
        return "+31" + cleaned[1:]
    # NL vaste nummers (010, 020, 030, 040, 050, 070, 085, 088, etc.)
    if re.match(r"^0[1-9]\d{8}$", cleaned):
        return "+31" + cleaned[1:]

    # ── Duitse nummers ───────────────────────────────────────────────────────
    if cleaned.startswith("+49"):
        return cleaned
    if cleaned.startswith("0049"):
        return "+49" + cleaned[4:]
    if cleaned.startswith("49") and len(cleaned) >= 11:
        return "+" + cleaned
    # DE mobiel: 015x, 016x, 017x
    if re.match(r"^01[5-7]\d{8,10}$", cleaned):
        return "+49" + cleaned[1:]
    # DE vast: 0[2-9]xxx
    if re.match(r"^0[2-9]\d{6,12}$", cleaned):
        return "+49" + cleaned[1:]

    logger.warning(f"Ongeldig/niet-herkend telefoonnummer: '{number}' → '{cleaned}'")
    return ""


def get_country_from_phone(phone: str) -> str:
    """Bepaal het land op basis van een genormaliseerd E.164 telefoonnummer."""
    if phone.startswith("+31"):
        return "NL"
    elif phone.startswith("+32"):
        return "BE"
    elif phone.startswith("+49"):
        return "DE"
    return "NL"  # Standaard NL


def clean_field(value) -> str:
    """Converteer database waarde naar schone string."""
    if value is None:
        return ""
    return str(value).strip().lstrip("'")


def truncate_message(message: str, max_length: int = 3900) -> list[str]:
    """
    Splits een lang bericht op in meerdere delen van max max_length tekens.
    Splitst op regeleindes waar mogelijk.
    """
    if len(message) <= max_length:
        return [message]

    parts = []
    lines = message.split("\n")
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 <= max_length:
            current += line + "\n"
        else:
            if current:
                parts.append(current.rstrip())
            current = line + "\n"

    if current.strip():
        parts.append(current.rstrip())

    return parts if parts else [message[:max_length]]
