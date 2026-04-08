"""
db.py - Database connectie en query voor mestbak-checker
Verbinding via Windows Authentication (ODBC Driver 17).
Query wordt geladen vanuit sql/query.sql.
"""

import os
from datetime import date, timedelta
import pyodbc
from logger import logger
from config import DB_SERVER, DB_NAME, DB_CLIENT_NO, DB_DRIVER, BASE_DIR
from utils import clean_field

SQL_FILE = os.path.join(BASE_DIR, "sql", "query.sql")


def get_connection():
    """Maak verbinding met SQL Server via Windows Authentication."""
    conn_str = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        "Trusted_Connection=yes;"
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=30)
        logger.debug(f"Database verbinding geslaagd: {DB_SERVER}/{DB_NAME}")
        return conn
    except pyodbc.Error as e:
        raise ConnectionError(f"Database verbinding mislukt ({DB_SERVER}): {e}")


def _load_query() -> str:
    """Laad de SQL query vanuit sql/query.sql en strip de DECLARE/SET regels.
    Python vult @Datum zelf in als parameter."""
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Verwijder DECLARE @Datum en SET @Datum regels + commentaarregels bovenaan
    query_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("DECLARE @Datum") or stripped.startswith("SET @Datum") \
                or stripped.startswith("DECLARE @ClientNo") or stripped.startswith("SET @ClientNo"):
            continue
        # Vervang @Datum en @ClientNo door ? voor pyodbc parameter binding
        query_lines.append(line.replace("@Datum", "?").replace("@ClientNo", "?"))

    return "".join(query_lines)


def get_customers_for_date(target_date: date) -> list[dict]:
    """
    Haal klanten op die gepland staan op target_date.
    Alleen klanten met een SjOrderId (vaste herhalende klanten).
    """
    date_str = target_date.strftime("%Y-%m-%d")

    try:
        query = _load_query()
        conn = get_connection()
        cursor = conn.cursor()
        # Twee parameters: MomentRTA >= ? en MomentRTA < DATEADD(DAY, 1, ?)
        cursor.execute(query, (date_str, date_str, DB_CLIENT_NO))
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        conn.close()

        customers = []
        for row in rows:
            customer = dict(zip(columns, row))
            customers.append({
                "order_id": customer.get("OrderId"),
                "sj_order_id": clean_field(customer.get("SjOrderId")),
                "name": clean_field(customer.get("LocName")),
                "street": clean_field(customer.get("LocStreet")),
                "zip": clean_field(customer.get("LocZip")),
                "city": clean_field(customer.get("LocCity")),
                "country": clean_field(customer.get("LocCountry")),
                "phone": clean_field(customer.get("LocPhone")),
                "mobile": clean_field(customer.get("LocMobile")),
                "moment_rta": customer.get("MomentRTA"),
            })

        logger.info(f"Database query: {len(customers)} klanten gevonden voor {date_str}")
        return customers

    except ConnectionError:
        raise
    except FileNotFoundError:
        raise ConnectionError(f"SQL bestand niet gevonden: {SQL_FILE}")
    except pyodbc.Error as e:
        raise ConnectionError(f"Database query mislukt: {e}")


def get_tomorrow_customers() -> list[dict]:
    """Haal klanten op voor morgen (standaard gebruik)."""
    tomorrow = date.today() + timedelta(days=1)
    return get_customers_for_date(tomorrow)
