# FinSight — End-to-End Data Lineage & Governance Map

---

### 1. Visual Data Lineage

```mermaid
graph TD
    subgraph S1["Upstream External Sources"]
        C_API["U.S. Census Bureau MRTS API<br>(Monthly Retail Trade)"]
        F_API["St. Louis Fed FRED API<br>(CPI, Fed Funds, UNRATE, PCE)"]
        S_API["SEC EDGAR XBRL API<br>(Company Facts Financials)"]
    end

    subgraph S2["Bronze / Raw Storage (`data/raw`)"]
        BR_CENSUS["raw_census_mrts.parquet"]
        BR_FRED["raw_fred_series.parquet"]
        BR_SEC["raw_sec_peer_facts.parquet"]
    end

    subgraph S3["Silver / Staging & Intermediate (`dbt`)"]
        STG_CENSUS["stg_census_retail_sales<br>(Cleaned NAICS, Type Casts)"]
        STG_FRED["stg_fred_macro_indicators<br>(Standardized Month Frequencies)"]
        STG_SEC["stg_sec_peer_financials<br>(Harmonized GAAP Metrics)"]
        
        INT_NOVA["int_sales_monthly<br>(Synthesized Enterprise P&L anchored on Census)"]
        INT_MACRO["int_economic_features<br>(Lagged Regressors, YoY Trends)"]
    end

    subgraph S4["Gold / Dimensional Warehouse (PostgreSQL)"]
        DIM_D["dim_date"]
        DIM_R["dim_region"]
        DIM_P["dim_product"]
        DIM_M["dim_economic_indicator"]
        FCT_FIN["fact_financial_performance"]
        FCT_BUD["fact_budget"]
        FCT_FC["fact_forecast"]
        FCT_SC["fact_scenario"]
        FCT_OPS["fact_pipeline_execution"]
    end

    subgraph S5["Analytical Modeling & Intelligence"]
        FC_ENG["Forecasting Tournament Engine<br>(SARIMA / Holt-Winters / XGBoost)"]
        SC_ENG["Interactive Scenario Engine<br>(Parametric P&L Simulator)"]
        PVM_ENG["Price-Volume-Mix Decomposition"]
    end

    subgraph S6["Consumption & Decision Interfaces"]
        API["FastAPI REST Endpoints<br>(/kpis, /forecast, /simulate)"]
        PBI_P1["PBI Page 1: Executive Overview"]
        PBI_P2["PBI Page 2: Financial Performance"]
        PBI_P3["PBI Page 3: Business Drivers"]
        PBI_P4["PBI Page 4: Forecast & Horizon"]
        PBI_P5["PBI Page 5: Scenario Planner"]
        PBI_P6["PBI Page 6: Data Quality & Governance"]
        PBI_P7["PBI Page 7: Platform Operations (SRE)"]
    end

    C_API --> BR_CENSUS
    F_API --> BR_FRED
    S_API --> BR_SEC

    BR_CENSUS --> STG_CENSUS
    BR_FRED --> STG_FRED
    BR_SEC --> STG_SEC

    STG_CENSUS --> INT_NOVA
    STG_FRED --> INT_MACRO

    INT_NOVA --> FCT_FIN & FCT_BUD & DIM_P & DIM_R
    INT_MACRO --> DIM_M
    STG_CENSUS --> DIM_D

    FCT_FIN --> PVM_ENG
    FCT_FIN & INT_MACRO --> FC_ENG
    FC_ENG --> FCT_FC

    FCT_FIN --> SC_ENG
    SC_ENG --> FCT_SC

    FCT_FIN & FCT_BUD & FCT_FC & FCT_SC & DIM_D & DIM_R & DIM_P --> API
    FCT_FIN & FCT_BUD & FCT_FC & FCT_SC & DIM_D & DIM_R & DIM_P --> PBI_P1 & PBI_P2 & PBI_P3 & PBI_P4 & PBI_P5 & PBI_P6 & PBI_P7
    FCT_OPS --> PBI_P6 & PBI_P7
```

---

### 2. Lineage Audit & Governance Matrix

| Target Entity | Grain | Direct Upstream Parents | Transformation Logic | Refresh Frequency | Criticality |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `raw_census_mrts` | Monthly, NAICS Code | U.S. Census Bureau API | Ingestion script with idempotency, JSON parsing, Parquet caching | Monthly | High |
| `raw_fred_series` | Monthly, Series ID | St. Louis Fed FRED API | Rate-limited API fetch, date alignment | Monthly | High |
| `raw_sec_peer_facts`| Quarterly, CIK, Concept | SEC EDGAR API | User-agent compliant XBRL extractor | Quarterly | Medium |
| `stg_census_retail_sales`| Monthly, NAICS Code | `raw_census_mrts` | Cleaned nulls, cast numeric dollar values, unpivot categories | On Ingestion | High |
| `stg_fred_macro_indicators`| Monthly, Series ID | `raw_fred_series` | Fill missing observations, compute MoM/YoY growth rates | On Ingestion | High |
| `fact_financial_performance`| Month, Region, Product, Channel | `int_sales_monthly`, `dim_date`, `dim_region`, `dim_product` | Enterprise P&L synthesis anchored to Census category volumes with regional variance | Nightly | Critical |
| `fact_budget` | Month, Region, Product | `int_sales_monthly` | Baseline annual budget targets (actuals $\pm$ plan growth assumptions) | Annual / Quarterly | Critical |
| `fact_forecast` | Month, Product, Model | `fact_financial_performance`, `int_economic_features` | Backtested tournament model inference (champion model selection) | Monthly | Critical |
| `fact_scenario` | Scenario, Month, Product | `fact_financial_performance` | Parametric stress shocks (Volume, Price, COGS, OpEx) | On Demand / Batch | High |
| `fact_pipeline_execution`| Pipeline Run | Ingestion, dbt, and ML pipelines | Telemetry logging of status, rows processed, tests passed, runtime | Real-Time | High |
