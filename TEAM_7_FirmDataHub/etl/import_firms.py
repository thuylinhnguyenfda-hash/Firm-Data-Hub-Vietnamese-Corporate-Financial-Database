import os
import pandas as pd
import mysql.connector

# ===============================
# CONFIG
# ===============================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_PASSWORD_HERE", # Enter your MySQL root password
    "database": "vn_firm_panel"
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_DIR = os.path.join(BASE_DIR, "data")
EXCEL_PATH = os.path.join(EXCEL_DIR, "firm.xlsx")

BATCH_SIZE = 100  # commit after every N rows


# ===============================
# DB HELPERS
# ===============================

def get_exchange_id(cursor, exchange_code):
    cursor.execute(
        "SELECT exchange_id FROM dim_exchange WHERE exchange_code = %s",
        (exchange_code,)
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Exchange code not found: {exchange_code}")
    return row[0]


def get_industry_l2_id(cursor, industry_name):
    cursor.execute(
        "SELECT industry_l2_id FROM dim_industry_l2 WHERE industry_l2_name = %s",
        (industry_name,)
    )
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Industry L2 not found: {industry_name}")
    return row[0]


def firm_exists(cursor, ticker):
    cursor.execute(
        "SELECT firm_id FROM dim_firm WHERE ticker = %s",
        (ticker,)
    )
    return cursor.fetchone()


def get_next_firm_id(cursor):
    """
    FIX #2: Use SELECT ... FOR UPDATE to avoid race conditions when running concurrently.
    The safest approach is to use AUTO_INCREMENT in the DDL.
    If dim_firm already has AUTO_INCREMENT, remove this function and drop firm_id from INSERT.
    """
    cursor.execute("SELECT COALESCE(MAX(firm_id), 0) + 1 FROM dim_firm FOR UPDATE")
    return cursor.fetchone()[0]


def safe_int(value):
    """Convert NaN/None to None, otherwise return as int."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return int(value)


def safe_str(value, default=None):
    """Convert NaN to default, otherwise return as str."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    return str(value).strip()


# ===============================
# MAIN ETL
# ===============================

def main():
    # Read Excel
    df = pd.read_excel(EXCEL_PATH)
    df.columns = df.columns.str.strip()

    conn = mysql.connector.connect(**DB_CONFIG)
    # FIX #8: use buffered=True to avoid "Unread result" errors
    cursor = conn.cursor(buffered=True)

    insert_sql = """
        INSERT INTO dim_firm (
            firm_id,
            ticker,
            company_name,
            exchange_id,
            industry_l2_id,
            founded_year,
            listed_year,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    update_sql = """
        UPDATE dim_firm
        SET
            company_name   = %s,
            exchange_id    = %s,
            industry_l2_id = %s,
            founded_year   = %s,
            listed_year    = %s,
            status         = %s,
            updated_at     = CURRENT_TIMESTAMP
        WHERE ticker = %s
    """

    # FIX #7: track counts for summary output
    n_insert = 0
    n_update = 0
    n_skip   = 0

    try:
        for i, (_, row) in enumerate(df.iterrows()):

            ticker = safe_str(row.get("ticker"))
            if not ticker:
                print(f"[SKIP] Row {i}: ticker is empty")
                n_skip += 1
                continue

            # FIX #4 + #3: handle NaN correctly for all fields
            company_name  = safe_str(row.get("company_name"))
            exchange_code = safe_str(row.get("exchange_code"))
            industry_name = safe_str(row.get("industry_l2_name"))
            founded_year  = safe_int(row.get("founded_year"))
            listed_year   = safe_int(row.get("listed_year"))
            # FIX #3: row.get("status") may return NaN, not "active"
            status = safe_str(row.get("status"), default="active")

            # FIX #5: catch lookup errors per row, skip instead of crashing the entire ETL
            try:
                exchange_id    = get_exchange_id(cursor, exchange_code)
                industry_l2_id = get_industry_l2_id(cursor, industry_name)
            except ValueError as e:
                print(f"[SKIP] {ticker}: {e}")
                n_skip += 1
                continue

            exists = firm_exists(cursor, ticker)

            if exists is None:
                # INSERT
                firm_id = get_next_firm_id(cursor)
                cursor.execute(
                    insert_sql,
                    (
                        firm_id,
                        ticker,
                        company_name,
                        exchange_id,
                        industry_l2_id,
                        founded_year,
                        listed_year,
                        status
                    )
                )
                print(f"[INSERT] {ticker}")
                n_insert += 1
            else:
                # UPDATE
                cursor.execute(
                    update_sql,
                    (
                        company_name,
                        exchange_id,
                        industry_l2_id,
                        founded_year,
                        listed_year,
                        status,
                        ticker
                    )
                )
                print(f"[UPDATE] {ticker}")
                n_update += 1

            # FIX #6: batch commit every BATCH_SIZE rows
            if (i + 1) % BATCH_SIZE == 0:
                conn.commit()
                print(f"  ... committed {i + 1} rows so far")

        # Commit the rest
        conn.commit()


    except Exception as e:
        conn.rollback()
        print(f"ETL FAILED: {e}")
        raise

    finally:
        cursor.close()
        conn.close()

    # FIX #7: print summary
    print("=" * 40)
    print("Import dim_firm completed successfully")
    print(f"  Inserted : {n_insert}")
    print(f"  Updated  : {n_update}")
    print(f"  Skipped  : {n_skip}")
    print("=" * 40)


if __name__ == "__main__":
    main()