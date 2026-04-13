"""
main.py - Hoofdscript mestbak-checker
Draait dagelijks via Windows Task Scheduler om 13:00.
"""

import sys
import time
from datetime import datetime, date

from config import (
    validate_config, SEND_HOUR, MAX_CUTOFF_HOUR, MAX_CUTOFF_MINUTE,
    DATA_DIR, LOGS_DIR, TEST_MODE,
    TEST_PHONE_NL, TEST_PHONE_BE, TEST_PHONE_DE, get_runtime_config_diagnostics
)
from logger import logger, cleanup_old_logs
from holidays import HolidayChecker
from db import get_customers_for_date
from utils import normalize_phone, get_country_from_phone, is_excluded_notation
from message_builder import build_message, detect_language
from messaging import send_whatsapp, send_system_message
from exclude import (
    load_excluded, is_excluded, register_failure,
    register_success, get_failure_count
)
from summary import (
    send_success_summary, send_failure_summary,
    send_skipped_summary, send_abort_message, send_completion_message
)
import os

# Zorg dat data en logs mappen bestaan
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)


def abort(reason: str):
    """Breek het script af met een logmelding en WhatsApp notificatie."""
    logger.error(f"SCRIPT AFGEBROKEN: {reason}")
    try:
        send_abort_message(reason)
    except Exception as e:
        logger.error(f"Kon abort bericht niet sturen: {e}")
    sys.exit(1)


def resolve_number(mobile_raw: str, phone_raw: str) -> list[tuple[str, str, str]]:
    """
    Bepaal welke nummers gebruikt worden voor verzending.
    Controleert op uitsluitingsnotaties (nul-zes, alleen spoed) voor beide nummers.

    Geeft een lijst van (num_type, raw, normalized) tuples terug in volgorde van voorkeur.
    Lege normalized string = ongeldig/uitgesloten.
    """
    numbers, _ = resolve_number_with_ignored(mobile_raw, phone_raw)
    return numbers


def resolve_number_with_ignored(
    mobile_raw: str,
    phone_raw: str
) -> tuple[list[tuple[str, str, str]], list[dict]]:
    """
    Bepaal welke nummers gebruikt worden en welke bewust genegeerd zijn.

    Geeft (numbers, ignored) terug:
    - numbers: lijst van (num_type, raw, normalized) tuples in voorkeursvolgorde.
    - ignored: lijst van dicts voor notaties zoals "(alleen spoed)" of "nul-zes".
    """
    numbers = []
    ignored = []

    for num_type, raw in [("mobile", mobile_raw), ("phone", phone_raw)]:
        if not raw:
            continue

        # Controleer uitsluitingsnotatie
        excl, reden = is_excluded_notation(raw)
        if excl:
            logger.info(f"Nummer overgeslagen ({reden}): '{raw}'")
            ignored.append({
                "num_type": num_type,
                "raw": raw,
                "reason": reden,
            })
            continue

        normalized = normalize_phone(raw)
        if normalized:
            numbers.append((num_type, raw, normalized))
        else:
            logger.warning(f"Ongeldig nummer ({num_type}): '{raw}'")

    return numbers, ignored


def _format_ignored_number_notes(ignored_numbers: list[dict]) -> list[str]:
    """Maak korte summary-regels voor bewust genegeerde nummernotaties."""
    notes = []
    labels = {
        "mobile": "Mobiel",
        "phone": "LocPhone",
    }
    for item in ignored_numbers:
        label = labels.get(item.get("num_type"), item.get("num_type", "Nummer"))
        reason = item.get("reason", "bewust genegeerd")
        raw = item.get("raw", "")
        notes.append(f"{label} genegeerd ({reason}): {raw}")
    return notes


def _send_summary_safely(summary_name: str, send_func, *args, **kwargs) -> bool:
    """Voorkom dat een falende samenvatting de rest van de afsluiting blokkeert."""
    try:
        send_func(*args, **kwargs)
        return True
    except Exception as e:
        logger.error(f"{summary_name} samenvatting mislukt: {e}")
        return False


