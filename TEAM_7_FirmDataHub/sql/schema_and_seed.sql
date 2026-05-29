/* =============================================================================
	WARNING : DROP DATABASE is included. Re-running resets all data.
============================================================================= */

/* =========================================================
   DATABASE
========================================================= */
DROP DATABASE IF EXISTS vn_firm_panel;
CREATE DATABASE vn_firm_panel
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE vn_firm_panel;


/* =============================================================================
   DIMENSION TABLES
   Reference / lookup tables that do not change frequently.
============================================================================= */

CREATE TABLE dim_exchange (
  exchange_id   TINYINT      AUTO_INCREMENT PRIMARY KEY,
  exchange_code VARCHAR(10)  NOT NULL UNIQUE,
  exchange_name VARCHAR(100)
);

CREATE TABLE dim_industry_l2 (
  industry_l2_id   SMALLINT     AUTO_INCREMENT PRIMARY KEY,
  industry_l2_name VARCHAR(150) NOT NULL UNIQUE
);

CREATE TABLE dim_data_source (
  source_id   SMALLINT     AUTO_INCREMENT PRIMARY KEY,
  source_name VARCHAR(100) NOT NULL UNIQUE,
  source_type ENUM('market', 'financial_statement', 'ownership', 'text_report', 'manual') NOT NULL,
  provider    VARCHAR(150),
  note        VARCHAR(255)
);

CREATE TABLE dim_firm (
  firm_id        BIGINT       AUTO_INCREMENT PRIMARY KEY,
  ticker         VARCHAR(20)  NOT NULL UNIQUE,
  company_name   VARCHAR(255) NOT NULL,
  exchange_id    TINYINT      NOT NULL,
  industry_l2_id SMALLINT,
  founded_year   SMALLINT,
  listed_year    SMALLINT,
  status         ENUM('active', 'delisted', 'inactive') DEFAULT 'active',
  created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_firm_exchange  FOREIGN KEY (exchange_id)    REFERENCES dim_exchange(exchange_id),
  CONSTRAINT fk_firm_industry  FOREIGN KEY (industry_l2_id) REFERENCES dim_industry_l2(industry_l2_id)
);


/* =============================================================================
   FACT TABLE — SNAPSHOT / VERSIONING
============================================================================= */

CREATE TABLE fact_data_snapshot (
  snapshot_id   BIGINT      AUTO_INCREMENT PRIMARY KEY,
  snapshot_date DATE        NOT NULL,               
  period_from   DATE,                               
  period_to     DATE,                               
  fiscal_year   SMALLINT    NOT NULL,
  source_id     SMALLINT    NOT NULL,
  version_tag   VARCHAR(50),                        
  created_by    VARCHAR(80),
  created_at    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_snapshot_source FOREIGN KEY (source_id) REFERENCES dim_data_source(source_id)
);


/* =============================================================================
   FACT TABLES
============================================================================= */

CREATE TABLE fact_ownership_year (
  firm_id               BIGINT         NOT NULL,
  fiscal_year           SMALLINT       NOT NULL,
  snapshot_id           BIGINT         NOT NULL,
  managerial_inside_own DECIMAL(10, 6),            
  state_own             DECIMAL(10, 6),            
  institutional_own     DECIMAL(10, 6),            
  foreign_own           DECIMAL(10, 6),            
  note                  VARCHAR(255),
  created_at            TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (firm_id, fiscal_year, snapshot_id),
  FOREIGN KEY (firm_id)      REFERENCES dim_firm(firm_id),
  FOREIGN KEY (snapshot_id)  REFERENCES fact_data_snapshot(snapshot_id)
);

