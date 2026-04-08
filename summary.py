"""
summary.py - Samenvattingsberichten naar eigen nummer
Successen en failures als aparte WhatsApp berichten, automatisch gesplitst.
"""

from datetime import datetime
from messaging import send_system_message, send_whatsapp
from utils import truncate_message
from logger import logger
from config import SUMMARY_PHONE, DELAY_BETWEEN_MESSAGES
import time


_COUNTRY_FLAGS = {
    "NL": "🇳🇱",
    "BE": "🇧🇪",
    "DE": "🇩🇪",
}


def _format_customer_line(customer: dict, phone_used: str, detail: str = "") -> str:
    """Formatteer één klantregel voor het samenvattingsbericht."""
    country = customer.get('country', '')
    flag = _COUNTRY_FLAGS.get(country, country)
    parts = [
        f"➡️ {customer.get('name', 'Onbekend')}",
        f"  {customer.get('street', '')}",
        f"  {customer.get('zip', '')} {customer.get('city', '')} {flag}",
        f"  📱 {phone_used}",
    ]
    if customer.get("sj_order_id"):
        parts.append(f"  Sjabloonnummer: {customer['sj_order_id']}")
    if detail:
        parts.append(f"  ⚠️ {detail}")
    return "\n".join(parts)


def _send_multipart(header: str, lines: list[str], footer: str = ""):
    """Stuur een bericht dat mogelijk te lang is als meerdere delen."""
    if not lines:
        msg = f"{header}\n\n(geen)\n\n{footer}".strip()
        send_system_message(msg)
        return

    # Bouw volledige tekst op
    full_text = header + "\n\n" + "\n\n".join(lines)
    if footer:
        full_text += f"\n\n{footer}"

    parts = truncate_message(full_text, max_length=3900)

    for i, part in enumerate(parts):
        if len(parts) > 1:
            part_header = f"(deel {i+1}/{len(parts)})\n\n"
            part = part_header + part

        send_system_message(part)

        if i < len(parts) - 1:
            time.sleep(DELAY_BETWEEN_MESSAGES)


def send_success_summary(successes: list[dict], run_date: str):
    """
    Stuur samenvattingsbericht met alle succesvolle verzendingen.
    successes: lijst van dicts met customer info + phone_used
    """
    if not successes:
        send_system_message(
            f"✅ Mestbak-checker {run_date}\n\n"
            "Geen succesvolle berichten verstuurd."
        )
        return

    header = f"✅ SUCCESSEN — Mestbak-checker {run_date}\n{len(successes)} bericht(en) verstuurd:"

    lines = []
    for item in successes:
        line = _format_customer_line(
            item["customer"],
            item["phone_used"],
            detail=item.get("note", "")
        )
        lines.append(line)

    _send_multipart(header, lines)
    logger.info(f"Successen samenvatting verstuurd ({len(successes)} klanten)")


def send_failure_summary(failures: list[dict], run_date: str):
    """
    Stuur samenvattingsbericht met alle mislukte verzendingen.
    failures: lijst van dicts met customer info + phone_used + error
    """
    if not failures:
        return  # Geen failures = geen bericht nodig

    header = f"❌ FAILURES — Mestbak-checker {run_date}\n{len(failures)} bericht(en) mislukt:"

    lines = []
    for item in failures:
        line = _format_customer_line(
            item["customer"],
            item["phone_used"],
            detail=item.get("error", "Onbekende fout")
        )
        # Voeg failure teller toe
        fc = item.get("failure_count", 0)
        if fc > 0:
            line += f"\n  🔢 Failures totaal: {fc}/{item.get('max_failures', 3)}"
        if item.get("auto_excluded"):
            line += "\n  🚫 AUTO-EXCLUDED na deze poging"
        lines.append(line)

    _send_multipart(header, lines)
    logger.info(f"Failures samenvatting verstuurd ({len(failures)} klanten)")


def send_abort_message(reason: str):
    """Stuur een bericht bij vroegtijdig afbreken van het script."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"⚠️ Mestbak-checker AFGEBROKEN\n{now}\n\nReden: {reason}"
    send_system_message(msg)
    logger.warning(f"Abort bericht verstuurd: {reason}")


def send_completion_message(
    run_date: str,
    sent_count: int,
    failed_count: int,
    skipped_count: int,
    excluded_count: int,
    duration_seconds: float
):
    """Stuur afsluitend bericht met statistieken."""
    mins = int(duration_seconds // 60)
    secs = int(duration_seconds % 60)
    duration_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

    msg = (
        f"🏁 Mestbak-checker klaar — {run_date}\n\n"
        f"✅ Verstuurd:    {sent_count}\n"
        f"❌ Mislukt:      {failed_count}\n"
        f"⏭️ Overgeslagen: {skipped_count}\n"
        f"🚫 Uitgesloten:  {excluded_count}\n"
        f"⏱️ Duur:         {duration_str}"
    )
    send_system_message(msg)
