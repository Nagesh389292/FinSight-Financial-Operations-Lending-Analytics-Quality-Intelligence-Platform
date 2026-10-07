# FinSight — Metric Definitions & Catalog

This document establishes the authoritative financial, operational, and mathematical definitions for all metrics used within FinSight. No metric may be used or displayed without adhering to these standards.

---

### 1. Financial Performance Metrics (P&L)

| Metric Name | Symbol / Code | Formula / Calculation | Grain | Source / Ownership | Business Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gross Revenue** | `gross_revenue` | $\sum (\text{Units Sold} \times \text{List Price})$ | Month, Region, Product, Channel | ERP / Finance | Total top-line sales value before customer discounts, returns, and allowances. |
| **Discounts & Allowances** | `discounts` | $\sum (\text{Promotional Discounts} + \text{Markdowns})$ | Month, Region, Product, Channel | Commercial / Sales | Aggregate deductions applied to gross sales. |
| **Net Revenue** | `revenue` | $\text{Gross Revenue} - \text{Discounts}$ | Month, Region, Product, Channel | Finance | Recognized net revenue for the period. Serves as base denominator for all margin ratios. |
| **Cost of Goods Sold** | `cogs` | $\sum (\text{Units Sold} \times \text{Unit Landed Cost})$ | Month, Region, Product, Channel | Supply Chain / Finance | Direct costs attributable to product procurement, manufacturing, and inbound freight. |
| **Gross Profit** | `gross_profit` | $\text{Net Revenue} - \text{COGS}$ | Month, Region, Product, Channel | Finance | Dollar profit remaining after direct product costs are deducted. |
| **Gross Margin %** | `gross_margin_pct` | $\frac{\text{Gross Profit}}{\text{Net Revenue}} \times 100$ | Any Aggregation Level | Finance | Core profitability ratio reflecting pricing power and procurement efficiency. |
| **Operating Expenses** | `opex` | $\text{Selling} + \text{Marketing} + \text{G\&A} + \text{Logistics}$ | Month, Region, Channel | Finance / HR / Ops | Indirect overhead expenses required to maintain business operations. |
| **Operating Income (EBIT)** | `operating_income` | $\text{Gross Profit} - \text{OpEx}$ | Month, Region, Channel | Corporate Finance | Earnings before interest and taxes; primary indicator of operational viability. |
| **Operating Margin %** | `operating_margin_pct` | $\frac{\text{Operating Income}}{\text{Net Revenue}} \times 100$ | Any Aggregation Level | Corporate Finance | Percentage of revenue converted into operating profits. |
| **EBITDA** | `ebitda` | $\text{Operating Income} + \text{Depreciation} + \text{Amortization}$ | Month, Region | Corporate Finance | Operating cash flow proxy before non-cash charges and capital structure effects. |

---

### 2. Growth & Market Benchmark Metrics

| Metric Name | Symbol / Code | Formula / Calculation | Grain | Interpretation |
| :--- | :--- | :--- | :--- | :--- |
| **YoY Revenue Growth %** | `yoy_revenue_growth` | $\frac{\text{Revenue}_t - \text{Revenue}_{t-12}}{\text{Revenue}_{t-12}} \times 100$ | Month, Category, Region | Annual trajectory eliminating normal monthly seasonality. |
| **MoM Revenue Growth %** | `mom_revenue_growth` | $\frac{\text{Revenue}_t - \text{Revenue}_{t-1}}{\text{Revenue}_{t-1}} \times 100$ | Month, Category, Region | Sequential velocity identifying emerging inflection points. |
| **Industry Benchmark Growth** | `census_industry_growth` | $\frac{\text{Census Sales}_t - \text{Census Sales}_{t-12}}{\text{Census Sales}_{t-12}} \times 100$ | Month, NAICS Sector | Sector-wide growth rate reported by U.S. Census Bureau MRTS. |
| **Relative Market Alpha** | `market_alpha` | $\text{YoY Revenue Growth \%} - \text{Industry Benchmark Growth \%}$ | Month, Category | Measures if NovaRetail is gaining or ceding market share relative to industry. |