CREATE TABLE fact_financial_year (
  firm_id                         BIGINT         NOT NULL,
  fiscal_year                     SMALLINT       NOT NULL,
  snapshot_id                     BIGINT         NOT NULL,
  unit_scale                      BIGINT         NOT NULL,  
  currency_code                   CHAR(3)        NOT NULL DEFAULT 'VND',
  net_sales                       DECIMAL(20, 2),
  total_assets                    DECIMAL(20, 2),
  selling_expenses                DECIMAL(20, 2),
  general_admin_expenses          DECIMAL(20, 2),
  intangible_assets_net           DECIMAL(20, 2),
  manufacturing_overhead          DECIMAL(20, 2),
  net_operating_income            DECIMAL(20, 2),
  raw_material_consumption        DECIMAL(20, 2),
  merchandise_purchase_year       DECIMAL(20, 2),
  wip_goods_purchase              DECIMAL(20, 2),
  outside_manufacturing_expenses  DECIMAL(20, 2),
  production_cost                 DECIMAL(20, 2),
  rnd_expenses                    DECIMAL(20, 2),           
  net_income                      DECIMAL(20, 2),
  total_equity                    DECIMAL(20, 2),
  total_liabilities               DECIMAL(20, 2),
  cash_and_equivalents            DECIMAL(20, 2),
  long_term_debt                  DECIMAL(20, 2),
  current_assets                  DECIMAL(20, 2),
  current_liabilities             DECIMAL(20, 2),
  growth_ratio                    DECIMAL(10, 6),           
  inventory                       DECIMAL(20, 2),
  net_ppe                         DECIMAL(20, 2),          
  created_at                      TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (firm_id, fiscal_year, snapshot_id),
  FOREIGN KEY (firm_id)      REFERENCES dim_firm(firm_id),
  FOREIGN KEY (snapshot_id)  REFERENCES fact_data_snapshot(snapshot_id)
);

CREATE TABLE fact_cashflow_year (
  firm_id       BIGINT         NOT NULL,
  fiscal_year   SMALLINT       NOT NULL,
  snapshot_id   BIGINT         NOT NULL,
  unit_scale    BIGINT         NOT NULL,
  currency_code CHAR(3)        NOT NULL DEFAULT 'VND',
  net_cfo       DECIMAL(20, 2),                            
  capex         DECIMAL(20, 2),                            
  net_cfi       DECIMAL(20, 2),                            
  created_at    TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (firm_id, fiscal_year, snapshot_id),
  FOREIGN KEY (firm_id)      REFERENCES dim_firm(firm_id),
  FOREIGN KEY (snapshot_id)  REFERENCES fact_data_snapshot(snapshot_id)
);

CREATE TABLE fact_market_year (
  firm_id             BIGINT          NOT NULL,
  fiscal_year         SMALLINT        NOT NULL,
  snapshot_id         BIGINT          NOT NULL,
  shares_outstanding  BIGINT,                              
  price_reference     ENUM('close_year_end', 'avg_year', 'close_fiscal_end'),
  share_price         DECIMAL(20, 4),                      
  market_value_equity DECIMAL(20, 2),
  dividend_cash_paid  DECIMAL(20, 2),
  eps_basic           DECIMAL(20, 6),                      
  currency_code       CHAR(3)         NOT NULL DEFAULT 'VND',
  created_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (firm_id, fiscal_year, snapshot_id),
  FOREIGN KEY (firm_id)      REFERENCES dim_firm(firm_id),
  FOREIGN KEY (snapshot_id)  REFERENCES fact_data_snapshot(snapshot_id)
);

CREATE TABLE fact_innovation_year (
  firm_id            BIGINT       NOT NULL,
  fiscal_year        SMALLINT     NOT NULL,
  snapshot_id        BIGINT       NOT NULL,
  product_innovation TINYINT,                              
  process_innovation TINYINT,                              
  evidence_source_id SMALLINT,                             
  evidence_note      VARCHAR(500),                         
  created_at         TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (firm_id, fiscal_year, snapshot_id),
  FOREIGN KEY (firm_id)            REFERENCES dim_firm(firm_id),
  FOREIGN KEY (snapshot_id)        REFERENCES fact_data_snapshot(snapshot_id),
  FOREIGN KEY (evidence_source_id) REFERENCES dim_data_source(source_id)
);

CREATE TABLE fact_firm_year_meta (
  firm_id         BIGINT     NOT NULL,
  fiscal_year     SMALLINT   NOT NULL,
  snapshot_id     BIGINT     NOT NULL,
  employees_count INT,                                     
  firm_age        SMALLINT,                                
  created_at      TIMESTAMP  DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (firm_id, fiscal_year, snapshot_id),
  FOREIGN KEY (firm_id)      REFERENCES dim_firm(firm_id),
  FOREIGN KEY (snapshot_id)  REFERENCES fact_data_snapshot(snapshot_id)
);


