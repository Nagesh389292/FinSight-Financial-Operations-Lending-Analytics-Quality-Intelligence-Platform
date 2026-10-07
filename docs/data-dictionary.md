# FinSight — Enterprise Data Dictionary

---

### 1. Ingestion Sources & Raw Layer Metadata

#### 1.1. U.S. Census Bureau — Monthly Retail Trade Survey (MRTS)
- **Endpoint**: `https://api.census.gov/data/timeseries/eits/mrts`
- **Cadence**: Monthly
- **Key Fields**:
  - `time_slot_id` / `time`: Monthly period (`YYYY-MM`).
  - `category_code`: NAICS category code:
    - `44X72`: Retail and Food Services, Total
    - `44000`: Retail Trade, Total
    - `443`: Electronics and Appliance Stores
    - `448`: Clothing and Clothing Accessories Stores
    - `442`: Furniture and Home Furnishings Stores
    - `445`: Food and Beverage Stores
    - `4541`: Electronic Shopping and Mail-Order Houses (E-Commerce)
  - `data_type_code`: `SM` (Sales - Monthly in Millions of Dollars), `MPCSM` (Monthly % Change).
  - `cell_value`: Numeric dollar value or percentage.
  - `seasonally_adj`: `yes` or `no`.

#### 1.2. Federal Reserve Bank of St. Louis — FRED API
- **Endpoint**: `https://api.stlouisfed.org/fred/series/observations`
- **Cadence**: Monthly / Daily aggregated to Monthly
- **Key Series Ingested**:
  - `CPIAUCNS`: Consumer Price Index for All Urban Consumers (All Items, Index 1982-1984=100)
  - `FEDFUNDS`: Federal Funds Effective Rate (%)
  - `UNRATE`: Civilian Unemployment Rate (%)
  - `PCE`: Personal Consumption Expenditures ($ Billions)
  - `UMCSENT`: University of Michigan: Consumer Sentiment Index

#### 1.3. SEC EDGAR — Company Facts API
- **Endpoint**: `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_10_digits}.json`
- **Cadence**: Quarterly / Annual
- **Concepts Extracted**:
  - `us-gaap/Revenues` or `us-gaap/SalesRevenueNet`
  - `us-gaap/CostOfGoodsAndServicesSold`
  - `us-gaap/GrossProfit`
  - `us-gaap/OperatingExpenses`
  - `us-gaap/OperatingIncomeLoss`

---

### 2. Gold Dimensional Model (PostgreSQL Warehouse)

#### 2.1. Dimension: `dim_date`
Primary calendar dimension enabling time-intelligence calculations in SQL and Power BI DAX.

| Column Name | Data Type | Nullable | Description / Example |
| :--- | :--- | :--- | :--- |
| `date_key` | `INT` (PK) | No | Surrogate integer key formatted `YYYYMMDD` (e.g., `20240101`). |
| `full_date` | `DATE` | No | Calendar date (`2024-01-01`). |
| `year` | `INT` | No | Calendar year (`2024`). |
| `quarter` | `INT` | No | Calendar quarter (`1`, `2`, `3`, `4`). |
| `quarter_name` | `VARCHAR(10)` | No | Quarter label (`Q1 2024`). |
| `month` | `INT` | No | Calendar month index (`1` to `12`). |
| `month_name` | `VARCHAR(20)` | No | Full month name (`January`). |
| `month_short` | `VARCHAR(3)` | No | Abbreviated month (`Jan`). |
| `year_month` | `VARCHAR(7)` | No | Formatted `YYYY-MM` (`2024-01`). |
| `fiscal_year` | `INT` | No | Fiscal year (Feb 1 - Jan 31 retail calendar). |
| `fiscal_quarter` | `INT` | No | Retail fiscal quarter (`1` to `4`). |
| `is_month_end` | `BOOLEAN` | No | True if last day of calendar month. |

#### 2.2. Dimension: `dim_region`
Geographic operating structure for NovaRetail Group.

| Column Name | Data Type | Nullable | Description / Example |
| :--- | :--- | :--- | :--- |
| `region_key` | `INT` (PK) | No | Surrogate key (`1`, `2`, `3`, `4`). |
| `region_id` | `VARCHAR(10)` | No | Natural identifier (`REG-NE`, `REG-MW`, `REG-SO`, `REG-WE`). |
| `region_name` | `VARCHAR(50)` | No | Name (`Northeast`, `Midwest`, `South`, `West`). |
| `headquarters_city` | `VARCHAR(50)` | No | Hub city (`Boston`, `Chicago`, `Atlanta`, `Seattle`). |
| `regional_vp` | `VARCHAR(100)`| No | Executive owner name. |
| `store_count` | `INT` | No | Number of operating physical stores. |

