# Firm-Data-Hub-Vietnamese-Corporate-Financial-Database
# TEAM_7_FirmDataHub

## Firm Data Hub – Corporate Data Storage & Processing Center (2020–2024)

---

## 1. Project Overview

A panel data management and storage system for 10 listed Vietnamese companies over the period 2020–2024, covering 38 variables across the following domains: ownership structure, market data, financial statements, cash flows, innovation, and firm-level metadata.

**Database:** MySQL  
**Processing Language:** Python 3  
**Data Version:** v1 (snapshot_date: 2026-02-10)

---

## 2. List of 10 Stock Tickers (Team 7)

| Ticker | Company Name                     | Exchange | Industry (L2)              |
| ------ | -------------------------------- | -------- | -------------------------- |
| GMD    | Gemadept                         | HOSE     | Hàng & Dịch vụ Công nghiệp |
| CII    | Hạ tầng Kỹ thuật TP.HCM          | HOSE     | Xây dựng và Vật liệu       |
| PVD    | Khoan Dầu khí PVDrilling         | HOSE     | Dầu khí                    |
| HAH    | Vận tải và Xếp dỡ Hải An         | HOSE     | Hàng & Dịch vụ Công nghiệp |
| HHV    | Đầu tư Hạ tầng Giao thông Đèo Cả | HOSE     | Xây dựng và Vật liệu       |
| HHS    | Đầu tư DV Hoàng Huy              | HOSE     | Ô tô và phụ tùng           |
| TCM    | Dệt may Thành Công               | HOSE     | Hàng cá nhân & Gia dụng    |
| LCG    | LIZEN                            | HOSE     | Xây dựng và Vật liệu       |
| VOS    | Vận tải Biển Việt Nam            | HOSE     | Hàng & Dịch vụ Công nghiệp |
| MST    | Đầu tư MST                       | HNX      | Xây dựng và Vật liệu       |

---

## 3. Directory Structure

```
TEAM_7_FirmDataHub/
│
├── sql/
│   └── schema_and_seed.sql           # Full schema + seed data + view
│
├── etl/
│   ├── import_firms.py               # Script A: Import firm master list
│   ├── create_snapshot.py            # Script B: Create data snapshots (versioning)
│   ├── import_panel.py               # Script C: Import 38-variable panel by year
│   ├── qc_checks.py                  # Script D: Data quality checks
│   ├── export_panel.py               # Script E: Export clean panel dataset
│   └── collect_vnstock_data.py       # Script F: Auto-collect data via vnstock
│
├── data/
│   ├── team_tickers.csv              # List of 10 team tickers
│   ├── firms.xlsx                    # Firm master list (10 companies)
│   └── panel_2020_2024.xlsx          # Panel data: 38 variables × 10 tickers × 5 years
│
├── outputs/
│   ├── qc_report.csv                 # Output of qc_checks.py
│   └── panel_latest.csv             # Output of export_panel.py
│
├── evidence/
│   ├── evidence_metadata.csv
│   ├── CII/
│   ├── GMD/
│   ├── HAH/
│   ├── HHS/
│   ├── HHV/
│   ├── LCG/
│   ├── MST/
│   ├── PVD/
│   ├── TCM/
│   └── VOS/
│
└── README.md
```

---

## 4. Installation Requirements

### 4.1 Software

- **MySQL** >= 8.0
- **Python** >= 3.8
- **pip packages:**

```bash
pip install mysql-connector-python pandas openpyxl
```

### 4.2 Database Connection Setup

