import os
import mysql.connector
import pandas as pd

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
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "panel_latest.csv")

# -----------------------------------------------------------------------------
# EXPORT QUERY
# Maps internal DB column names to the canonical variable labels used in the
# project specification. share_price is intentionally excluded (QC use only).
# -----------------------------------------------------------------------------

EXPORT_QUERY = """
SELECT
    ticker                          AS 'StockCode',
    fiscal_year                     AS 'YearEnd',

    -- Metadata
    firm_age                        AS 'Firm age',
    employees_count                 AS 'Number of employees',

    -- Ownership (4 variables)
    managerial_inside_own           AS 'Managerial/Inside ownership',
    state_own                       AS 'State ownership',
    institutional_own               AS 'Institutional ownership',
    foreign_own                     AS 'Foreign ownership',

    -- Market (5 variables)
    shares_outstanding              AS 'Total share outstanding',
    market_value_equity             AS 'Market value of equity',
    dividend_cash_paid              AS 'Dividend payment',
    eps_basic                       AS 'EPS',

    -- Financial statement (23 variables)
    net_sales                       AS 'Net sales revenue',
    total_assets                    AS 'Total assets',
    selling_expenses                AS 'Selling expenses',
    general_admin_expenses          AS 'General and administrative expenditure',
    intangible_assets_net           AS 'Value of intangible assets',
    manufacturing_overhead          AS 'Manufacturing overhead (Indirect cost)',
    net_operating_income            AS 'Net operating income',
    raw_material_consumption        AS 'Consumption of raw material',
    merchandise_purchase_year       AS 'Merchandise purchase of the year',
    wip_goods_purchase              AS 'Work-in-progress goods purchase',
    outside_manufacturing_expenses  AS 'Outside manufacturing expenses',
    production_cost                 AS 'Production cost',
    rnd_expenses                    AS 'R&D',
    net_income                      AS 'Net income',
    total_equity                    AS 'Total shareholders equity',
    total_liabilities               AS 'Total liabilities',
    cash_and_equivalents            AS 'Cash and cash equivalents',
    long_term_debt                  AS 'Long-term debt',
    current_assets                  AS 'Current assets',
    current_liabilities             AS 'Current liabilities',
    growth_ratio                    AS 'Growth ratio',
    inventory                       AS 'Total inventory',
    net_ppe                         AS 'Net plant, property and equipment',

    -- Innovation (2 variables)
    product_innovation              AS 'Product innovation',
    process_innovation              AS 'Process innovation',

    -- Cash flow (3 variables)
    net_cfo                         AS 'Net cash from operating activities',
    capex                           AS 'Capital expenditure',
    net_cfi                         AS 'Cash flows from investing activities'

FROM vw_firm_panel_latest
ORDER BY ticker, fiscal_year
"""

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------

def export_panel():
    print("Connecting to database...")
    conn = mysql.connector.connect(**DB_CONFIG)

    print("Running export query...")
    df = pd.read_sql(EXPORT_QUERY, conn)
    conn.close()

    # Replace NULL with NaN to ensure a complete panel for downstream analysis
    df = df.fillna("NaN")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Export complete. Rows: {len(df)} | Columns: {len(df.columns)}")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    export_panel()