def warn_if_duplicate_test_numbers():
    """Log een waarschuwing als testnummers op hetzelfde genormaliseerde nummer uitkomen."""
    labels = {
        "TEST_PHONE_NL": TEST_PHONE_NL,
        "TEST_PHONE_BE": TEST_PHONE_BE,
        "TEST_PHONE_DE": TEST_PHONE_DE,
    }
    normalized_map = {}

    for label, raw in labels.items():
        normalized = normalize_phone(raw)
        if not normalized:
            continue
        normalized_map.setdefault(normalized, []).append(label)

    for normalized, used_by in normalized_map.items():
        if len(used_by) > 1:
            logger.warning(
                f"Testnummers delen hetzelfde nummer {normalized}: {', '.join(used_by)}. "
                "Deduplicatie zal extra testklanten overslaan."
            )


def _get_allowed_test_numbers() -> set[str]:
    """Genormaliseerde allowlist van testnummers voor fail-closed testmodus."""
    allowed = set()
    for raw in (TEST_PHONE_NL, TEST_PHONE_BE, TEST_PHONE_DE):
        normalized = normalize_phone(raw)
        if normalized:
            allowed.add(normalized)
    return allowed


def assert_safe_test_customers(customers: list[dict]):
    """
    Verifieer dat testmodus alleen expliciet gemarkeerde testrecords met
    toegestane testnummers verwerkt.
    """
    allowed_numbers = _get_allowed_test_numbers()

    if not allowed_numbers:
        abort("Testmodus onveilig: geen geldige TEST_PHONE_* nummers geconfigureerd")

    for customer in customers:
        if not customer.get("is_test_customer"):
            abort(
                "Testmodus onveilig: klantenlijst bevat niet-gemarkeerde records. "
                "Databaseklanten mogen nooit in testmodus worden verwerkt."
            )

        numbers_to_try = resolve_number(
            customer.get("mobile", ""),
            customer.get("phone", "")
        )
        disallowed_numbers = [
            normalized for _, _, normalized in numbers_to_try
            if normalized not in allowed_numbers
        ]

        if disallowed_numbers:
            abort(
                f"Testmodus onveilig: klant '{customer.get('name', 'Onbekend')}' "
                f"bevat niet-toegestaan nummer: {', '.join(disallowed_numbers)}"
            )


