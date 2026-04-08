"""
holidays.py - Feestdagenlogica via Nager.Date API
Ondersteunt NL, BE, NRW en Niedersachsen (DE).
"""

import requests
from datetime import date, timedelta
from logger import logger
from config import NAGER_API_URL, NAGER_TIMEOUT, DE_REGIONS


def get_public_holidays(country_code: str, year: int) -> list[dict]:
    """Haal public feestdagen op voor een land en jaar via Nager.Date API.
    Geeft een lijst van feestdag-dicts terug met 'date', 'localName', 'name', 'counties'.
    """
    url = f"{NAGER_API_URL}/{year}/{country_code}"
    try:
        response = requests.get(url, timeout=NAGER_TIMEOUT)
        response.raise_for_status()
        holidays = response.json()
        # Alleen public feestdagen
        return [h for h in holidays if h.get("types") and "Public" in h["types"]]
    except requests.exceptions.Timeout:
        raise ConnectionError(f"Nager.Date timeout voor {country_code} {year}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Nager.Date onbereikbaar voor {country_code} {year}: {e}")


def _is_holiday_for_date(target_date: date, holidays: list[dict],
                          regions: list[str] | None = None) -> tuple[bool, str]:
    """Controleer of een datum een feestdag is.
    Als regions opgegeven is (bijv. ['NW', 'NI'] voor DE), check dan ook op counties.
    Geeft (is_holiday, holiday_name) terug.
    """
    target_str = target_date.strftime("%Y-%m-%d")
    for h in holidays:
        if h.get("date") != target_str:
            continue
        counties = h.get("counties")
        if regions is None:
            # Geen regio filter: geldt voor heel het land
            return True, h.get("localName", h.get("name", "Feestdag"))
        else:
            # Feestdag geldt voor heel land (counties is None/leeg) of voor onze regio
            if not counties or any(r in counties for r in regions):
                return True, h.get("localName", h.get("name", "Feestdag"))
    return False, ""


