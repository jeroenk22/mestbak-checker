# mestbak-checker

Stuurt elke werkdag om 13:00 een WhatsApp bericht naar klanten via de TextMeBot API.
Het vraagt hoeveel mestbakken zij de volgende dag klaar hebben staan.

- Haalt klantgegevens op uit SQL Server (alleen lezen)
- Houdt rekening met feestdagen in NL, Belgie en Duitsland
- Stuurt berichten in de juiste taal (NL of Duits)
- Logt alles en stuurt een samenvatting naar de beheerder

## Mapstructuur

```text
mestbak-checker/
|- main.py               Hoofdscript (dit wordt uitgevoerd)
|- config.py             Alle instellingen en variabelen
|- db.py                 Database verbinding en query
|- messaging.py          WhatsApp verzendlogica (TextMeBot)
|- message_builder.py    Berichtteksten NL/DE per scenario
|- holidays.py           Feestdagenlogica (Nager.Date API)
|- exclude.py            Uitsluitlijst en failure tellers
|- logger.py             Logging naar dagelijkse logbestanden
|- summary.py            Samenvattingsberichten naar beheerder
|- utils.py              Telefoonnummer normalisatie e.d.
|- run_tests.py          Voer alle unit tests uit
|- requirements.txt      Benodigde Python packages
|- .env                  API keys en instellingen (NOOIT in Git!)
|- .env.example          Template voor .env
|- sql/
|  \- query.sql          SQL query voor klantgegevens
|- tests/
|  |- test_utils.py           Tests telefoonnummer normalisatie
|  |- test_message_builder.py Tests berichtteksten
|  |- test_holidays.py        Tests feestdagenlogica
|  |- test_main.py            Tests dispatch-logica
|  \- test_messaging.py       Live berichten test (eigen nummer)
|- data/
|  |- excluded_numbers.json   Uitgesloten nummers
|  \- failure_counts.json     Failure tellers per nummer
\- logs/
   \- mestbak-checker-YYYY-MM-DD.log
```

## Installatie

1. Installeer Python via python.org (minimaal 3.11)
2. Open Command Prompt in de projectmap:

```bat
cd C:\Scripts\mestbak-checker
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. Kopieer `.env.example` naar `.env` en vul de waarden in
4. Test: `python run_tests.py`
5. Live test: `python tests\test_messaging.py`

## Task Scheduler

| Instelling | Waarde |
|---|---|
| Programma | `C:\Scripts\mestbak-checker\venv\Scripts\python.exe` |
| Argumenten | `C:\Scripts\mestbak-checker\main.py` |
| Start in | `C:\Scripts\mestbak-checker\` |
| Trigger | Dagelijks 13:00, maandag t/m vrijdag |

Opties: **Run as soon as possible after missed start** = AAN, **Run whether user is logged on or not** = AAN

## Netwerk

Alleen uitgaande verbindingen naar:
- `api.textmebot.com` - WhatsApp berichten
- `date.nager.at` - feestdagenkalender

DB rechten: alleen leesrechten op de geconfigureerde SQL Server

## Logbestanden

- Locatie: `logs\`
- Formaat: `mestbak-checker-YYYY-MM-DD.log`
- Bewaard: 90 dagen, daarna automatisch verwijderd

## Uitgesloten nummers

Locatie: `data\excluded_numbers.json`
Nummers worden automatisch uitgesloten na 3 mislukte pogingen. Handmatig te bewerken met Kladblok.