#### 2.3. Dimension: `dim_product`
Product taxonomy and margin classification.

| Column Name | Data Type | Nullable | Description / Example |
| :--- | :--- | :--- | :--- |
| `product_key` | `INT` (PK) | No | Surrogate key (`1` to `5`). |
| `category_id` | `VARCHAR(20)` | No | Natural identifier (`CAT-ELEC`, `CAT-APP`, `CAT-HOME`, `CAT-FOOD`, `CAT-GEN`). |
| `category_name` | `VARCHAR(100)`| No | Category (`Electronics & Appliances`, `Apparel`, `Home & Living`, etc.). |
| `naics_code` | `VARCHAR(10)` | No | Associated U.S. Census NAICS code (`443`, `448`, `442`, `445`, `4541`). |
| `target_gross_margin_pct` | `NUMERIC(5,2)` | No | Target benchmark gross margin % (`28.00`, `45.00`, etc.). |
| `elasticity_tier` | `VARCHAR(20)` | No | Price elasticity classification (`High`, `Moderate`, `Defensive`). |

#### 2.4. Dimension: `dim_economic_indicator`
Catalog of external macroeconomic regressors.

| Column Name | Data Type | Nullable | Description / Example |
| :--- | :--- | :--- | :--- |
| `indicator_key` | `INT` (PK) | No | Surrogate key (`1` to `5`). |
| `series_id` | `VARCHAR(20)` | No | FRED series identifier (`CPIAUCNS`, `FEDFUNDS`, `UNRATE`, etc.). |
| `series_name` | `VARCHAR(100)`| No | Descriptive name (`Consumer Price Index`, `Fed Funds Effective Rate`). |
| `reporting_agency` | `VARCHAR(50)` | No | St. Louis Fed / BLS / Census. |
| `units` | `VARCHAR(50)` | No | Percent, Index, Billions USD. |
| `update_cadence` | `VARCHAR(20)` | No | `Monthly`. |

#### 2.5. Fact: `fact_financial_performance`
Core monthly financial performance grain: Month $\times$ Product Category $\times$ Region $\times$ Sales Channel.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :--- | :--- | :--- |
| `performance_id` | `BIGINT` (PK) | No | Primary Key | Synthetic sequence identifier. |
| `date_key` | `INT` | No | FK $\to$ `dim_date` | Date reference (first of month). |
| `product_key` | `INT` | No | FK $\to$ `dim_product`| Product category reference. |
| `region_key` | `INT` | No | FK $\to$ `dim_region` | Geographic region reference. |
| `channel_code` | `VARCHAR(20)` | No | Domain constraint | Sales channel (`Retail Stores`, `E-Commerce`). |
| `units_sold` | `NUMERIC(12,2)`| No | $\ge 0$ | Aggregate unit volume sold. |
| `gross_revenue` | `NUMERIC(15,2)`| No | $\ge 0$ | Total revenue before discounts ($). |
| `discounts` | `NUMERIC(15,2)`| No | $\ge 0$ | Total discount deductions ($). |
| `net_revenue` | `NUMERIC(15,2)`| No | $\ge 0$ | Recognized net sales ($). |
| `cogs` | `NUMERIC(15,2)`| No | $\ge 0$ | Landed cost of goods sold ($). |
| `gross_profit` | `NUMERIC(15,2)`| No | Derived | `net_revenue - cogs`. |
| `gross_margin_pct` | `NUMERIC(6,2)`| No | Derived | `(gross_profit / net_revenue) * 100`. |
| `opex` | `NUMERIC(15,2)`| No | $\ge 0$ | Allocated SG&A and operational expenses ($). |
| `operating_income` | `NUMERIC(15,2)`| No | Derived | `gross_profit - opex` (EBIT). |
| `operating_margin_pct` | `NUMERIC(6,2)`| No | Derived | `(operating_income / net_revenue) * 100`. |

#### 2.6. Fact: `fact_budget`
Annual and quarterly budget targets against which actual performance is benchmarked.

| Column Name | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :--- | :--- | :--- |
| `budget_id` | `BIGINT` (PK) | No | Primary Key | Synthetic identifier. |
| `date_key` | `INT` | No | FK $\to$ `dim_date` | Planned period. |
| `product_key` | `INT` | No | FK $\to$ `dim_product`| Planned category. |
| `region_key` | `INT` | No | FK $\to$ `dim_region` | Planned region. |
| `budget_units` | `NUMERIC(12,2)`| No | $\ge 0$ | Planned sales volume. |
| `budget_revenue` | `NUMERIC(15,2)`| No | $\ge 0$ | Planned net revenue ($). |
| `budget_cogs` | `NUMERIC(15,2)`| No | $\ge 0$ | Planned COGS ($). |
| `budget_gross_profit` | `NUMERIC(15,2)`| No | Derived | `budget_revenue - budget_cogs`. |
| `budget_opex` | `NUMERIC(15,2)`| No | $\ge 0$ | Planned OpEx ($). |
| `budget_operating_income`| `NUMERIC(15,2)`| No | Derived | `budget_gross_profit - budget_opex`. |

