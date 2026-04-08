"""
messaging.py - WhatsApp verzendlogica via TextMeBot API
Met URL encoding, timeout en foutafhandeling.
"""

import time
from urllib.parse import quote

import requests

from config import (
    DELAY_BETWEEN_MESSAGES,
    TEXTMEBOT_API_KEY,
    TEXTMEBOT_API_URL,
    TEXTMEBOT_TIMEOUT,
)
from logger import logger

_TEXTMEBOT_MIN_INTERVAL_SECONDS = 8
_last_send_time: float = 0.0


def send_whatsapp(phone: str, message: str, skip_delay: bool = False) -> tuple[bool, str]:
    """
    Verstuur een WhatsApp bericht via TextMeBot API.

    Args:
        phone: E.164 telefoonnummer (+31612345678)
        message: Berichttekst (wordt automatisch URL-encoded)
        skip_delay: Sla de delay over als dit expliciet gewenst is

    Returns:
        (succes: bool, detail: str)
    """
    global _last_send_time

    if not TEXTMEBOT_API_KEY:
        return False, "TEXTMEBOT_API_KEY niet geconfigureerd"

    if not phone:
        return False, "Leeg telefoonnummer"

    effective_delay = max(DELAY_BETWEEN_MESSAGES, _TEXTMEBOT_MIN_INTERVAL_SECONDS)

    if not skip_delay and _last_send_time > 0:
        elapsed = time.monotonic() - _last_send_time
        wait = effective_delay - elapsed
        if wait > 0:
            time.sleep(wait)

    encoded_message = quote(message, encoding="utf-8")
    encoded_phone = quote(phone, encoding="utf-8")

    url = (
        f"{TEXTMEBOT_API_URL}"
        f"?recipient={encoded_phone}"
        f"&apikey={quote(TEXTMEBOT_API_KEY)}"
        f"&text={encoded_message}"
    )

    try:
        response = requests.get(url, timeout=TEXTMEBOT_TIMEOUT)
        _last_send_time = time.monotonic()

        if response.status_code == 200:
            response_text = response.text.strip()
            logger.debug(f"TextMeBot response voor {phone}: {response_text}")

            if any(err in response_text.lower() for err in ["error", "invalid", "failed", "not found"]):
                return False, f"TextMeBot fout: {response_text}"

            return True, response_text

        detail = f"HTTP {response.status_code}: {response.text.strip()[:200]}"
        logger.warning(f"TextMeBot fout voor {phone}: {detail}")
        return False, detail

    except requests.exceptions.Timeout:
        logger.warning(f"TextMeBot timeout voor {phone}")
        _last_send_time = time.monotonic()
        return False, "Timeout"
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"TextMeBot verbindingsfout voor {phone}: {e}")
        return False, f"Verbindingsfout: {e}"
    except requests.exceptions.RequestException as e:
        logger.warning(f"TextMeBot onverwachte fout voor {phone}: {e}")
        return False, f"Onverwachte fout: {e}"


def send_system_message(message: str) -> bool:
    """
    Stuur een systeembericht naar het eigen samenvattingsnummer.
    Respecteert dezelfde throttling als klantberichten om rate limits te voorkomen.
    """
    from config import SUMMARY_PHONE

    if not SUMMARY_PHONE:
        logger.error("SUMMARY_PHONE niet geconfigureerd, kan systeembericht niet sturen")
        return False

    success, detail = send_whatsapp(SUMMARY_PHONE, message, skip_delay=False)
    if not success:
        logger.error(f"Systeembericht versturen mislukt: {detail}")
    return success
