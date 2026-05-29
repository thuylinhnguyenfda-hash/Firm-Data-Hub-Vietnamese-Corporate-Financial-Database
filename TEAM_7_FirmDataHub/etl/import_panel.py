# ==========================================
# MASTER FACT ETL
# ==========================================

import os
import pandas as pd
import mysql.connector
from datetime import date
from decimal import Decimal, InvalidOperation

from create_snapshot import create_snapshot

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------

DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "YOUR_PASSWORD_HERE",   # Replace with your MySQL password
    "database": "vn_firm_panel"
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_DIR = os.path.join(BASE_DIR, "data")
EXCEL_PATH = os.path.join(EXCEL_DIR, "panel_2020_2024.xlsx")

CREATED_BY    = "team_7_etl"
SNAPSHOT_DATE = date(2026, 2, 10)
VERSION_TAG   = "v1"
CURRENCY_CODE = "VND"
UNIT_SCALE    = 1                       # All monetary values stored in VND (no scaling)
PRICE_REFERENCE = "close_year_end"

# Maps each domain to its source in dim_data_source
SOURCE_MAP = {
    "financial":  "BCTC_Audited",
    "cashflow":   "BCTC_Audited",
    "ownership":  "AnnualReport",
    "innovation": "AnnualReport",
    "meta":       "AnnualReport",
    "market":     "Vietstock",
}

# Column mappings: { db_column_name: excel_column_name (lowercased) }
FINANCIAL_COLUMNS = {
    "net_sales":                      "net sales revenue",
    "total_assets":                   "total assets",
    "selling_expenses":               "selling expenses",
    "general_admin_expenses":         "general and administrative expenditure",
    "intangible_assets_net":          "value of intangible assets",
    "manufacturing_overhead":         "manufacturing overhead (indirect cost)",
    "net_operating_income":           "net operating income",
    "raw_material_consumption":       "consumption of raw material",
    "merchandise_purchase_year":      "merchandise purchase of the year",
    "wip_goods_purchase":             "work-in-progess goods purchase",
    "outside_manufacturing_expenses": "outside manufacturing expenses",
    "production_cost":                "production cost",
    "rnd_expenses":                   "r&d",
    "net_income":                     "net income",
    "total_equity":                   "total shareholders' equity",
    "total_liabilities":              "total liabilities",
    "cash_and_equivalents":           "cash and cash equivalent",
    "long_term_debt":                 "long-term debt",
    "current_assets":                 "current assets",
    "current_liabilities":            "current liabilities",
    "growth_ratio":                   "growth ratio",
    "inventory":                      "total inventory",
    "net_ppe":                        "net plant, property and equipment",
}

CASHFLOW_COLUMNS = {
    "net_cfo": "net cash from operating activities",
    "capex":   "capital expenditure",
    "net_cfi": "cash flows from investing activities",
}

OWNERSHIP_COLUMNS = {
    "managerial_inside_own": "managerial/inside ownership",
    "state_own":             "state ownership",
    "institutional_own":     "institutional ownership",
    "foreign_own":           "foreign ownership",
}

INNOVATION_COLUMNS = {
    "product_innovation": "product innovation",
    "process_innovation": "process innovation",
}

META_COLUMNS = {
    "employees_count": "number of employees",
    "firm_age":        "firm age",
}