#### 2.7. Fact: `fact_forecast`
Multi-model forecast predictions generated by the ML & statistical engine.

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `forecast_id` | `BIGINT` (PK) | No | Primary Key. |
| `forecast_date_key` | `INT` | No | Target future date being predicted (`dim_date`). |
| `product_key` | `INT` | No | Target product category (`dim_product`). |
| `model_name` | `VARCHAR(50)` | No | Model identifier (`SARIMA`, `Holt-Winters`, `XGBoost`, `Ensemble`). |
| `is_champion` | `BOOLEAN` | No | Flag indicating if this model is the tournament winner. |
| `predicted_revenue` | `NUMERIC(15,2)`| No | Point estimate of future net revenue ($). |
| `lower_ci_80` | `NUMERIC(15,2)`| No | 80% confidence interval lower bound. |
| `upper_ci_80` | `NUMERIC(15,2)`| No | 80% confidence interval upper bound. |
| `lower_ci_95` | `NUMERIC(15,2)`| No | 95% confidence interval lower bound. |
| `upper_ci_95` | `NUMERIC(15,2)`| No | 95% confidence interval upper bound. |
| `train_mae` | `NUMERIC(12,2)`| No | Backtested out-of-sample MAE. |
| `train_smape` | `NUMERIC(6,2)`| No | Backtested out-of-sample sMAPE %. |
| `generated_timestamp` | `TIMESTAMP` | No | Model inference execution timestamp. |

#### 2.8. Fact: `fact_scenario`
Pre-calculated and dynamically simulated what-if scenarios.

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `scenario_id` | `VARCHAR(50)` | No | Composite identifier (e.g., `SCEN-STRESS-STAGFLATION`). |
| `scenario_name` | `VARCHAR(100)`| No | Business name (`Stagflation: Volume -5%, COGS +4%`). |
| `date_key` | `INT` | No | Evaluated period (`dim_date`). |
| `product_key` | `INT` | No | Evaluated category (`dim_product`). |
| `volume_delta_pct` | `NUMERIC(6,2)`| No | Simulated volume change % ($\pm 20\%$). |
| `price_delta_pct` | `NUMERIC(6,2)`| No | Simulated price change % ($\pm 15\%$). |
| `cogs_delta_pct` | `NUMERIC(6,2)`| No | Simulated COGS inflation % ($\pm 10\%$). |
| `opex_delta_pct` | `NUMERIC(6,2)`| No | Simulated OpEx reduction % ($\pm 10\%$). |
| `simulated_revenue` | `NUMERIC(15,2)`| No | Resulting net revenue under scenario ($). |
| `simulated_cogs` | `NUMERIC(15,2)`| No | Resulting COGS ($). |
| `simulated_gross_profit` | `NUMERIC(15,2)`| No | Resulting gross profit ($). |
| `simulated_gross_margin_pct`| `NUMERIC(6,2)`| No | Resulting gross margin %. |
| `simulated_operating_income` | `NUMERIC(15,2)`| No | Resulting operating income ($). |

#### 2.9. Fact: `fact_pipeline_execution` (SRE Observability)
Tracks pipeline telemetry, SLAs, data volumes, and health statuses.

| Column Name | Data Type | Nullable | Description |
| :--- | :--- | :--- | :--- |
| `run_id` | `VARCHAR(64)` | No | Execution UUID / Timestamp hash. |
| `pipeline_name` | `VARCHAR(100)`| No | Name (`census_ingest`, `fred_ingest`, `dbt_transform`, `forecast_train`). |
| `status` | `VARCHAR(20)` | No | `SUCCESS`, `FAILURE`, `RUNNING`. |
| `start_time` | `TIMESTAMP` | No | Pipeline initiation timestamp. |
| `end_time` | `TIMESTAMP` | Yes| Pipeline completion timestamp. |
| `duration_seconds` | `NUMERIC(8,2)`| Yes| Total runtime in seconds. |
| `records_processed` | `INT` | Yes| Number of rows read or produced. |
| `dq_tests_passed` | `INT` | Yes| Count of passed data quality checks. |
| `dq_tests_failed` | `INT` | Yes| Count of failed data quality checks. |
| `error_details` | `TEXT` | Yes| Stack trace or error message if failed. |
