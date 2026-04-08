"""
messaging.py - WhatsApp verzendlogica via TextMeBot API
Met URL encoding, timeout en foutafhandeling.
"""

import time
import requests
from urllib.parse import quote
from logger import logger
from config import (
    TEXTMEBOT_API_KEY, TEXTMEBOT_API_URL,
    TEXTMEBOT_TIMEOUT, DELAY_BETWEEN_MESSAGES
)


def send_whatsapp(phone: str, message: str, skip_delay: bool = False) -> tuple[bool, str]:
    """
    Verstuur een WhatsApp bericht via TextMeBot API.

    Args:
        phone: E.164 telefoonnummer (+31612345678)
        message: Berichttekst (wordt automatisch URL-encoded)
        skip_delay: Sla de delay over (bijv. voor samenvattingsberichten)

    Returns:
        (succes: bool, detail: str)
    """
    if not TEXTMEBOT_API_KEY:
        return False, "TEXTMEBOT_API_KEY niet geconfigureerd"

    if not phone:
        return False, "Leeg telefoonnummer"

    # URL-encode met expliciete UTF-8 voor speciale tekens (ë, ü, ä, etc.)
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

        # TextMeBot geeft 200 terug bij succes
        if response.status_code == 200:
            response_text = response.text.strip()
            logger.debug(f"TextMeBot response voor {phone}: {response_text}")

            # TextMeBot geeft soms een foutmelding in de body ondanks 200
            if any(err in response_text.lower() for err in ["error", "invalid", "failed", "not found"]):
                return False, f"TextMeBot fout: {response_text}"

            if not skip_delay:
                time.sleep(DELAY_BETWEEN_MESSAGES)

            return True, response_text
        else:
            detail = f"HTTP {response.status_code}: {response.text.strip()[:200]}"
            logger.warning(f"TextMeBot fout voor {phone}: {detail}")
            if not skip_delay:
                time.sleep(DELAY_BETWEEN_MESSAGES)
            return False, detail

    except requests.exceptions.Timeout:
        logger.warning(f"TextMeBot timeout voor {phone}")
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
    Geen delay, want dit zijn interne berichten.
    """
    from config import SUMMARY_PHONE
    if not SUMMARY_PHONE:
        logger.error("SUMMARY_PHONE niet geconfigureerd, kan systeembericht niet sturen")
        return False

    success, detail = send_whatsapp(SUMMARY_PHONE, message, skip_delay=True)
    if not success:
        logger.error(f"Systeembericht versturen mislukt: {detail}")
    return success
