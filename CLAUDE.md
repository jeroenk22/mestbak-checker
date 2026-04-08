# mestbak-checker - Claude Code Context

## Doel
Automatisch dagelijks WhatsApp berichten sturen naar klanten via de TextMeBot API.
Het script vraagt klanten hoeveel mestbakken zij de volgende werkdag klaar hebben staan.
Vervangt een handmatig proces waarbij een medewerker elke dag een SQL query draaide,
resultaat in Excel plakte, uploadde in een React tool en handmatig op verzenden klikte.

## Bedrijfscontext
- Bedrijf: Miedema Ophaaldienst B.V.
- Klanten zijn in NL, Belgie (alleen Vlaanderen) en Duitsland (NRW + Niedersachsen)
- Database: SQL Server in het interne netwerk, read-only rechten
- Berichten via: TextMeBot API (WhatsApp, eigen nummer gekoppeld)
- Eigen WhatsApp nummer: via `.env` ingesteld (ontvangt ook samenvattingsberichten)

## Repo hygiene
- Deze repository mag publiek blijven.
- Commit geen interne telefoonnummers, interne IP-adressen, database-namen, contactmailadressen of andere operationele identifiers.
- Gevoelige waarden horen alleen in `.env` of andere niet-getrackte lokale configuratie.
- Publieke documentatie gebruikt placeholders zoals `<db-server>`, `<db-naam>` en `<samenvattingsnummer>`.

## Technische stack
- Python 3.12+
- pyodbc (SQL Server via Windows Authentication)
- requests (TextMeBot API + Nager.Date feestdagen API)
- python-dotenv (.env configuratie)
- Windows Task Scheduler (dagelijkse uitvoering om 13:00)

## Projectstructuur
```
mestbak-checker/
|- main.py               Hoofdscript - Task Scheduler roept dit aan
|- config.py             Alle variabelen en .env laden
|- db.py                 SQL Server verbinding, laadt query uit sql/query.sql
|- messaging.py          TextMeBot API aanroepen
|- message_builder.py    Berichtteksten bouwen (NL/DE, dagdeel, feestdagscenario)
|- holidays.py           Feestdagen ophalen via Nager.Date API
|- exclude.py            Uitsluitlijst + failure tellers bijhouden
|- logger.py             Rotating dagelijkse logfiles
|- summary.py            Samenvattingsberichten naar eigen nummer
|- utils.py              Telefoonnummer normalisatie, uitsluitingsnotaties
|- run_tests.py          Alle unit tests uitvoeren (geen live berichten)
|- sql/
|  \- query.sql          SQL query voor klantgegevens (morgen)
|- api-docs/             Nager.Date API documentatie (referentie)
|- tests/
|  |- test_utils.py           Telefoonnummer normalisatie tests
|  |- test_message_builder.py Berichttekst tests alle scenario's
|  |- test_holidays.py        Feestdagenlogica tests (gemockte API)
|  |- test_messaging.py       Live berichten test naar eigen nummers
|  \- test_main.py            Dispatch-logica tests (resolve_number, dedup, fallback)
|- data/
|  |- excluded_numbers.json   Uitgesloten nummers (auto + handmatig)
|  \- failure_counts.json     Failure tellers per nummer
\- logs/
   \- mestbak-checker-YYYY-MM-DD.log
```

## Berichtenlogica

### Taaldetectie
- +31 -> Nederlands (NL)
- +32 -> Nederlands (BE, alleen Vlaanderen)
- +49 -> Duits (DE, alleen NRW + Niedersachsen)

### Feestdagscenario's (bepaald per klant op basis van landcode)
| Situatie | NL klant | BE klant | DE klant |
|---|---|---|---|
| Morgen gewone werkdag | Standaard + datum morgen | Standaard + datum morgen | Standaard + datum morgen |
| Morgen NL feestdag, BE/DE werkdag | Eerstvolgende werkdag | Melding NL feestdag + eerstvolgende werkdag | Melding NL feestdag + eerstvolgende werkdag (Duits) |
| Morgen BE/DE feestdag, NL werkdag | n.v.t. | Feestdagvariant (rijden we wel) | Feestdagvariant (rijden we wel) |
| Morgen BE/DE en NL feestdag | Eerstvolgende werkdag | Eerstvolgende werkdag | Eerstvolgende werkdag |
| Morgen weekend | Eerstvolgende werkdag (maandag) | Idem | Idem |

### Berichtvarianten (13:00 = altijd Goedemiddag / Guten Mittag)

**NL/BE normaal:**
```
Goedemiddag,

Weet u al hoeveel mestbakken u morgen/maandag (07-04) heeft?

Met vriendelijke groet,
Miedema Ophaaldienst B.V.
```

**BE feestdag, NL werkdag:**
```
Goedemiddag,

Heeft u morgen mestbakken klaar staan i.v.m. feestdag? Indien ja, hoeveel bakken heeft u dan klaar staan?

Met vriendelijke groet,
Miedema Ophaaldienst B.V.
```