class HolidayChecker:
    """Beheert feestdagendata voor NL, BE en DE (NRW + Niedersachsen)."""

    def __init__(self):
        self._cache = {}

    def _get_holidays(self, country_code: str, year: int) -> list[dict]:
        key = f"{country_code}_{year}"
        if key not in self._cache:
            self._cache[key] = get_public_holidays(country_code, year)
            logger.debug(f"Feestdagen geladen: {country_code} {year} "
                         f"({len(self._cache[key])} public feestdagen)")
        return self._cache[key]

    def fetch_all(self, check_date: date):
        """Haal alle benodigde feestdagendata op voor check_date en het jaar erna."""
        years = {check_date.year}
        if (check_date + timedelta(days=7)).year != check_date.year:
            years.add(check_date.year + 1)
        for country in ["NL", "BE", "DE"]:
            for year in years:
                self._get_holidays(country, year)

    def is_nl_holiday(self, d: date) -> tuple[bool, str]:
        holidays = self._get_holidays("NL", d.year)
        return _is_holiday_for_date(d, holidays)

    def is_be_holiday(self, d: date) -> tuple[bool, str]:
        holidays = self._get_holidays("BE", d.year)
        return _is_holiday_for_date(d, holidays)

    def is_de_holiday(self, d: date) -> tuple[bool, str]:
        """Controleer of datum een feestdag is in NRW of Niedersachsen."""
        holidays = self._get_holidays("DE", d.year)
        return _is_holiday_for_date(d, holidays, regions=DE_REGIONS)

    def is_workday(self, d: date, country: str) -> bool:
        """Controleer of een datum een werkdag is voor het opgegeven land (NL/BE/DE)."""
        if d.weekday() >= 5:  # Weekend
            return False
        if country == "NL":
            is_hol, _ = self.is_nl_holiday(d)
            return not is_hol
        elif country == "BE":
            is_hol, _ = self.is_be_holiday(d)
            return not is_hol
        elif country == "DE":
            is_hol, _ = self.is_de_holiday(d)
            return not is_hol
        return True

    def next_workday(self, from_date: date, country: str = "NL") -> date:
        """Geef de eerstvolgende werkdag terug na from_date voor het opgegeven land."""
        d = from_date + timedelta(days=1)
        while not self.is_workday(d, country):
            d += timedelta(days=1)
        return d

    def get_holiday_scenario(self, today: date, country: str) -> dict:
        """
        Bepaal het feestdagscenario voor morgen voor een klant in het opgegeven land.

        Geeft een dict terug met:
        - scenario: 'normal', 'nl_holiday', 'country_holiday', 'both_holiday'
        - next_workday: eerstvolgende werkdag (NL-perspectief)
        - nl_holiday_name: naam van de NL feestdag (indien van toepassing)
        - tomorrow_is_weekend: True als morgen weekend is
        """
        tomorrow = today + timedelta(days=1)
        tomorrow_is_weekend = tomorrow.weekday() >= 5

        nl_hol, nl_name = self.is_nl_holiday(tomorrow)
        be_hol, be_name = self.is_be_holiday(tomorrow)
        de_hol, de_name = self.is_de_holiday(tomorrow)

        # Als morgen weekend is: altijd standaard (eerstvolgende werkdag)
        if tomorrow_is_weekend:
            next_wd = self.next_workday(today, "NL")
            return {
                "scenario": "normal",
                "next_workday": next_wd,
                "nl_holiday_name": "",
                "tomorrow_is_weekend": True,
            }

        # Morgen is een werkdag — bepaal scenario per land
        if country == "NL":
            if nl_hol:
                next_wd = self.next_workday(tomorrow, "NL")
                return {
                    "scenario": "nl_holiday",
                    "next_workday": next_wd,
                    "nl_holiday_name": nl_name,
                    "tomorrow_is_weekend": False,
                }
            return {
                "scenario": "normal",
                "next_workday": tomorrow,
                "nl_holiday_name": "",
                "tomorrow_is_weekend": False,
            }

        elif country == "BE":
            if nl_hol and be_hol:
                next_wd = self.next_workday(tomorrow, "NL")
                return {
                    "scenario": "both_holiday",
                    "next_workday": next_wd,
                    "nl_holiday_name": nl_name,
                    "tomorrow_is_weekend": False,
                }
            elif nl_hol and not be_hol:
                next_wd = self.next_workday(tomorrow, "NL")
                return {
                    "scenario": "nl_holiday",
                    "next_workday": next_wd,
                    "nl_holiday_name": nl_name,
                    "tomorrow_is_weekend": False,
                }
            elif be_hol and not nl_hol:
                return {
                    "scenario": "country_holiday",
                    "next_workday": tomorrow,
                    "nl_holiday_name": "",
                    "country_holiday_name": be_name,
                    "tomorrow_is_weekend": False,
                }
            return {
                "scenario": "normal",
                "next_workday": tomorrow,
                "nl_holiday_name": "",
                "tomorrow_is_weekend": False,
            }

        elif country == "DE":
            if nl_hol and de_hol:
                next_wd = self.next_workday(tomorrow, "NL")
                return {
                    "scenario": "both_holiday",
                    "next_workday": next_wd,
                    "nl_holiday_name": nl_name,
                    "tomorrow_is_weekend": False,
                }
            elif nl_hol and not de_hol:
                next_wd = self.next_workday(tomorrow, "NL")
                return {
                    "scenario": "nl_holiday",
                    "next_workday": next_wd,
                    "nl_holiday_name": nl_name,
                    "tomorrow_is_weekend": False,
                }
            elif de_hol and not nl_hol:
                return {
                    "scenario": "country_holiday",
                    "next_workday": tomorrow,
                    "nl_holiday_name": "",
                    "country_holiday_name": de_name,
                    "tomorrow_is_weekend": False,
                }
            return {
                "scenario": "normal",
                "next_workday": tomorrow,
                "nl_holiday_name": "",
                "tomorrow_is_weekend": False,
            }

        # Fallback
        return {
            "scenario": "normal",
            "next_workday": tomorrow,
            "nl_holiday_name": "",
            "tomorrow_is_weekend": False,
        }