/* =============================================================================
   AUDIT TABLE
============================================================================= */

CREATE TABLE fact_value_override_log (
  override_id  BIGINT       AUTO_INCREMENT PRIMARY KEY,
  firm_id      BIGINT       NOT NULL,
  fiscal_year  SMALLINT     NOT NULL,
  table_name   VARCHAR(80)  NOT NULL,
  column_name  VARCHAR(80)  NOT NULL,
  old_value    VARCHAR(255),
  new_value    VARCHAR(255),
  reason       VARCHAR(255),
  changed_by   VARCHAR(80),
  changed_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (firm_id) REFERENCES dim_firm(firm_id)
);


/* =============================================================================
   SEED DATA — DIMENSION TABLES ONLY
============================================================================= */

INSERT INTO dim_exchange VALUES
  (1, 'HOSE', 'Ho Chi Minh Stock Exchange'),
  (2, 'HNX',  'Hanoi Stock Exchange');

INSERT INTO dim_industry_l2 (industry_l2_id, industry_l2_name) VALUES
	(1,'Tài nguyên Cơ bản'),
	(2,'Thực phẩm và đồ uống'),
	(3,'Hóa chất'),
	(4,'Dầu khí'),
	(5,'Hàng & Dịch vụ Công nghiệp'),
	(6,'Hàng cá nhân & Gia dụng'),
	(7,'Xây dựng và Vật liệu'),
	(8,'Ô tô và phụ tùng'),
	(9,'Y tế');

INSERT INTO dim_data_source (source_id, source_name, source_type, provider, note) VALUES
	(1,'BCTC_Audited','financial_statement','Company/Exchange','Audited financial statements'),
	(2,'Vietstock','market','Vietstock','Market fields (price, shares, dividend, EPS)'),
	(3,'AnnualReport','text_report','Company','Annual report / disclosures');

-- Ten tickers for Team 7 (sorted by firm_id ASC)
INSERT INTO dim_firm (firm_id, ticker, company_name, exchange_id, industry_l2_id, founded_year, listed_year, status, created_at, updated_at) VALUES
  (1,  'GMD', 'Gemadept',                        	 1, 5, 1993, 2002, 'active', '2026-02-10 12:30:00', '2026-02-10 12:30:00'),
  (2,  'CII', 'Hạ tầng Kỹ thuật TP.HCM',  			 1, 7, 2001, 2006, 'active', '2026-02-10 12:30:00', '2026-02-10 12:30:00'),
  (3,  'PVD', 'Khoan Dầu khí PVDrilling',     		 1, 4, 2005, 2006, 'active', '2026-02-10 12:30:00', '2026-02-10 12:30:00'),
  (4,  'HAH', 'Vận tải và Xếp dỡ Hải An',            1, 5, 2009, 2015, 'active', '2026-02-10 12:30:00', '2026-02-10 12:30:00'),
  (5,  'HHV', 'Đầu tư Hạ tầng Giao thông Đèo Cả',    1, 7, 1997, 2022, 'active', '2026-02-10 12:30:00', '2026-02-10 12:30:00'),
  (6,  'HHS', 'Đầu tư DV Hoàng Huy',               	 1, 8, 2008, 2012, 'active', '2026-02-10 12:30:00', '2026-02-10 12:30:00'),
  (7,  'TCM', 'Dệt may Thành Công',       			 1, 6, 2006, 2007, 'active', '2026-02-10 12:30:00', '2026-02-10 12:30:00'),
  (8,  'LCG', 'LIZEN',                   			 1, 7, 2006, 2008, 'active', '2026-02-10 12:30:00', '2026-02-10 12:30:00'),
  (9,  'VOS', 'Vận tải Biển Việt Namg',              1, 5, 2007, 2010, 'active', '2026-02-10 12:30:00', '2026-02-10 12:30:00'),
  (10, 'MST', 'Đầu tư MST',          				 2, 7, 2009, 2016, 'active', '2026-02-10 12:30:00', '2026-02-10 12:30:00');


/* =============================================================================
   VIEW — FINAL PANEL DATASET
============================================================================= */