Before running any Python script, open each file in `etl/` and update the `DB_CONFIG` section with your MySQL credentials:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "YOUR_PASSWORD_HERE",   # <-- Replace with your password
    "database": "vn_firm_panel"
}
```

Files that require password update: `import_firms.py`, `create_snapshot.py`, `import_panel.py`, `qc_checks.py`, `export_panel.py`.

---

## 5. Run Order

**Important:** Steps must be executed in the exact order below. Do not skip any step.

### Step 1 — Initialize the database schema

Open a MySQL client (Workbench, CLI, or DBeaver) and run the entire file:

```sql
SOURCE sql/schema_and_seed.sql;
```

This file will:

- Drop and recreate the `vn_firm_panel` database
- Create all DIM, FACT, and Audit tables
- Seed initial data for `dim_exchange`, `dim_industry_l2`, `dim_data_source`, and `dim_firm` (10 team companies)
- Create the `vw_firm_panel_latest` view

> ⚠️ The SQL file includes a `DROP DATABASE IF EXISTS` statement, which will wipe all existing data each time it is re-run. Only re-run Step 1 if you intend a full reset.

### Step 2 — Import the firm master list

```bash
python etl/import_firms.py
```

- Input: `data/firms.xlsx`
- Handles INSERT for new tickers or UPDATE if the ticker already exists
- Since `dim_firm` is seeded in Step 1, this script will run in UPDATE mode for the 10 existing companies

### Step 3 — Create snapshots

```bash
python etl/create_snapshot.py
```

- Creates snapshot records in `fact_data_snapshot` for 3 data sources × 5 years (2020–2024)
- Idempotent: running multiple times will not create duplicate records

### Step 4 — Import 38-variable panel data

```bash
python etl/import_panel.py
```

- Input: `data/panel_2020_2024.xlsx`
- Writes data to 6 fact tables: `fact_financial_year`, `fact_cashflow_year`, `fact_ownership_year`, `fact_market_year`, `fact_innovation_year`, `fact_firm_year_meta`
- Automatically skips (and logs) rows where the ticker is not found in `dim_firm`
- Uses `ON DUPLICATE KEY UPDATE` — safe to re-run

### Step 5 — Run data quality checks (QC)

```bash
python etl/qc_checks.py
```

- Output: `outputs/qc_report.csv`
- Applies 6 validation rules (see Section 8 for details)

### Step 6 — Export clean panel dataset

```bash
python etl/export_panel.py
```

- Output: `outputs/panel_latest.csv`
- Selects the latest snapshot for each firm-year from `vw_firm_panel_latest`

---

## 6. Data Sources

| Source                                          | Data Type                                                              | Collection Method                                                                                      |
| ----------------------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Audited Financial Statements** (BCTC_Audited) | Financial data, cash flows                                             | Manually collected from audited annual financial statements published on HOSE/HNX and company websites |
| **Vietstock** (Vietstock)                       | Stock price, market capitalization, dividends, EPS, shares outstanding | Manually retrieved from [vietstock.vn](https://vietstock.vn)                                           |
| **Annual Reports** (AnnualReport)               | Ownership structure, innovation activity, headcount, firm age          | Manually collected from annual reports published by each company                                       |

All data was entered **manually** into `data/panel_2020_2024.xlsx`.

---

## 7. Evidence

Evidences are place in this link because the file limit is 30mb so we couldn't add the evidence folder in the submission link.
https://drive.google.com/drive/folders/1iJ7BFi_BQjAdFDfH9TVTZF3TcwxXy7sb?usp=drive_link

### 7.1 Variables Collected via `collect_vnstock_data.py`

The following variables were retrieved programmatically using the `vnstock` Python library, which pulls data directly from VCI's financial statement API. The values have been cross-verified against the companies' official consolidate financial statements and annual reports and are confirmed to be accurate:

| Variable                                       | Source Table                       |
| ---------------------------------------------- | ---------------------------------- |
| Total sales revenue                            | Income Statement                   |
| Net sales revenue                              | Income Statement                   |
| Total assets                                   | Balance Sheet                      |
| Selling expenses                               | Income Statement                   |
| General & administrative expenditure           | Income Statement                   |
| Manufacturing overhead (proxy = Cost of Sales) | Income Statement                   |
| Net operating income                           | Income Statement                   |
| Merchandise purchase of the year               | Income Statement + Balance Sheet   |
| Net income                                     | Income Statement                   |
| Total shareholders' equity                     | Balance Sheet                      |
| Market value of equity                         | Price history × Shares outstanding |
| Total liabilities                              | Balance Sheet                      |
| Net cash from operating activities             | Cash Flow Statement                |
| Capital expenditure (CAPEX)                    | Cash Flow Statement                |
| Cash flows from investing activities           | Cash Flow Statement                |
| Cash and cash equivalents                      | Cash Flow Statement                |
| Long-term debt                                 | Balance Sheet                      |
| Current assets                                 | Balance Sheet                      |
| Current liabilities                            | Balance Sheet                      |
| Growth ratio (net income growth)               | Derived from Income Statement      |
| Total inventory                                | Balance Sheet                      |
| Dividend payment                               | Cash Flow Statement                |
| Total shares outstanding                       | Balance Sheet                      |
| Firm age                                       | Derived from company overview      |

> These variables are collected automatically and do not require manual screenshot evidence. The code in `etl/collect_vnstock_data.py` documents the exact column mappings and derivation logic for each variable.

### 7.2 Variables Collected Manually

The following variables could not be retrieved via `vnstock` and were manually collected from consolidated financial statements (CFS) or annual reports (AR). For each observation, a screenshot of the source page was captured and stored in the `evidence/` directory, organized by ticker.

**Manually collected variables:**

| Variable                          | Primary Source                   |
| --------------------------------- | -------------------------------- |
| Managerial / Inside ownership     | Annual Report                    |
| State ownership                   | Annual Report                    |
| Institutional ownership           | Annual Report                    |
| Foreign ownership                 | Annual Report                    |
| Value of intangible assets        | Consolidated Financial Statement |
| Consumption of raw material       | Consolidated Financial Statement |
| Work-in-progress goods purchase   | Consolidated Financial Statement |
| Outside manufacturing expenses    | Consolidated Financial Statement |
| Production cost                   | Consolidated Financial Statement |
| R&D expenses                      | Consolidated Financial Statement |
| Product innovation (dummy)        | Annual Report                    |
| Process innovation (dummy)        | Annual Report                    |
| EPS (Earnings per share)          | Consolidated Financial Statement |
| Number of employees               | Annual Report                    |
| Net plant, property and equipment | Consolidated Financial Statement |

**Evidence index file:** `evidence/evidence_metadata.csv`

The file `evidence_metadata.csv` serves as a complete index of all screenshot evidence. It contains 550 records with the following columns:

| Column     | Description                                                     |
| ---------- | --------------------------------------------------------------- |
| `firm`     | Stock ticker (e.g., GMD, CII)                                   |
| `year`     | Fiscal year (2020–2024)                                         |
| `variable` | Name of the variable being evidenced                            |
| `file`     | Filename of the screenshot image stored in `evidence/<ticker>/` |
| `document` | Source document type (e.g., CFS, AR)                            |
| `section`  | Section or table name within the document                       |
| `page`     | Page number in the original document                            |

Screenshot files are organized by ticker under the `evidence/` directory (e.g., `evidence/GMD/`, `evidence/CII/`, etc.). Each image filename corresponds to the `file` column in `evidence_metadata.csv` and can be cross-referenced with the `page` and `section` columns to locate the original data point in its source document.

---

## 8. QC Rules – Data Quality Checks

The `qc_checks.py` script applies the following 6 rules:

| Rule | Field(s) Checked                                                         | Error Condition                                        |
| ---- | ------------------------------------------------------------------------ | ------------------------------------------------------ |
| 1    | `managerial_inside_own`, `state_own`, `institutional_own`, `foreign_own` | Value outside [0, 1]                                   |
| 2    | `shares_outstanding`                                                     | Value ≤ 0                                              |
| 3    | `total_assets`                                                           | Value < 0                                              |
| 4    | `current_liabilities`                                                    | Value < 0                                              |
| 5    | `growth_ratio`                                                           | Outside range [−5.0, 5.0]                              |
| 6    | `market_value_equity`                                                    | Deviation > 5% from `shares_outstanding × share_price` |

---

## 9. Notes on Manually Collected Data

- **`share_price`** in `panel_2020_2024.xlsx` is not one of the 38 required variables. It was added by the team solely to support QC Rule 6 (market value consistency check). It is stored in `fact_market_year` but **does not appear** in `vw_firm_panel_latest`.

- **`rnd_expenses` (R&D):** All rows are NULL because most companies in the dataset do not separately disclose R&D expenses in their financial statements. This is a common reporting practice among listed Vietnamese companies.

- **`firm_age`:** Calculated as `fiscal_year − founded_year + 1`.

- **`product_innovation` and `process_innovation`:** Binary dummy variables (0/1) determined by reading the annual report and identifying evidence of a new product launch or adoption of a new manufacturing process during the year.

---

## 10. Database Structure

```
DIM Tables:
  dim_exchange          — Stock exchanges (HOSE, HNX)
  dim_industry_l2       — Level-2 industry classification
  dim_data_source       — Data sources
  dim_firm              — Firm master list

FACT Tables:
  fact_data_snapshot    — Version management (snapshot tracking)
  fact_financial_year   — Financial statement data (23 variables)
  fact_cashflow_year    — Cash flow data (3 variables)
  fact_ownership_year   — Ownership structure (4 variables)
  fact_market_year      — Market data (5 variables + share_price)
  fact_innovation_year  — Innovation activity (2 variables)
  fact_firm_year_meta   — Firm-year metadata (2 variables)
  fact_value_override_log — Audit log for manually corrected values

VIEW:
  vw_firm_panel_latest  — Final panel dataset: ticker + fiscal_year + 38 variables
                          (selects the latest snapshot for each firm-year)
```

---

## 11. Team Information

**Course:** Data Analysis with Python  
**Team:** Team 7  
**Member:** Nguyễn Hồng Anh (leader), Vũ Thị Phương Anh, Nguyễn Phương Linh, Nguyễn Thị Thùy Linh
**Dataset:** 10 tickers × 5 years (2020–2024) = 50 firm-year observations