MARKET_COLUMNS = {
    "shares_outstanding": "total share outstanding",
    "share_price":        "share price",
    "market_value_equity": "market value of equity",
    "dividend_cash_paid": "divident payment",
    "eps_basic":          "eps",
}


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise DataFrame column names to lowercase with single spaces."""
    df.columns = (
        df.columns.str.strip()
          .str.lower()
          .str.replace("\n", " ", regex=False)
          .str.replace(r"\s+", " ", regex=True)
    )
    return df


def safe(value):
    """Return None if value is NaN/None, otherwise return value as-is."""
    return None if pd.isna(value) else value


def build_firm_cache(cursor) -> dict:
    """Return a dict mapping ticker -> firm_id from dim_firm."""
    cursor.execute("SELECT ticker, firm_id FROM dim_firm")
    return {row[0]: row[1] for row in cursor.fetchall()}


def build_source_cache(cursor) -> dict:
    """Return a dict mapping source_name -> source_id from dim_data_source."""
    cursor.execute("SELECT source_name, source_id FROM dim_data_source")
    return {row[0]: row[1] for row in cursor.fetchall()}


def get_or_create_snapshot(snapshot_cache: dict, conn, source_name: str, fiscal_year: int) -> int:
    """
    Return the snapshot_id for (source_name, fiscal_year), creating it if needed.
    Results are cached in snapshot_cache to avoid redundant DB calls.
    """
    key = (source_name, fiscal_year)
    if key not in snapshot_cache:
        snapshot_cache[key] = create_snapshot(
            conn=conn,
            source_name=source_name,
            fiscal_year=fiscal_year,
            snapshot_date=SNAPSHOT_DATE,
            version_tag=VERSION_TAG,
            created_by=CREATED_BY
        )
    return snapshot_cache[key]


def normalize_value(v):
    """
    Convert a value to Decimal for consistent numeric comparison.
    Returns None for null values; returns the original string for non-numerics.
    """
    if v is None:
        return None
    try:
        return Decimal(str(v).strip())
    except InvalidOperation:
        return str(v).strip()


def log_value_change(cursor, firm_id: int, fiscal_year: int, table_name: str,
                     column_name: str, new_value, current_snapshot_id: int):
    """
    Compare new_value against the most recent prior snapshot for the same
    (firm_id, fiscal_year) and log any differences to fact_value_override_log.
    Skips logging on the first import (no prior snapshot to compare against).
    """
    try:
        cursor.execute(
            f"""
            SELECT `{column_name}`
            FROM   `{table_name}`
            WHERE  firm_id     = %s
              AND  fiscal_year = %s
              AND  snapshot_id < %s
            ORDER BY snapshot_id DESC
            LIMIT 1
            """,
            (firm_id, fiscal_year, current_snapshot_id)
        )
        result = cursor.fetchone()
    except Exception:
        return  # Column does not exist in this table — skip

    if result is None:
        return  # No prior snapshot — first import, nothing to compare

    old_value = result[0]

    if normalize_value(old_value) == normalize_value(new_value):
        return  # Value unchanged — no log entry needed

    cursor.execute(
        """
        INSERT INTO fact_value_override_log
            (firm_id, fiscal_year, table_name, column_name,
             old_value, new_value, reason, changed_by, changed_at)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """,
        (
            firm_id, fiscal_year, table_name, column_name,
            str(old_value).strip() if old_value is not None else None,
            str(new_value).strip() if new_value is not None else None,
            "Auto-detected change between import versions",
            CREATED_BY
        )
    )


def build_fact_values(cursor, firm_id: int, fiscal_year: int, row: pd.Series,
                      column_mapping: dict, table_name: str, snapshot_id: int) -> dict:
    """
    Extract values from the Excel row using column_mapping, log any changes
    vs. the prior snapshot, and return a dict of { db_column: value }.
    """
    values = {}
    for db_col, excel_col in column_mapping.items():
        value = safe(row.get(excel_col))
        log_value_change(cursor, firm_id, fiscal_year, table_name, db_col, value, snapshot_id)
        values[db_col] = value
    return values


def build_evidence_note(product_innovation, process_innovation) -> str:
    """
    Generate a human-readable evidence note for fact_innovation_year
    based on the two dummy indicators.
    """
    p = int(product_innovation) if pd.notna(product_innovation) else 0
    r = int(process_innovation) if pd.notna(process_innovation) else 0

    if p == 1 and r == 1:
        return "Product and process innovation reported"
    if p == 1:
        return "Product innovation reported (new product/line launched)"
    if r == 1:
        return "Process innovation reported (new manufacturing process implemented)"
    return "No innovation reported"


# -----------------------------------------------------------------------------
# MAIN ETL
# -----------------------------------------------------------------------------

def main():
    # Load Excel (row 0 is a header offset; actual headers are on row 1)
    df = pd.read_excel(EXCEL_PATH, skiprows=1)
    df = clean_columns(df)
    df = df.rename(columns={"stockcode": "ticker", "yearend": "fiscal_year"})

    conn   = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(buffered=True)

    firm_cache     = build_firm_cache(cursor)
    source_cache   = build_source_cache(cursor)
    snapshot_cache = {}

    # Counters for summary report
    counts = {domain: 0 for domain in SOURCE_MAP}
    counts["skipped_missing_ticker"] = 0

    try:
        for _, row in df.iterrows():
            ticker      = str(row["ticker"]).strip()
            fiscal_year = int(row["fiscal_year"])

            firm_id = firm_cache.get(ticker)
            if firm_id is None:
                print(f"  [SKIP] Ticker not found in dim_firm: '{ticker}'")
                counts["skipped_missing_ticker"] += 1
                continue

            # -----------------------------------------------------------------
            # 1. FINANCIAL
            # -----------------------------------------------------------------
            snapshot_id = get_or_create_snapshot(snapshot_cache, conn, SOURCE_MAP["financial"], fiscal_year)
            v = build_fact_values(cursor, firm_id, fiscal_year, row, FINANCIAL_COLUMNS, "fact_financial_year", snapshot_id)

            cursor.execute(
                """
                INSERT INTO fact_financial_year
                    (firm_id, fiscal_year, snapshot_id, unit_scale, currency_code,
                     net_sales, total_assets, selling_expenses, general_admin_expenses,
                     intangible_assets_net, manufacturing_overhead, net_operating_income,
                     raw_material_consumption, merchandise_purchase_year, wip_goods_purchase,
                     outside_manufacturing_expenses, production_cost, rnd_expenses,
                     net_income, total_equity, total_liabilities, cash_and_equivalents,
                     long_term_debt, current_assets, current_liabilities, growth_ratio,
                     inventory, net_ppe, created_at)
                VALUES
                    (%s,%s,%s,%s,%s, %s,%s,%s,%s, %s,%s,%s, %s,%s,%s, %s,%s,%s,
                     %s,%s,%s,%s, %s,%s,%s,%s, %s,%s, NOW())
                ON DUPLICATE KEY UPDATE
                    unit_scale                     = VALUES(unit_scale),
                    currency_code                  = VALUES(currency_code),
                    net_sales                      = VALUES(net_sales),
                    total_assets                   = VALUES(total_assets),
                    selling_expenses               = VALUES(selling_expenses),
                    general_admin_expenses         = VALUES(general_admin_expenses),
                    intangible_assets_net          = VALUES(intangible_assets_net),
                    manufacturing_overhead         = VALUES(manufacturing_overhead),
                    net_operating_income           = VALUES(net_operating_income),
                    raw_material_consumption       = VALUES(raw_material_consumption),
                    merchandise_purchase_year      = VALUES(merchandise_purchase_year),
                    wip_goods_purchase             = VALUES(wip_goods_purchase),
                    outside_manufacturing_expenses = VALUES(outside_manufacturing_expenses),
                    production_cost                = VALUES(production_cost),
                    rnd_expenses                   = VALUES(rnd_expenses),
                    net_income                     = VALUES(net_income),
                    total_equity                   = VALUES(total_equity),
                    total_liabilities              = VALUES(total_liabilities),
                    cash_and_equivalents           = VALUES(cash_and_equivalents),
                    long_term_debt                 = VALUES(long_term_debt),
                    current_assets                 = VALUES(current_assets),
                    current_liabilities            = VALUES(current_liabilities),
                    growth_ratio                   = VALUES(growth_ratio),
                    inventory                      = VALUES(inventory),
                    net_ppe                        = VALUES(net_ppe)
                """,
                (
                    firm_id, fiscal_year, snapshot_id, UNIT_SCALE, CURRENCY_CODE,
                    v["net_sales"], v["total_assets"], v["selling_expenses"], v["general_admin_expenses"],
                    v["intangible_assets_net"], v["manufacturing_overhead"], v["net_operating_income"],
                    v["raw_material_consumption"], v["merchandise_purchase_year"], v["wip_goods_purchase"],
                    v["outside_manufacturing_expenses"], v["production_cost"], v["rnd_expenses"],
                    v["net_income"], v["total_equity"], v["total_liabilities"], v["cash_and_equivalents"],
                    v["long_term_debt"], v["current_assets"], v["current_liabilities"], v["growth_ratio"],
                    v["inventory"], v["net_ppe"]
                )
            )
            counts["financial"] += 1

            # -----------------------------------------------------------------
            # 2. CASH FLOW
            # -----------------------------------------------------------------
            snapshot_id = get_or_create_snapshot(snapshot_cache, conn, SOURCE_MAP["cashflow"], fiscal_year)
            v = build_fact_values(cursor, firm_id, fiscal_year, row, CASHFLOW_COLUMNS, "fact_cashflow_year", snapshot_id)

            cursor.execute(
                """
                INSERT INTO fact_cashflow_year
                    (firm_id, fiscal_year, snapshot_id, unit_scale, currency_code,
                     net_cfo, capex, net_cfi, created_at)
                VALUES
                    (%s,%s,%s,%s,%s, %s,%s,%s, NOW())
                ON DUPLICATE KEY UPDATE
                    unit_scale    = VALUES(unit_scale),
                    currency_code = VALUES(currency_code),
                    net_cfo       = VALUES(net_cfo),
                    capex         = VALUES(capex),
                    net_cfi       = VALUES(net_cfi)
                """,
                (firm_id, fiscal_year, snapshot_id, UNIT_SCALE, CURRENCY_CODE,
                 v["net_cfo"], v["capex"], v["net_cfi"])
            )
            counts["cashflow"] += 1

            # -----------------------------------------------------------------
            # 3. OWNERSHIP
            # -----------------------------------------------------------------
            snapshot_id = get_or_create_snapshot(snapshot_cache, conn, SOURCE_MAP["ownership"], fiscal_year)
            v = build_fact_values(cursor, firm_id, fiscal_year, row, OWNERSHIP_COLUMNS, "fact_ownership_year", snapshot_id)

            cursor.execute(
                """
                INSERT INTO fact_ownership_year
                    (firm_id, fiscal_year, snapshot_id,
                     managerial_inside_own, state_own, institutional_own, foreign_own,
                     note, created_at)
                VALUES
                    (%s,%s,%s, %s,%s,%s,%s, NULL, NOW())
                ON DUPLICATE KEY UPDATE
                    managerial_inside_own = VALUES(managerial_inside_own),
                    state_own             = VALUES(state_own),
                    institutional_own     = VALUES(institutional_own),
                    foreign_own           = VALUES(foreign_own)
                """,
                (firm_id, fiscal_year, snapshot_id,
                 v["managerial_inside_own"], v["state_own"], v["institutional_own"], v["foreign_own"])
            )
            counts["ownership"] += 1

            # -----------------------------------------------------------------
            # 4. INNOVATION
            # -----------------------------------------------------------------
            snapshot_id = get_or_create_snapshot(snapshot_cache, conn, SOURCE_MAP["innovation"], fiscal_year)
            v = build_fact_values(cursor, firm_id, fiscal_year, row, INNOVATION_COLUMNS, "fact_innovation_year", snapshot_id)

            source_id     = source_cache.get(SOURCE_MAP["innovation"])
            evidence_note = build_evidence_note(v["product_innovation"], v["process_innovation"])

            cursor.execute(
                """
                INSERT INTO fact_innovation_year
                    (firm_id, fiscal_year, snapshot_id,
                     product_innovation, process_innovation,
                     evidence_source_id, evidence_note, created_at)
                VALUES
                    (%s,%s,%s, %s,%s, %s,%s, NOW())
                ON DUPLICATE KEY UPDATE
                    product_innovation = VALUES(product_innovation),
                    process_innovation = VALUES(process_innovation),
                    evidence_source_id = VALUES(evidence_source_id),
                    evidence_note      = VALUES(evidence_note)
                """,
                (firm_id, fiscal_year, snapshot_id,
                 v["product_innovation"] or 0, v["process_innovation"] or 0,
                 source_id, evidence_note)
            )
            counts["innovation"] += 1

            # -----------------------------------------------------------------
            # 5. FIRM-YEAR METADATA
            # -----------------------------------------------------------------
            snapshot_id = get_or_create_snapshot(snapshot_cache, conn, SOURCE_MAP["meta"], fiscal_year)
            v = build_fact_values(cursor, firm_id, fiscal_year, row, META_COLUMNS, "fact_firm_year_meta", snapshot_id)

            cursor.execute(
                """
                INSERT INTO fact_firm_year_meta
                    (firm_id, fiscal_year, snapshot_id, employees_count, firm_age, created_at)
                VALUES
                    (%s,%s,%s, %s,%s, NOW())
                ON DUPLICATE KEY UPDATE
                    employees_count = VALUES(employees_count),
                    firm_age        = VALUES(firm_age)
                """,
                (firm_id, fiscal_year, snapshot_id, v["employees_count"], v["firm_age"])
            )
            counts["meta"] += 1

            # -----------------------------------------------------------------
            # 6. MARKET
            # -----------------------------------------------------------------
            snapshot_id = get_or_create_snapshot(snapshot_cache, conn, SOURCE_MAP["market"], fiscal_year)
            v = build_fact_values(cursor, firm_id, fiscal_year, row, MARKET_COLUMNS, "fact_market_year", snapshot_id)

            cursor.execute(
                """
                INSERT INTO fact_market_year
                    (firm_id, fiscal_year, snapshot_id,
                     shares_outstanding, price_reference, share_price,
                     market_value_equity, dividend_cash_paid, eps_basic,
                     currency_code, created_at)
                VALUES
                    (%s,%s,%s, %s,%s,%s, %s,%s,%s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    shares_outstanding  = VALUES(shares_outstanding),
                    price_reference     = VALUES(price_reference),
                    share_price         = VALUES(share_price),
                    market_value_equity = VALUES(market_value_equity),
                    dividend_cash_paid  = VALUES(dividend_cash_paid),
                    eps_basic           = VALUES(eps_basic),
                    currency_code       = VALUES(currency_code)
                """,
                (firm_id, fiscal_year, snapshot_id,
                 v["shares_outstanding"], PRICE_REFERENCE, v["share_price"],
                 v["market_value_equity"], v["dividend_cash_paid"], v["eps_basic"],
                 CURRENCY_CODE)
            )
            counts["market"] += 1

        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] ETL failed — transaction rolled back.\n{e}")
        raise

    finally:
        cursor.close()
        conn.close()

    # Summary
    print("\n" + "=" * 50)
    print("ETL COMPLETE")
    print("=" * 50)
    for domain, count in counts.items():
        label = domain.replace("_", " ").title()
        print(f"  {label:<30} : {count}")
    print("=" * 50)


if __name__ == "__main__":
    main()