---

### 3. Variance & Driver Analysis (Price-Volume-Mix)

When comparing **Actual ($A$)** against **Budget / Plan ($B$)**:

$$\Delta \text{Revenue} = \text{Revenue}_A - \text{Revenue}_B$$

FinSight decomposes this variance into three mutually exclusive, collectively exhaustive drivers:

1. **Volume Variance ($VV$)**:
   The impact of selling more or fewer units than planned, holding budget price constant:
   $$VV = (V_A - V_B) \times P_B$$

2. **Price Variance ($PV$)**:
   The impact of charging a higher or lower average selling price than planned, evaluated at actual volume:
   $$PV = (P_A - P_B) \times V_A$$

3. **Cost Variance ($CV$)**:
   The impact of procurement inflation or cost savings, evaluated at actual volume:
   $$CV = (C_B - C_A) \times V_A$$
   *(Note: A positive value indicates cost savings favorable to margin).*

4. **Net Operating Variance**:
   $$\Delta \text{Operating Profit} = VV + PV + CV - \Delta \text{OpEx}$$

---

### 4. Forecast Accuracy & Tournament Metrics

Let $y_t$ be the actual value at time $t$, and $\hat{y}_t$ be the model forecast. Over evaluation horizon $n$:

| Metric | Code | Mathematical Formula | Purpose & Thresholds |
| :--- | :--- | :--- | :--- |
| **Mean Absolute Error** | `MAE` | $\frac{1}{n}\sum_{t=1}^n \|y_t - \hat{y}_t\|$ | Interpretable dollar-magnitude error. Target: $< 4\%$ of mean revenue. |
| **Root Mean Squared Error** | `RMSE` | $\sqrt{\frac{1}{n}\sum_{t=1}^n (y_t - \hat{y}_t)^2}$ | Penalizes large outlier forecast errors heavily. |
| **Mean Absolute % Error** | `MAPE` | $\frac{100\%}{n}\sum_{t=1}^n \left\|\frac{y_t - \hat{y}_t}{y_t}\right\|$ | Intuitive percentage error. Target: $< 5.0\%$ for 1-month ahead. |
| **Symmetric MAPE** | `sMAPE` | $\frac{100\%}{n}\sum_{t=1}^n \frac{2\|y_t - \hat{y}_t\|}{\|y_t\| + \|\hat{y}_t\|}$ | Bounded $[0\%, 200\%]$, avoids division by zero, symmetric penalty. |
| **Forecast Bias (Mean Error)** | `BIAS` | $\frac{1}{n}\sum_{t=1}^n (y_t - \hat{y}_t)$ | Positive = model systematically underpredicts; Negative = model overpredicts. |
| **Tracking Signal** | `TS` | $\frac{\sum_{t=1}^n (y_t - \hat{y}_t)}{\text{MAD}}$ | Cumulative error over MAD. Signal alarms if $\|TS\| > 4$. |

---

### 5. Data Quality & SRE Service Level Indicators (SLIs)

| Indicator | Code | Measurement | Target SLA |
| :--- | :--- | :--- | :--- |
| **Completeness Ratio** | `dq_completeness` | $\frac{\text{Non-null Records}}{\text{Total Required Records}} \times 100$ | $100.0\%$ on mandatory keys (`date_key`, `revenue`, `region_key`) |
| **Uniqueness Adherence** | `dq_uniqueness` | Count of duplicate composite primary keys | $0$ duplicates allowed at fact grain |
| **Domain Range Validity** | `dq_validity` | Percentage of records adhering to domain constraints ($\text{revenue} \ge 0$, $\text{gross\_margin\_pct} \in [-100, 100]$) | $100.0\%$ |
| **Referential Integrity** | `dq_ref_integrity` | Orphaned foreign keys in facts referencing dimensions | $0$ orphaned foreign keys |
| **Data Freshness** | `dq_freshness` | Elapsed hours since publication of latest government index | Within $24$ hours of upstream release |