**BE/NL feestdag, DE werkdag:**
```
Goedemiddag,

Vanwege de Nederlandse feestdag Koningsdag rijden wij morgen niet. Weet u al hoeveel mestbakken u woensdag (29-04) heeft?

Met vriendelijke groet,
Miedema Ophaaldienst B.V.
```

**DE normaal:**
```
Guten Mittag,

Wissen Sie schon, wie viele Kisten Sie morgen/Montag (07.04.2026) haben?

Mit freundlichen Gruessen,
Miedema Ophaaldienst B.V.
```

**DE feestdag, NL werkdag:**
```
Guten Mittag,

Haben Sie morgen Kisten bereitstehen aufgrund eines Feiertags? Wenn ja, wie viele Kisten haetten Sie bereit?

Mit freundlichen Gruessen,
Miedema Ophaaldienst B.V.
```

**NL feestdag, DE werkdag:**
```
Guten Mittag,

Aufgrund des niederlaendischen Feiertags Koningsdag fahren wir morgen nicht. Wissen Sie schon, wie viele Kisten Sie Dienstag (28.04.2026) haben?

Mit freundlichen Gruessen,
Miedema Ophaaldienst B.V.
```

### Datumnotatie
- NL/BE: dd-mm (bijv. 07-04)
- DE: dd.mm.yyyy (bijv. 07.04.2026)

### Dagdeel (op basis van SEND_HOUR in config.py)
- < 12 -> Goedemorgen / Guten Morgen
- 12-17 -> Goedemiddag / Guten Mittag
- >= 18 -> Goedenavond / Guten Abend

## Telefoonnummer logica
- LocMobile heeft voorkeur boven LocPhone
- Als mobile mislukt -> fallback naar LocPhone
- Failure tellers worden per nummer bijgehouden (niet per klant)
- Na 3 mislukkingen -> auto-exclude met klantgegevens als commentaar
- Deduplicatie op telefoonnummer (zelfde nummer krijgt maar 1 bericht per dag)

### Uitsluitingsnotaties (bewust niet verzenden, geen failure)
- Begint met `nul` -> nul-notatie (bijv. "nul-zes 43091465")
- Bevat `(alleen spoed)` -> alleen spoed notatie

### Ongeldige nummers (wel failure teller)
- Te lang/kort
- Onbekende landcode
- Rommel (bijv. "00467191026427475")

## Feestdagenlogica
- API: https://date.nager.at/api/v3/PublicHolidays/{year}/{country}
- Alleen `Public` feestdagen worden meegenomen
- NL: nationale feestdagen
- BE: nationale feestdagen
- DE: alleen NRW (NW) en Niedersachsen (NI) regio's
- Als vandaag een NL feestdag is -> script stopt volledig
- Als vandaag een BE/DE feestdag is -> alleen die klanten overgeslagen

## Samenvattingsberichten
- Einde van elke run: successen (apart bericht) + failures (apart bericht)
- Bij vroegtijdig afbreken: WhatsApp met reden
- Bij voltooiing: statistieken (verstuurd/mislukt/overgeslagen/duur)
- Te lange berichten worden automatisch gesplitst (max 3900 tekens)

## Cutoff en timing
- Normaal: 13:00 via Task Scheduler
- MAX_CUTOFF: 16:30 - na dit tijdstip stopt het script zonder te verzenden
- DELAY_BETWEEN_MESSAGES: 4 seconden (spam preventie WhatsApp)

## Testmodus
Zet `TEST_MODE=true` in `.env` om te testen zonder echte DB query.
Stuurt naar TEST_PHONE_NL, TEST_PHONE_BE, TEST_PHONE_DE.
Bevat testklanten voor: normaal, duplicaat, nul-notatie, alleen spoed.

## .env variabelen
```
TEXTMEBOT_API_KEY=        # TextMeBot API key
SUMMARY_PHONE=<samenvattingsnummer> # Eigen nummer voor samenvattingen
DB_SERVER=<db-server>
DB_NAME=<db-naam>
DB_CLIENT_NO=3582
DB_DRIVER=ODBC Driver 17 for SQL Server
TEST_MODE=false
TEST_PHONE_NL=+31612345678
TEST_PHONE_BE=+32498123456  # Zie .env.example voor formaat
TEST_PHONE_DE=+4917612345678
```

## Bekende data-eigenaardigheden in de database
- Sommige nummers bevatten tekst: "nul-zes 43091465", "nul6-27856048" -> bewuste uitsluiting
- Sommige nummers bevatten "(alleen spoed)" -> bewuste uitsluiting
- Nummers kunnen spaties, streepjes of haakjes bevatten -> utils.normalize_phone() handelt dit af
- LocPhone en LocMobile zijn varchar(100) in de database
- Klanten kunnen dubbel voorkomen in de query (zelfde telefoonnummer) -> deduplicatie in main.py
- SjOrderId = vaste herhalende klant (alleen deze krijgen een bericht)

## Openstaande punten / toekomstige verbeteringen
- Task Scheduler nog in te stellen op de Windows server
- Overwegen: officiele WhatsApp Business API voor meer betrouwbaarheid op lange termijn