def run():
    start_time = time.time()
    now = datetime.now()
    today = date.today()
    run_date = now.strftime("%Y-%m-%d %H:%M")

    logger.info("=" * 60)
    logger.info(f"Mestbak-checker gestart — {run_date}")
    logger.info(f"Testmodus: {'AAN' if TEST_MODE else 'UIT'}")
    diagnostics = get_runtime_config_diagnostics()
    logger.info(
        "Config bron: .env=%s | TEST_MODE raw=%s | bron=%s | .env TEST_MODE=%s",
        diagnostics["dotenv_path"],
        diagnostics["test_mode_raw"],
        diagnostics["test_mode_source"],
        diagnostics["dotenv_test_mode_raw"],
    )
    if TEST_MODE:
        warn_if_duplicate_test_numbers()

    # ── Stap 1: Cutoff check ─────────────────────────────────────────────────
    cutoff = now.replace(hour=MAX_CUTOFF_HOUR, minute=MAX_CUTOFF_MINUTE, second=0)
    if now > cutoff and not TEST_MODE:
        abort(
            f"Te laat gestart ({now.strftime('%H:%M')}), "
            f"cutoff is {MAX_CUTOFF_HOUR}:{MAX_CUTOFF_MINUTE:02d}"
        )

    # ── Stap 2: Config valideren ─────────────────────────────────────────────
    missing = validate_config()
    if missing:
        abort(f".env incompleet, ontbrekende variabelen: {', '.join(missing)}")
    logger.info("Config geladen ✓")

    # ── Stap 3: Feestdagen ophalen ───────────────────────────────────────────
    if today.weekday() >= 5:
        msg = "Vandaag is het weekend, script stopt zonder berichten te versturen"
        logger.info(msg)
        send_system_message(f"â„¹ï¸ Mestbak-checker niet uitgevoerd\n{today}\n\nReden: {msg}")
        sys.exit(0)

    checker = HolidayChecker()
    try:
        checker.fetch_all(today)
        logger.info("Feestdagen opgehaald ✓")
    except ConnectionError as e:
        abort(str(e))

    # ── Stap 4: Is vandaag een NL feestdag? ──────────────────────────────────
    nl_today, nl_today_name = checker.is_nl_holiday(today)
    if nl_today:
        msg = f"Vandaag is een Nederlandse feestdag ({nl_today_name}), script stopt"
        logger.info(msg)
        send_system_message(f"ℹ️ Mestbak-checker niet uitgevoerd\n{today}\n\nReden: {msg}")
        sys.exit(0)

    # ── Stap 4b: Is vandaag een BE/DE feestdag? ──────────────────────────────
    be_today, _ = checker.is_be_holiday(today)
    de_today, _ = checker.is_de_holiday(today)

    if be_today:
        logger.info("Vandaag BE feestdag — BE klanten worden overgeslagen")
    if de_today:
        logger.info("Vandaag DE feestdag — DE klanten worden overgeslagen")

    # ── Stap 5: Exclude lijst laden ──────────────────────────────────────────
    excluded = load_excluded()
    logger.info(f"Excludelijst geladen: {len(excluded)} uitgesloten nummers")

    # ── Stap 6: Database query ───────────────────────────────────────────────
    if TEST_MODE:
        logger.info("TESTMODUS: Gebruik testklanten i.p.v. database")
        customers = _get_test_customers()
        assert_safe_test_customers(customers)
    else:
        query_date = checker.next_workday(today, "NL")
        try:
            customers = get_customers_for_date(query_date)
        except ConnectionError as e:
            abort(str(e))

        if not customers:
            msg = f"Geen klanten gevonden in database voor {query_date}"
            logger.info(msg)
            send_system_message(f"ℹ️ Mestbak-checker: {msg}")
            sys.exit(0)

    logger.info(f"Aantal klanten te verwerken: {len(customers)}")

    # ── Stap 7: Per klant berichten versturen ────────────────────────────────
    successes = []
    failures = []
    skipped = []
    excluded_count = 0
    ignored_number_count = 0
    seen_phones = set()  # Deduplicatie op telefoonnummer

    for customer in customers:
        customer_info = {
            "order_id": customer.get("order_id"),
            "sj_order_id": customer.get("sj_order_id", ""),
            "name": customer.get("name", ""),
            "street": customer.get("street", ""),
            "zip": customer.get("zip", ""),
            "city": customer.get("city", ""),
            "country": customer.get("country", ""),
        }

        # Bepaal geldige nummers (mobile eerst, dan phone)
        numbers_to_try, ignored_numbers = resolve_number_with_ignored(
            customer.get("mobile", ""),
            customer.get("phone", "")
        )
        ignored_number_count += len(ignored_numbers)
        ignored_number_notes = _format_ignored_number_notes(ignored_numbers)

        # Geen enkel geldig nummer
        if not numbers_to_try:
            logger.info(
                f"Overgeslagen (geen geldig nummer): {customer['name']} | "
                f"mobile='{customer.get('mobile', '')}' "
                f"phone='{customer.get('phone', '')}'"
            )
            skipped.append({
                "customer": customer_info,
                "reason": "; ".join(
                    ["Geen geldig nummer", *ignored_number_notes]
                ) if ignored_number_notes else "Geen geldig nummer"
            })
            continue

        # Verwerk elk nummer
        customer_sent = False
        any_send_attempted = False  # Werd er daadwerkelijk een API-call gedaan?
        seen_skipped_numbers = []
        excluded_numbers = []

        for num_type, raw, phone_number in numbers_to_try:
            if customer_sent:
                break

            # Deduplicatie — al een bericht gestuurd naar dit nummer?
            # Alleen dit specifieke nummer overslaan; het volgende nummer (fallback)
            # krijgt nog een kans. customer_sent blijft False zodat de lus doorgaat.
            if phone_number in seen_phones:
                seen_skipped_numbers.append(phone_number)
                logger.debug(
                    f"Nummer al verzonden vandaag, probeer volgend nummer: "
                    f"{customer['name']} → {phone_number} ({num_type})"
                )
                continue

            # Exclude check per nummer
            if is_excluded(phone_number):
                logger.info(f"Uitgesloten: {phone_number} ({customer['name']})")
                excluded_numbers.append(phone_number)
                excluded_count += 1
                continue

            # Vandaag feestdag voor dit land? → overslaan
            country = get_country_from_phone(phone_number)
            language = detect_language(phone_number, customer.get("country", ""))

            if be_today and country == "BE":
                logger.info(f"Overgeslagen (BE feestdag vandaag): {customer['name']}")
                skipped.append({
                    "customer": customer_info,
                    "reason": "Vandaag BE feestdag"
                })
                customer_sent = True
                continue

            if de_today and country == "DE":
                logger.info(f"Overgeslagen (DE feestdag vandaag): {customer['name']}")
                skipped.append({
                    "customer": customer_info,
                    "reason": "Vandaag DE feestdag"
                })
                customer_sent = True
                continue

            # Bepaal feestdagscenario voor morgen
            scenario = checker.get_holiday_scenario(today, country)

            # Bouw bericht
            message = build_message(language, scenario, today, hour=SEND_HOUR)

            logger.info(
                f"Versturen naar {customer['name']} | "
                f"{phone_number} ({num_type}) | "
                f"Scenario: {scenario['scenario']} | "
                f"Taal: {language}"
            )
            logger.debug(f"Bericht:\n{message}")

            # Verstuur
            any_send_attempted = True
            success, detail = send_whatsapp(phone_number, message)

            if success:
                register_success(phone_number)
                # Voeg alle nummers van deze klant toe aan seen_phones zodat een
                # duplicate klantrecord verderop in de lijst via zijn andere nummer
                # geen tweede bericht krijgt.
                seen_phones.update(n for _, _, n in numbers_to_try)
                successes.append({
                    "customer": customer_info,
                    "phone_used": phone_number,
                    "num_type": num_type,
                    "note": "; ".join([
                        note for note in [
                            "via LocPhone (fallback)" if num_type == "phone" else "",
                            *ignored_number_notes,
                        ] if note
                    ]),
                    "ignored_numbers": ignored_numbers,
                })
                customer_sent = True
                logger.info(f"✅ Verstuurd: {customer['name']} → {phone_number}")

            else:
                fc = get_failure_count(phone_number)
                auto_excl = register_failure(phone_number, {
                    **customer_info,
                    "phone": phone_number
                })
                failures.append({
                    "customer": customer_info,
                    "phone_used": phone_number,
                    "num_type": num_type,
                    "error": detail,
                    "failure_count": fc + 1,
                    "max_failures": 3,
                    "auto_excluded": auto_excl,
                })
                logger.warning(
                    f"❌ Mislukt: {customer['name']} → {phone_number} | {detail}"
                )
                # Als mobile mislukt en phone nog beschikbaar: probeer phone

        # Klant volledig afgehandeld zonder verzendpoging → alle nummers
        # waren al eerder vandaag verstuurd of uitgesloten.
        if not customer_sent and not any_send_attempted:
            reasons = []
            if seen_skipped_numbers:
                reasons.append(
                    "al verzonden: " + ", ".join(seen_skipped_numbers)
                )
            if excluded_numbers:
                reasons.append(
                    "uitgesloten: " + ", ".join(excluded_numbers)
                )
            reason = "; ".join(reasons) or "Geen verzendpoging gedaan"
            logger.info(
                f"Overgeslagen (nummers al verzonden vandaag of uitgesloten): "
                f"{customer['name']} | {reason}"
            )
            skipped.append({
                "customer": customer_info,
                "reason": "; ".join([
                    note for note in [reason, *ignored_number_notes] if note
                ])
            })

    # ── Stap 8 & 9: Samenvattingsberichten ──────────────────────────────────
    logger.info(
        f"Run klaar: {len(successes)} verstuurd, "
        f"{len(failures)} mislukt, "
        f"{len(skipped)} overgeslagen, "
        f"{excluded_count} uitgesloten, "
        f"{ignored_number_count} nummers genegeerd"
    )

    _send_summary_safely("Successen", send_success_summary, successes, run_date)
    _send_summary_safely("Failures", send_failure_summary, failures, run_date)
    _send_summary_safely("Overgeslagen", send_skipped_summary, skipped, run_date)

    # ── Stap 10: Afsluiting ──────────────────────────────────────────────────
    duration = time.time() - start_time
    send_completion_message(
        run_date=run_date,
        sent_count=len(successes),
        failed_count=len(failures),
        skipped_count=len(skipped),
        excluded_count=excluded_count,
        ignored_number_count=ignored_number_count,
        duration_seconds=duration
    )

    cleanup_old_logs()

    logger.info(f"Mestbak-checker afgesloten in {duration:.1f} seconden")
    logger.info("=" * 60)


