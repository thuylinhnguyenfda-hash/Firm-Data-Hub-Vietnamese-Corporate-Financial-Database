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
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "qc_report.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configurable thresholds
GROWTH_MIN        = -5.0   # Lower bound for growth_ratio (Rule 5)
GROWTH_MAX        =  5.0    # Upper bound for growth_ratio (Rule 5)
MARKET_TOLERANCE  =  0.05   # Allowed relative deviation for market value (Rule 6)


# -----------------------------------------------------------------------------
# DATA LOADING
# -----------------------------------------------------------------------------

def load_panel_with_share_price() -> pd.DataFrame:
    """
    Load the latest panel snapshot from vw_firm_panel_latest and join
    share_price from fact_market_year. share_price is excluded from the view
    but is required for Rule 6 (market value consistency check).
    """
    conn = mysql.connector.connect(**DB_CONFIG)

    query = """
        SELECT
            v.*,
            fm.share_price
        FROM vw_firm_panel_latest v
        JOIN dim_firm d ON v.ticker = d.ticker
        LEFT JOIN (
            SELECT m.*
            FROM fact_market_year m
            INNER JOIN (
                SELECT firm_id, fiscal_year, MAX(snapshot_id) AS max_snapshot_id
                FROM   fact_market_year
                GROUP BY firm_id, fiscal_year
            ) latest
                ON  m.firm_id     = latest.firm_id
                AND m.fiscal_year = latest.fiscal_year
                AND m.snapshot_id = latest.max_snapshot_id
        ) fm
            ON  fm.firm_id     = d.firm_id
            AND fm.fiscal_year = v.fiscal_year
    """

    df = pd.read_sql(query, conn)
    conn.close()
    return df


# -----------------------------------------------------------------------------
# RULE FUNCTIONS
# Each function returns True if the value FAILS the rule (i.e. is an error).
# -----------------------------------------------------------------------------

def fails_ownership_range(value) -> bool:
    """Rule 1: Ownership ratio must be in [0.0, 1.0]."""
    return pd.notna(value) and (value < 0.0 or value > 1.0)


def fails_positive(value) -> bool:
    """Rule 2: Value must be strictly greater than zero."""
    return pd.notna(value) and value <= 0


def fails_non_negative(value) -> bool:
    """Rules 3 & 4: Value must be >= 0."""
    return pd.notna(value) and value < 0


def fails_growth_range(value) -> bool:
    """Rule 5: Growth ratio must be in [GROWTH_MIN, GROWTH_MAX]."""
    return pd.notna(value) and (value < GROWTH_MIN or value > GROWTH_MAX)


def fails_market_consistency(shares, price, market_value) -> bool:
    """
    Rule 6: Market value must be within MARKET_TOLERANCE of shares * price.
    Returns False (no error) if any input is null or expected value is zero.
    """
    if pd.isna(shares) or pd.isna(price) or pd.isna(market_value):
        return False
    expected = shares * price
    if expected == 0:
        return False
    return abs(market_value - expected) / expected > MARKET_TOLERANCE


# -----------------------------------------------------------------------------
# MAIN QC LOGIC
# -----------------------------------------------------------------------------

def run_qc():
    print("Loading latest panel data...")
    df = load_panel_with_share_price()

    errors = []

    print(f"Running QC checks on {len(df)} firm-year observations...\n")

    for _, row in df.iterrows():
        ticker      = row.get("ticker")
        fiscal_year = row.get("fiscal_year")

        # Rule 1 — Ownership ratios in [0, 1]
        for field in ("managerial_inside_own", "state_own", "institutional_own", "foreign_own"):
            if fails_ownership_range(row.get(field)):
                errors.append({
                    "ticker":      ticker,
                    "fiscal_year": fiscal_year,
                    "rule":        "Rule 1",
                    "field_name":  field,
                    "error_type":  "INVALID_RANGE",
                    "value":       row.get(field),
                    "message":     f"{field} = {row.get(field):.4f} is outside [0.0, 1.0]"
                })

        # Rule 2 — shares_outstanding > 0
        if fails_positive(row.get("shares_outstanding")):
            errors.append({
                "ticker":      ticker,
                "fiscal_year": fiscal_year,
                "rule":        "Rule 2",
                "field_name":  "shares_outstanding",
                "error_type":  "INVALID_VALUE",
                "value":       row.get("shares_outstanding"),
                "message":     "shares_outstanding must be > 0"
            })

        # Rule 3 — total_assets >= 0
        if fails_non_negative(row.get("total_assets")):
            errors.append({
                "ticker":      ticker,
                "fiscal_year": fiscal_year,
                "rule":        "Rule 3",
                "field_name":  "total_assets",
                "error_type":  "NEGATIVE_VALUE",
                "value":       row.get("total_assets"),
                "message":     "total_assets cannot be negative"
            })

        # Rule 4 — current_liabilities >= 0
        if fails_non_negative(row.get("current_liabilities")):
            errors.append({
                "ticker":      ticker,
                "fiscal_year": fiscal_year,
                "rule":        "Rule 4",
                "field_name":  "current_liabilities",
                "error_type":  "NEGATIVE_VALUE",
                "value":       row.get("current_liabilities"),
                "message":     "current_liabilities cannot be negative"
            })

        # Rule 5 — growth_ratio in [GROWTH_MIN, GROWTH_MAX]
        if fails_growth_range(row.get("growth_ratio")):
            errors.append({
                "ticker":      ticker,
                "fiscal_year": fiscal_year,
                "rule":        "Rule 5",
                "field_name":  "growth_ratio",
                "error_type":  "OUT_OF_RANGE",
                "value":       row.get("growth_ratio"),
                "message":     f"growth_ratio = {row.get('growth_ratio'):.4f} is outside [{GROWTH_MIN}, {GROWTH_MAX}]"
            })

        # Rule 6 — market_value_equity consistent with shares * share_price
        if fails_market_consistency(
            row.get("shares_outstanding"),
            row.get("share_price"),
            row.get("market_value_equity")
        ):
            expected = row.get("shares_outstanding") * row.get("share_price")
            errors.append({
                "ticker":      ticker,
                "fiscal_year": fiscal_year,
                "rule":        "Rule 6",
                "field_name":  "market_value_equity",
                "error_type":  "INCONSISTENT_VALUE",
                "value":       row.get("market_value_equity"),
                "message":     (
                    f"market_value_equity = {row.get('market_value_equity'):,.0f} "
                    f"deviates > {MARKET_TOLERANCE:.0%} from "
                    f"shares_outstanding × share_price = {expected:,.0f}"
                )
            })

    # -------------------------------------------------------------------------
    # EXPORT REPORT
    # -------------------------------------------------------------------------

    error_df = pd.DataFrame(
        errors,
        columns=["ticker", "fiscal_year", "rule", "field_name", "error_type", "value", "message"]
    )

    error_df.to_csv(OUTPUT_PATH, index=False)

    print(f"QC complete. Total errors found: {len(error_df)}")
    print(f"Report saved to: {OUTPUT_PATH}")

    if not error_df.empty:
        print("\nError summary by rule:")
        rule_counts = error_df.groupby("rule")["ticker"].count()
        for rule, count in rule_counts.items():
            label = "error" if count == 1 else "errors"
            print(f"- {rule}: {count} {label}")

if __name__ == "__main__":
    run_qc()