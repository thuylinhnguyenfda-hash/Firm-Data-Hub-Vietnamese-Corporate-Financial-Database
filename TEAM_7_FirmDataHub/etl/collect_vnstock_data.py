# =============================================================================
# FETCH FINANCIAL DATA FROM VNSTOCK LIBRARY
# Variables collected for the period 2020–2024
#
# Variables NOT available via vnstock (excluded):
#   1.  Managerial/Inside ownership
#   2.  State ownership
#   3.  Institutional ownership
#   4.  Foreign ownership
#   11. Value of intangible assets
#   13. Consumption of raw material
#   15. Work-in-progress goods purchase
#   16. Outside manufacturing expenses
#   17. Production cost
#   18. R&D
#   19. Product innovation
#   20. Process innovation
#   35. EPS (Earnings per share) 
#   36. Number of employees
#   37. Net plant, property and equipment 
# Requirements:
#   pip install vnstock pandas
# =============================================================================

from vnstock import Vnstock
import pandas as pd
import numpy as np
import re

# ------------------------------------------------------------------------------
# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------

# Change the stock ticker here to apply to the entire script
SYMBOL = "MST"

# Year range to fetch data
YEARS = [2020, 2021, 2022, 2023, 2024]

# Number format: no thousands separator, decimals rounded to 6 digits
pd.options.display.float_format = '{:.6f}'.format
pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", None)

# Initialize stock object (source='VCI' for financial statements)
stock = Vnstock().stock(symbol=SYMBOL, source='VCI')


# ==============================================================================
# LOAD RAW DATA ONCE — REUSED ACROSS MULTIPLE VARIABLES
# ==============================================================================

# Income statement
income_statement = stock.finance.income_statement(period='year')

# Balance sheet
balance_sheet = stock.finance.balance_sheet(period='year')

# Cash flow statement
cashflow = stock.finance.cash_flow(period='year')

# Company overview (source KBS to get founded_date)
stock_kbs = Vnstock().stock(symbol=SYMBOL, source='KBS')
overview = stock_kbs.company.overview()


# ==============================================================================
# VARIABLE 38: FIRM AGE
# Formula: fiscal_year - founded_year + 1
# ==============================================================================

# Extract founded year from the first year appearing in the 'history' column
# Regex searches for 4-digit years starting with 19xx or 20xx
def extract_founded_year(history_text):
    if not isinstance(history_text, str):
        return None
    match = re.search(r"\b(19|20)\d{2}\b", history_text)
    return int(match.group()) if match else None

founded_year = extract_founded_year(overview["history"].iloc[0])

if founded_year is None:
    raise ValueError(
        f"Could not extract founded year from 'history' column for ticker {SYMBOL}. "
        "Please check the overview data or manually assign the founded_year variable."
    )

firm_age = pd.DataFrame({
    'ticker':       SYMBOL,
    'yearReport':   YEARS,
    'founded_year': founded_year,
    'firm_age':     [yr - founded_year + 1 for yr in YEARS]
})

print("\n=== VARIABLE 38: FIRM AGE ===")
print(firm_age.to_string(index=False))


# ==============================================================================
# VARIABLE 5: TOTAL SALES REVENUE
# Source: income_statement → column 'Revenue (VND)'
# ==============================================================================

total_sales_revenue = (
    income_statement[income_statement['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Revenue (Bn. VND)']]
    .rename(columns={'Revenue (Bn. VND)': 'Revenue (VND)'})
    .sort_values('yearReport')
)

print("\n=== VARIABLE 5: TOTAL SALES REVENUE ===")
print(total_sales_revenue.to_string(index=False))


# ==============================================================================
# VARIABLE 6: TOTAL SHARES OUTSTANDING
# Source: balance_sheet → column 'Common shares (VND)'
# Par value per share = 10,000 VND
# If value > 1e6 it is already in VND, otherwise multiply by 1e9 to convert from Bn. VND to VND
# ==============================================================================

bs_5y = balance_sheet[balance_sheet['yearReport'].isin(YEARS)].copy()
cs = bs_5y['Common shares (Bn. VND)']
bs_5y['CommonShares_VND'] = np.where(cs > 1e6, cs, cs * 1e9)
bs_5y['TotalShares'] = (bs_5y['CommonShares_VND'] / 10000).round().astype(int)

total_shares = bs_5y[['ticker', 'yearReport', 'TotalShares']].sort_values('yearReport')

print("\n=== VARIABLE 6: TOTAL SHARES OUTSTANDING ===")
print(total_shares.to_string(index=False))