def _get_test_customers() -> list[dict]:
    """Testklanten voor testmodus — gebruikt eigen testnummers."""
    return [
        {
            "order_id": 99001,
            "sj_order_id": "TEST-NL-001",
            "name": "Test Klant Nederland",
            "street": "Teststraat 1",
            "zip": "7121 AA",
            "city": "Aalten",
            "country": "NL",
            "phone": "",
            "mobile": TEST_PHONE_NL,
            "moment_rta": None,
            "is_test_customer": True,
        },
        {
            "order_id": 99002,
            "sj_order_id": "TEST-BE-001",
            "name": "Test Klant België",
            "street": "Testlaan 2",
            "zip": "9000",
            "city": "Gent",
            "country": "BE",
            "phone": "",
            "mobile": TEST_PHONE_BE,
            "moment_rta": None,
            "is_test_customer": True,
        },
        {
            "order_id": 99003,
            "sj_order_id": "TEST-DE-001",
            "name": "Test Kunde Deutschland",
            "street": "Teststraße 3",
            "zip": "48143",
            "city": "Münster",
            "country": "DE",
            "phone": "",
            "mobile": TEST_PHONE_DE,
            "moment_rta": None,
            "is_test_customer": True,
        },
        # Test deduplicatie: zelfde nummer als TEST-NL-001
        {
            "order_id": 99004,
            "sj_order_id": "TEST-NL-DUP",
            "name": "Test Duplicaat (zelfde nummer als NL-001)",
            "street": "Teststraat 2",
            "zip": "7121 AA",
            "city": "Aalten",
            "country": "NL",
            "phone": "",
            "mobile": TEST_PHONE_NL,
            "moment_rta": None,
            "is_test_customer": True,
        },
        # Test nul-notatie
        {
            "order_id": 99005,
            "sj_order_id": "TEST-NUL-001",
            "name": "Test Nul-notatie",
            "street": "Teststraat 3",
            "zip": "7121 AA",
            "city": "Aalten",
            "country": "NL",
            "phone": "",
            "mobile": "nul-zes 43091465",
            "moment_rta": None,
            "is_test_customer": True,
        },
        # Test alleen spoed
        {
            "order_id": 99006,
            "sj_order_id": "TEST-SPOED-001",
            "name": "Test Alleen Spoed",
            "street": "Teststraat 4",
            "zip": "7121 AA",
            "city": "Aalten",
            "country": "NL",
            "phone": "0031653301960 (alleen spoed)",
            "mobile": "",
            "moment_rta": None,
            "is_test_customer": True,
        },
    ]


if __name__ == "__main__":
    run()
