# Retail Analytics — The Mean Girls Store 🛍️

**End-to-end e-commerce analytics on a real, live Shopify apparel brand** (Y2K women's fashion, Pakistan) — from API extraction through customer segmentation, forecasting, and an interactive Tableau dashboard.

> 📊 **Tableau Public dashboard:** https://public.tableau.com/app/profile/syed.haris.shah/viz/MeanGirlsRetailAnalytics/MonthlyRevenue
> 🔒 All customer PII is anonymized (`CUST-####`). Raw identity data never leaves the store.

## Why this project

Most portfolio projects use Kaggle datasets everyone has seen. This one analyzes a **real operating business I have direct access to** — 632 orders, 531 customers, ~30K sessions, PKR 2.76M gross sales over Feb–Jul 2026 — with the messiness that comes with real data: cancellations, COD friction, test orders, freebie promos, and a viral traffic spike that broke the conversion trend.

## Headline insights

1. **Growth is real but fragile.** Revenue grew 6x from March to June (PKR 204K → 1.28M), driven ~entirely by order volume, not basket size. SARIMA forecasting projects PKR 410–505K/week if June's social momentum holds; the trailing-average base case is ~PKR 298K/week.
2. **Traffic quality is the constraint, not traffic.** June sessions tripled (5.7K → 16.9K) but conversion *fell* from 2.8% to 1.7%. Search traffic converts at **4.7% vs 0.5% for social** — a 9x intent gap the brand isn't exploiting.
3. **8 products = 80% of sales, and the top 2 are out of stock.** The two wine-red tops alone generated PKR 855K (31% of gross sales) and both sit at 0–5 units while demand peaks. Inventory depth on winners is the most expensive gap found.
4. **Retention is the untapped lever.** Only 11% of customers repeat, yet repeat buyers (median 2nd purchase in just **8 days**) segment into a clear high-CLV group. Lifting the 257-customer June cohort to May's retention rate ≈ +PKR 90K/month.
5. **45% of the customer base is "Hibernating"** — 237 customers acquired in the growth push who never returned. A WhatsApp win-back flow is the cheapest revenue available.

## Project structure

```
├── data/
│   ├── raw/                  # API extracts (orders anonymized before commit)
│   └── processed/            # cleaned orders, RFM table, cohort matrix
├── notebooks/
│   ├── 01_data_cleaning_eda.ipynb          # KPIs, trends, geography, data quality
│   ├── 02_sales_trends_forecasting.ipynb   # SARIMA forecast + growth decomposition
│   ├── 03_customer_rfm_clv.ipynb           # RFM segments, K-Means validation, CLV
│   ├── 04_cohort_retention.ipynb           # cohort heatmap, repurchase timing
│   └── 05_product_funnel_channel.ipynb     # Pareto, funnel, channels, stockouts
├── src/
│   ├── extract_shopify.py    # Shopify Admin GraphQL extraction (reference)
│   └── build_features.py     # anonymization, RFM, K-Means, cohort pipeline
├── tableau/
│   ├── extracts/             # dashboard-ready CSVs
│   └── BUILD_GUIDE.md        # step-by-step 4-tab dashboard build
└── reports/
    └── executive_summary.md  # business recommendations
```

## Methods & techniques

| Area | Technique |
|---|---|
| Extraction | Shopify Admin GraphQL API (cursor pagination), ShopifyQL analytics |
| Privacy | Deterministic PII anonymization before any data is committed |
| Segmentation | RFM quintile scoring + K-Means (silhouette-validated, log-scaled features) |
| Forecasting | SARIMA with trend, 3-week holdout backtest (MAPE 33.6%) |
| Retention | Monthly acquisition cohorts, repurchase-gap analysis |
| Product | Pareto/ABC analysis, discount-dependence, stockout risk flags |
| Funnel | Session → cart → checkout → purchase conversion decomposition |
| Visualization | Matplotlib (notebooks) + Tableau Public (interactive dashboard) |

## Reproducing

```bash
pip install -r requirements.txt
python src/build_features.py        # rebuilds processed data + Tableau extracts
jupyter lab notebooks/              # notebooks run top-to-bottom
```

To pull fresh data from your own store, set `SHOPIFY_SHOP` / `SHOPIFY_TOKEN` and run `python src/extract_shopify.py`.

## About

Built by **Syed Haris Shah** — MSc Business Analytics candidate, UBC Sauder. The store analyzed is a family-run business, giving this project something rare in analytics portfolios: recommendations that were actually implemented, on data I'm accountable for.