# ==============================================================================
# VARIABLE 7: NET SALES REVENUE
# Source: income_statement → column 'Net Sales'
# ==============================================================================

net_sales = (
    income_statement[income_statement['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Net Sales']]
    .sort_values('yearReport')
)

print("\n=== VARIABLE 7: NET SALES REVENUE ===")
print(net_sales.to_string(index=False))


# ==============================================================================
# VARIABLE 8: TOTAL ASSETS
# Source: balance_sheet → column 'TOTAL ASSETS (VND)'
# ==============================================================================

total_assets = (
    balance_sheet[balance_sheet['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'TOTAL ASSETS (Bn. VND)']]
    .rename(columns={'TOTAL ASSETS (Bn. VND)': 'TOTAL ASSETS (VND)'})
    .sort_values('yearReport')
)

print("\n=== VARIABLE 8: TOTAL ASSETS ===")
print(total_assets.to_string(index=False))


# ==============================================================================
# VARIABLE 9: SELLING EXPENSES
# Source: income_statement → column 'Selling Expenses'
# ==============================================================================

selling_expenses = (
    income_statement[income_statement['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Selling Expenses']]
    .sort_values('yearReport')
    .copy()
)
selling_expenses['Selling Expenses'] = selling_expenses['Selling Expenses'].abs()

print("\n=== VARIABLE 9: SELLING EXPENSES ===")
print(selling_expenses.to_string(index=False))


# ==============================================================================
# VARIABLE 10: GENERAL AND ADMINISTRATIVE EXPENDITURE
# Source: income_statement → column 'General & Admin Expenses'
# ==============================================================================

general_admin = (
    income_statement[income_statement['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'General & Admin Expenses']]
    .sort_values('yearReport')
    .copy()
)
general_admin['General & Admin Expenses'] = general_admin['General & Admin Expenses'].abs()

print("\n=== VARIABLE 10: GENERAL AND ADMINISTRATIVE EXPENDITURE ===")
print(general_admin.to_string(index=False))


# ==============================================================================
# VARIABLE 12: MANUFACTURING OVERHEAD (INDIRECT COST) — APPROXIMATION
# Cannot separate direct materials / direct labor from vnstock financial statements
# → Using Cost of Sales as a proxy
# ==============================================================================

manufacturing_overhead = (
    income_statement[income_statement['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Cost of Sales']]
    .rename(columns={'Cost of Sales': 'Manufacturing Overhead (proxy)'})
    .sort_values('yearReport')
    .copy()
)
manufacturing_overhead['Manufacturing Overhead (proxy)'] = manufacturing_overhead['Manufacturing Overhead (proxy)'].abs()

print("\n=== VARIABLE 12: MANUFACTURING OVERHEAD (proxy = Cost of Sales) ===")
print(manufacturing_overhead.to_string(index=False))


# ==============================================================================
# VARIABLE 13: NET OPERATING INCOME
# Source: income_statement → column 'Operating Profit/Loss'
# ==============================================================================

net_operating_income = (
    income_statement[income_statement['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Operating Profit/Loss']]
    .sort_values('yearReport')
)

print("\n=== VARIABLE 13: NET OPERATING INCOME ===")
print(net_operating_income.to_string(index=False))


# ==============================================================================
# VARIABLE 14: MERCHANDISE PURCHASE OF THE YEAR
# Formula: Merchandise Purchase = -COGS + Ending Inventory - Beginning Inventory
# Source: income_statement (COGS) + balance_sheet (Inventories)
# ==============================================================================

inc_cogs = (
    income_statement[income_statement['yearReport'].between(2019, 2024)]
    [['yearReport', 'Cost of Sales']]
    .rename(columns={'yearReport': 'year', 'Cost of Sales': 'cogs'})
)

bs_inv = (
    balance_sheet[balance_sheet['yearReport'].between(2019, 2024)]
    [['yearReport', 'Inventories, Net (Bn. VND)']]
    .rename(columns={'yearReport': 'year', 'Inventories, Net (Bn. VND)': 'inventory'})
)

merch_df = (
    pd.merge(inc_cogs, bs_inv, on='year', how='inner')
    .sort_values('year')
)

merch_df['begin_inventory'] = merch_df['inventory'].shift(1)
merch_df['merchandise_purchase'] = (
    -merch_df['cogs'] + merch_df['inventory'] - merch_df['begin_inventory']
)

merchandise_purchase = merch_df[merch_df['year'].isin(YEARS)][
    ['year', 'cogs', 'inventory', 'begin_inventory', 'merchandise_purchase']
]

print("\n=== VARIABLE 14: MERCHANDISE PURCHASE OF THE YEAR ===")
print(merchandise_purchase.to_string(index=False))


# ==============================================================================
# VARIABLE 22: NET INCOME
# Source: income_statement → column 'Net Profit For the Year'
# ==============================================================================

net_income = (
    income_statement[income_statement['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Net Profit For the Year']]
    .sort_values('yearReport')
)

print("\n=== VARIABLE 22: NET INCOME ===")
print(net_income.to_string(index=False))


# ==============================================================================
# VARIABLE 23: TOTAL SHAREHOLDERS' EQUITY
# Source: balance_sheet → column "OWNER'S EQUITY (VND)"
# ==============================================================================

total_equity = (
    balance_sheet[balance_sheet['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', "OWNER'S EQUITY(Bn.VND)"]]
    .rename(columns={"OWNER'S EQUITY(Bn.VND)": "Total shareholders equity (VND)"})
    .sort_values('yearReport')
)

print("\n=== VARIABLE 23: TOTAL SHAREHOLDERS' EQUITY ===")
print(total_equity.to_string(index=False))


# ==============================================================================
# VARIABLE 24: MARKET VALUE OF EQUITY
# Formula: Year-end closing price × Total shares outstanding
# ==============================================================================

# Fetch price history from KBS source (stock_kbs initialized earlier)
price_hist = stock_kbs.quote.history(start='2019-01-01', end='2024-12-31', interval='1D')
price_hist['time'] = pd.to_datetime(price_hist['time'])
price_hist['year'] = price_hist['time'].dt.year

# Get closing price of the last trading day of each year (convert to VND)
year_end_price = (
    price_hist.sort_values('time')
    .groupby('year')
    .tail(1)
    .copy()
)
year_end_price['close_vnd'] = year_end_price['close'] * 1000
year_end_price = year_end_price[year_end_price['year'].isin(YEARS)][['year', 'time', 'close_vnd']]

# Merge with shares outstanding (from variable 6)
shares_map = (
    total_shares
    .rename(columns={'yearReport': 'year'})
    [['year', 'TotalShares']]
)
market_value_df = year_end_price.merge(shares_map, on='year')
market_value_df['Market value of equity (VND)'] = (
    market_value_df['close_vnd'] * market_value_df['TotalShares']
)

market_value = market_value_df[['year', 'time', 'close_vnd', 'TotalShares', 'Market value of equity (VND)']]

print("\n=== VARIABLE 24: MARKET VALUE OF EQUITY ===")
print(market_value.to_string(index=False))


# ==============================================================================
# VARIABLE 25: TOTAL LIABILITIES
# Source: balance_sheet → column 'Total liabilities (VND)'
# ==============================================================================

total_liabilities = (
    balance_sheet[balance_sheet['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'LIABILITIES (Bn. VND)']]
    .rename(columns={'LIABILITIES (Bn. VND)': 'Total liabilities (VND)'})
    .sort_values('yearReport')
)

print("\n=== VARIABLE 25: TOTAL LIABILITIES ===")
print(total_liabilities.to_string(index=False))


# ==============================================================================
# VARIABLE 26: NET CASH FROM OPERATING ACTIVITIES
# Source: cashflow → column 'Net cash inflows/outflows from operating activities'
# ==============================================================================

net_cfo = (
    cashflow[cashflow['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Net cash inflows/outflows from operating activities']]
    .rename(columns={
        'Net cash inflows/outflows from operating activities':
        'Net cash from operating activities'
    })
    .sort_values('yearReport')
)

print("\n=== VARIABLE 26: NET CASH FROM OPERATING ACTIVITIES ===")
print(net_cfo.to_string(index=False))


# ==============================================================================
# VARIABLE 27: CAPITAL EXPENDITURE (CAPEX)
# Source: cashflow → column 'Purchase of fixed assets'
# ==============================================================================

capex = (
    cashflow[cashflow['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Purchase of fixed assets']]
    .rename(columns={'Purchase of fixed assets': 'CAPEX'})
    .sort_values('yearReport')
    .copy()
)
capex['CAPEX'] = capex['CAPEX'].abs()

print("\n=== VARIABLE 27: CAPITAL EXPENDITURE (CAPEX) ===")
print(capex.to_string(index=False))


# ==============================================================================
# VARIABLE 28: CASH FLOWS FROM INVESTING ACTIVITIES
# Source: cashflow → column 'Net Cash Flows from Investing Activities'
# ==============================================================================

cfi = (
    cashflow[cashflow['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Net Cash Flows from Investing Activities']]
    .rename(columns={
        'Net Cash Flows from Investing Activities':
        'Cash flows from investing activities'
    })
    .sort_values('yearReport')
)

print("\n=== VARIABLE 28: CASH FLOWS FROM INVESTING ACTIVITIES ===")
print(cfi.to_string(index=False))


# ==============================================================================
# VARIABLE 29: CASH AND CASH EQUIVALENTS
# Source: cashflow → column 'Cash and Cash Equivalents at the end of period'
# ==============================================================================

cash_eq = (
    cashflow[cashflow['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Cash and Cash Equivalents at the end of period']]
    .rename(columns={
        'Cash and Cash Equivalents at the end of period':
        'Cash and cash equivalents'
    })
    .sort_values('yearReport')
)

print("\n=== VARIABLE 29: CASH AND CASH EQUIVALENTS ===")
print(cash_eq.to_string(index=False))


# ==============================================================================
# VARIABLE 30: LONG-TERM DEBT
# Source: balance_sheet → column 'Long-term debt (VND)'
# ==============================================================================

long_term_debt = (
    balance_sheet[balance_sheet['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Long-term borrowings (Bn. VND)']]
    .rename(columns={'Long-term borrowings (Bn. VND)': 'Long-term debt (VND)'})
    .sort_values('yearReport')
)

print("\n=== VARIABLE 30: LONG-TERM DEBT ===")
print(long_term_debt.to_string(index=False))


# ==============================================================================
# VARIABLE 31: CURRENT ASSETS
# Source: balance_sheet → column 'CURRENT ASSETS (VND)'
# ==============================================================================

current_assets = (
    balance_sheet[balance_sheet['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'CURRENT ASSETS (Bn. VND)']]
    .rename(columns={'CURRENT ASSETS (Bn. VND)': 'CURRENT ASSETS (VND)'})
    .sort_values('yearReport')
)

print("\n=== VARIABLE 31: CURRENT ASSETS ===")
print(current_assets.to_string(index=False))


# ==============================================================================
# VARIABLE 32: CURRENT LIABILITIES
# Source: balance_sheet → column 'Current liabilities (VND)'
# ==============================================================================

current_liabilities = (
    balance_sheet[balance_sheet['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Current liabilities (Bn. VND)']]
    .rename(columns={'Current liabilities (Bn. VND)': 'Current liabilities (VND)'})
    .sort_values('yearReport')
)

print("\n=== VARIABLE 32: CURRENT LIABILITIES ===")
print(current_liabilities.to_string(index=False))


# ==============================================================================
# VARIABLE 33: GROWTH RATIOS
# Net income growth: pct_change() of Net Profit For the Year
# Using 2019 as base year to calculate 2020 growth
# ==============================================================================

yrs_ext = [2019] + YEARS  # add 2019 as base year

# Net income growth
ni_df = (
    income_statement[income_statement['yearReport'].isin(yrs_ext)]
    [['yearReport', 'Net Profit For the Year']]
    .sort_values('yearReport')
    .copy()
)
ni_df['Net income growth'] = ni_df['Net Profit For the Year'].pct_change()

# Keep only YEARS (drop 2019 after growth is calculated)
net_income_growth = ni_df[ni_df['yearReport'].isin(YEARS)][['yearReport', 'Net Profit For the Year', 'Net income growth']]

print("\n=== VARIABLE 33: GROWTH RATIOS ===")
print("\n-- Net Income Growth --")
print(net_income_growth.to_string(index=False))


# ==============================================================================
# VARIABLE 34: TOTAL INVENTORY
# Source: balance_sheet → column 'Net Inventories'
# ==============================================================================

total_inventory = (
    balance_sheet[balance_sheet['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Net Inventories']]
    .sort_values('yearReport')
)

print("\n=== VARIABLE 34: TOTAL INVENTORY ===")
print(total_inventory.to_string(index=False))


# ==============================================================================
# VARIABLE 35: DIVIDEND PAYMENT
# Source: cashflow → column 'Dividends paid'
# ==============================================================================

dividend_payment = (
    cashflow[cashflow['yearReport'].isin(YEARS)]
    [['ticker', 'yearReport', 'Dividends paid']]
    .sort_values('yearReport')
    .copy()
)
dividend_payment['Dividends paid'] = dividend_payment['Dividends paid'].abs()

print("\n=== VARIABLE 35: DIVIDEND PAYMENT ===")
print(dividend_payment.to_string(index=False))
