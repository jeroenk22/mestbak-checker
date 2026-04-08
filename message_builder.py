"""
message_builder.py - Berichtteksten voor mestbak-checker
Bouwt WhatsApp berichten op basis van land, dagdeel en feestdagscenario.
"""

from datetime import date
from config import SEND_HOUR, MIDDAG_START, AVOND_START


# ─── Dagdeel ─────────────────────────────────────────────────────────────────

def get_greeting(language: str, hour: int = SEND_HOUR) -> str:
    """Geef de juiste begroeting op basis van taal en uur."""
    if hour < MIDDAG_START:
        return "Goedemorgen" if language in ("NL", "BE") else "Guten Morgen"
    elif hour < AVOND_START:
        return "Goedemiddag" if language in ("NL", "BE") else "Guten Mittag"
    else:
        return "Goedenavond" if language in ("NL", "BE") else "Guten Abend"


# ─── Datumopmaak ─────────────────────────────────────────────────────────────

DUTCH_WEEKDAYS = {
    0: "maandag", 1: "dinsdag", 2: "woensdag",
    3: "donderdag", 4: "vrijdag", 5: "zaterdag", 6: "zondag"
}

GERMAN_WEEKDAYS = {
    0: "Montag", 1: "Dienstag", 2: "Mittwoch",
    3: "Donnerstag", 4: "Freitag", 5: "Samstag", 6: "Sonntag"
}


def format_date_nl(d: date) -> str:
    """Formatteer datum als dd-mm (NL/BE stijl)."""
    return d.strftime("%d-%m")


def format_date_de(d: date) -> str:
    """Formatteer datum als dd.mm.yyyy (DE stijl)."""
    return d.strftime("%d.%m.%Y")


def get_day_name(d: date, language: str) -> str:
    """Geef de naam van de dag in de juiste taal."""
    if language in ("NL", "BE"):
        return DUTCH_WEEKDAYS[d.weekday()]
    return GERMAN_WEEKDAYS[d.weekday()]


def format_target_date(d: date, today: date, language: str) -> str:
    """
    Formatteer de doeldatum voor in het bericht.
    - Morgen: 'morgen (07-04)' of 'morgen (07.04.2026)'
    - Overmorgen of verder: 'maandag (09-04)' of 'Montag (09.04.2026)'
    """
    tomorrow = today + __import__("datetime").timedelta(days=1)

    if language in ("NL", "BE"):
        date_str = format_date_nl(d)
        if d == tomorrow:
            return f"morgen ({date_str})"
        else:
            day_name = get_day_name(d, language)
            return f"{day_name} ({date_str})"
    else:
        date_str = format_date_de(d)
        if d == tomorrow:
            return f"morgen ({date_str})"
        else:
            day_name = get_day_name(d, language)
            return f"{day_name} ({date_str})"


# ─── Berichtteksten ──────────────────────────────────────────────────────────

SIGNATURE_NL = "Met vriendelijke groet,\nMiedema Ophaaldienst B.V."
SIGNATURE_DE = "Mit freundlichen Grüßen,\nMiedema Ophaaldienst B.V."


def build_message(language: str, scenario: dict, today: date,
                  hour: int = SEND_HOUR) -> str:
    """
    Bouw het WhatsApp bericht op basis van taal en feestdagscenario.

    scenario dict (van HolidayChecker.get_holiday_scenario):
        - scenario: 'normal' | 'nl_holiday' | 'country_holiday' | 'both_holiday'
        - next_workday: date
        - nl_holiday_name: str
        - tomorrow_is_weekend: bool
    """
    greeting = get_greeting(language, hour)
    sig = SIGNATURE_NL if language in ("NL", "BE") else SIGNATURE_DE
    sc = scenario["scenario"]
    next_wd = scenario["next_workday"]
    nl_name = scenario.get("nl_holiday_name", "")

    # ── Normaal (werkdag of weekend → volgende werkdag) ──────────────────────
    if sc == "normal":
        target = format_target_date(next_wd, today, language)
        if language in ("NL", "BE"):
            body = f"Weet u al hoeveel mestbakken u {target} heeft?"
        else:
            body = f"Wissen Sie schon, wie viele Kisten Sie {target} haben?"

    # ── NL feestdag, BE/DE gewone werkdag ────────────────────────────────────
    elif sc == "nl_holiday":
        target = format_target_date(next_wd, today, language)
        if language == "NL":
            body = f"Weet u al hoeveel mestbakken u {target} heeft?"
        elif language == "BE":
            body = (
                f"Vanwege de Nederlandse feestdag {nl_name} rijden wij morgen niet. "
                f"Weet u al hoeveel mestbakken u {target} heeft?"
            )
        else:  # DE
            body = (
                f"Aufgrund des niederländischen Feiertags {nl_name} fahren wir morgen nicht. "
                f"Wissen Sie schon, wie viele Kisten Sie {target} haben?"
            )

    # ── BE/DE feestdag, NL gewone werkdag ────────────────────────────────────
    elif sc == "country_holiday":
        country_name = scenario.get("country_holiday_name", "")
        if language == "BE":
            name_suffix = f" ({country_name})" if country_name else ""
            body = (
                f"Heeft u morgen mestbakken klaar staan i.v.m. feestdag{name_suffix}? "
                "Indien ja, hoeveel bakken heeft u dan klaar staan?"
            )
        else:  # DE
            name_suffix = f" ({country_name})" if country_name else ""
            body = (
                f"Haben Sie morgen Kisten bereitstehen aufgrund eines Feiertags{name_suffix}? "
                "Wenn ja, wie viele Kisten hätten Sie bereit?"
            )

    # ── Beide landen feestdag → eerstvolgende werkdag ────────────────────────
    elif sc == "both_holiday":
        target = format_target_date(next_wd, today, language)
        if language in ("NL", "BE"):
            body = f"Weet u al hoeveel mestbakken u {target} heeft?"
        else:
            body = f"Wissen Sie schon, wie viele Kisten Sie {target} haben?"

    else:
        # Fallback
        target = format_target_date(next_wd, today, language)
        if language in ("NL", "BE"):
            body = f"Weet u al hoeveel mestbakken u {target} heeft?"
        else:
            body = f"Wissen Sie schon, wie viele Kisten Sie {target} haben?"

    return f"{greeting},\n\n{body}\n\n{sig}"


# ─── Taaldetectie op basis van landcode ──────────────────────────────────────

def detect_language(phone: str, loc_country: str = "") -> str:
    """
    Bepaal de taal op basis van telefoonnummer landcode of LocCountry veld.
    Geeft 'NL', 'BE' of 'DE' terug.
    """
    # Probeer eerst op telefoonnummer
    if phone.startswith("+31"):
        return "NL"
    elif phone.startswith("+32"):
        return "BE"
    elif phone.startswith("+49"):
        return "DE"

    # Fallback op LocCountry veld
    country = (loc_country or "").strip().upper()
    if country in ("NL", "NEDERLAND", "NETHERLANDS", "THE NETHERLANDS"):
        return "NL"
    elif country in ("BE", "BELGIE", "BELGIË", "BELGIUM"):
        return "BE"
    elif country in ("DE", "DEUTSCHLAND", "GERMANY", "DUITSLAND"):
        return "DE"

    # Standaard NL
    return "NL"