CREATE OR REPLACE VIEW vw_firm_panel_latest AS
SELECT 
    f.ticker,
    y.fiscal_year,

    fo.managerial_inside_own,
    fo.state_own,
    fo.institutional_own,
    fo.foreign_own,

    fm.shares_outstanding,

    ff.net_sales,
    ff.total_assets,
    ff.selling_expenses,
    ff.general_admin_expenses,
    ff.intangible_assets_net,
    ff.manufacturing_overhead,
    ff.net_operating_income,
    ff.raw_material_consumption,
    ff.merchandise_purchase_year,
    ff.wip_goods_purchase,
    ff.outside_manufacturing_expenses,
    ff.production_cost,
    ff.rnd_expenses,

    fi.product_innovation,
    fi.process_innovation,

    ff.net_income,
    ff.total_equity,
    fm.market_value_equity,
    ff.total_liabilities,

    fc.net_cfo,
    fc.capex,
    fc.net_cfi,

    ff.cash_and_equivalents,
    ff.long_term_debt,
    ff.current_assets,
    ff.current_liabilities,
    ff.growth_ratio,
    ff.inventory,

    fm.dividend_cash_paid,
    fm.eps_basic,

    meta.employees_count,
    ff.net_ppe,
    meta.firm_age

FROM dim_firm f

-- Build the full set of firm-year combinations that exist across all fact tables
JOIN (
    SELECT firm_id, fiscal_year FROM fact_ownership_year
    UNION
    SELECT firm_id, fiscal_year FROM fact_financial_year
    UNION
    SELECT firm_id, fiscal_year FROM fact_market_year
    UNION
    SELECT firm_id, fiscal_year FROM fact_cashflow_year
    UNION
    SELECT firm_id, fiscal_year FROM fact_innovation_year
    UNION
    SELECT firm_id, fiscal_year FROM fact_firm_year_meta
) y ON f.firm_id = y.firm_id

-- Ownership: latest snapshot
LEFT JOIN fact_ownership_year fo
    ON  fo.firm_id    = y.firm_id
    AND fo.fiscal_year = y.fiscal_year
    AND fo.snapshot_id = (
        SELECT MAX(x.snapshot_id) FROM fact_ownership_year x
        WHERE x.firm_id = y.firm_id AND x.fiscal_year = y.fiscal_year
    )

-- Financial: latest snapshot
LEFT JOIN fact_financial_year ff
    ON  ff.firm_id    = y.firm_id
    AND ff.fiscal_year = y.fiscal_year
    AND ff.snapshot_id = (
        SELECT MAX(x.snapshot_id) FROM fact_financial_year x
        WHERE x.firm_id = y.firm_id AND x.fiscal_year = y.fiscal_year
    )

-- Market: latest snapshot
LEFT JOIN fact_market_year fm
    ON  fm.firm_id    = y.firm_id
    AND fm.fiscal_year = y.fiscal_year
    AND fm.snapshot_id = (
        SELECT MAX(x.snapshot_id) FROM fact_market_year x
        WHERE x.firm_id = y.firm_id AND x.fiscal_year = y.fiscal_year
    )

-- Cash flow: latest snapshot
LEFT JOIN fact_cashflow_year fc
    ON  fc.firm_id    = y.firm_id
    AND fc.fiscal_year = y.fiscal_year
    AND fc.snapshot_id = (
        SELECT MAX(x.snapshot_id) FROM fact_cashflow_year x
        WHERE x.firm_id = y.firm_id AND x.fiscal_year = y.fiscal_year
    )

-- Innovation: latest snapshot
LEFT JOIN fact_innovation_year fi
    ON  fi.firm_id    = y.firm_id
    AND fi.fiscal_year = y.fiscal_year
    AND fi.snapshot_id = (
        SELECT MAX(x.snapshot_id) FROM fact_innovation_year x
        WHERE x.firm_id = y.firm_id AND x.fiscal_year = y.fiscal_year
    )

-- Firm-year metadata: latest snapshot
LEFT JOIN fact_firm_year_meta meta
    ON  meta.firm_id    = y.firm_id
    AND meta.fiscal_year = y.fiscal_year
    AND meta.snapshot_id = (
        SELECT MAX(x.snapshot_id) FROM fact_firm_year_meta x
        WHERE x.firm_id = y.firm_id AND x.fiscal_year = y.fiscal_year
    );
