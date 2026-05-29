import mysql.connector
from datetime import date, datetime

# -----------------------------------------------------------------------------
# DATABASE CONFIG
# -----------------------------------------------------------------------------

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "YOUR_PASSWORD_HERE",   # Replace with your MySQL password
    "database": "vn_firm_panel"
}

# -----------------------------------------------------------------------------
# SNAPSHOT SETTINGS
# Change VERSION_TAG and SNAPSHOT_DATE when importing a new data version.
# -----------------------------------------------------------------------------

SNAPSHOT_DATE = date(2026, 2, 10)
VERSION_TAG   = "v1"

# Data sources and fiscal years to create snapshots for
SOURCES = ["BCTC_Audited", "Vietstock", "AnnualReport"]
YEARS   = range(2020, 2025)

# -----------------------------------------------------------------------------
# CORE FUNCTION
# -----------------------------------------------------------------------------

def create_snapshot(
    conn,
    source_name: str,
    fiscal_year: int,
    snapshot_date: date,
    version_tag: str,
    created_by: str = "team_7_etl"
) -> int:
   
    cursor = conn.cursor(dictionary=True)

    # Resolve source_name to source_id
    cursor.execute(
        "SELECT source_id FROM dim_data_source WHERE source_name = %s",
        (source_name,)
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Source not found in dim_data_source: '{source_name}'")
    source_id = row["source_id"]

    # Return existing snapshot if already present (idempotent)
    cursor.execute(
        """
        SELECT snapshot_id
        FROM   fact_data_snapshot
        WHERE  source_id   = %s
          AND  fiscal_year = %s
          AND  version_tag = %s
        """,
        (source_id, fiscal_year, version_tag)
    )
    row = cursor.fetchone()
    if row:
        return row["snapshot_id"]

    # Insert new snapshot record
    cursor.execute(
        """
        INSERT INTO fact_data_snapshot
            (snapshot_date, fiscal_year, source_id, version_tag, created_by, created_at)
        VALUES
            (%s, %s, %s, %s, %s, %s)
        """,
        (snapshot_date, fiscal_year, source_id, version_tag, created_by, datetime.now())
    )
    conn.commit()
    return cursor.lastrowid

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    conn = mysql.connector.connect(**DB_CONFIG)

    print(f"Creating snapshots — version: {VERSION_TAG}, date: {SNAPSHOT_DATE}\n")

    for source in SOURCES:
        for year in YEARS:
            snapshot_id = create_snapshot(
                conn=conn,
                source_name=source,
                fiscal_year=year,
                snapshot_date=SNAPSHOT_DATE,
                version_tag=VERSION_TAG
            )
            print(f"  ✔ {source} | {year} | snapshot_id = {snapshot_id}")

    conn.close()
    print("\nDone.")