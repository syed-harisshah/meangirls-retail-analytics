# Project Handoff — MeanGirls Retail Analytics

**Context for any assistant (e.g. Claude Sonnet) continuing this work.** Read this fully before acting.

## What this project is

A portfolio analytics project for Syed Haris Shah (MSc Business Analytics, UBC) built on **real Shopify data** from his family's store (The Mean Girls Store — Y2K women's fashion, Pakistan). Target audience: retail analytics recruiters (Lululemon etc.). Repo lives at `~/Documents/Meangirls/meangirls-retail-analytics/`.

## Completed work (do not redo)

1. **Data extraction** — All 632 orders (Feb 24–Jul 2, 2026) pulled via Shopify Admin GraphQL API (cursor pagination, 13 pages in `data/raw/orders_p*.csv`); aggregates (daily sales, sessions/funnel, product sales, device/referrer mixes) via ShopifyQL. Reference script: `src/extract_shopify.py`.
2. **Anonymization** — All customer PII replaced with `CUST-####` IDs (ordered by first purchase). Verified: no raw Shopify IDs anywhere in committed CSVs.
3. **Feature engineering** — `src/build_features.py`: RFM quintile scores + labeled segments, K-Means clusters (k=4, silhouette-validated), CLV proxy, monthly cohort retention matrix. Outputs in `data/processed/`.
4. **Dashboard-ready extracts** — `src/build_dashboard_data.py` pre-computes all table-calc-style math (cumulative %, funnel %, sortable labels like `2026-03 (Mar)` and `01 · Product`) into `tableau/extracts/*.csv` so Tableau charts stay simple.
5. **Five executed notebooks** — `notebooks/01–05`: EDA, SARIMA forecasting (MAPE 33.6% backtest), RFM/CLV + K-Means, cohort retention, product/funnel/channel. All run end-to-end with outputs.
6. **Docs** — `README.md` (portfolio pitch + insights), `reports/executive_summary.md` (5 prioritized business recommendations), `tableau/BUILD_GUIDE.md`.
7. **Desktop Tableau workbook** — `tableau/MeanGirls Retail Analytics.twb` + `.twbx`: 10 sheets, 4 dashboards, extracts embedded. **Cannot be published** — user has Tableau Desktop 2026.2 FREE Edition (publishing disabled) and Tableau Public web rejects .twbx upload ("file type not supported on the web").
8. **Web rebuild (partially done)** — Rebuilt in Tableau Public **web authoring** and PUBLISHED at:
   **https://public.tableau.com/app/profile/syed.haris.shah/viz/MeanGirlsRetailAnalytics/MonthlyRevenue**
   Published sheets so far: `Monthly Revenue` (bar), `Monthly Orders` (line), `Sessions by Month` (bar), `Conversion Rate Trend` (line), `RFM Scatter` (531 disaggregated marks, Segment on Shape/Color). In-progress unsaved: `Sheet 6` = Product Pareto horizontal bars (Product Label on Rows, SUM(Gross Sales) on Columns) — built but not renamed/published.

## Remaining work (the ask)

Continue in Tableau Public web authoring (user signs in at public.tableau.com, opens the workbook → Edit). Data sources `monthly_kpis`, `customers_rfm`, `product_pareto` are already connected as extracts.

1. Rename `Sheet 6` → **Product Pareto**; publish.
2. Add data source `tableau/extracts/funnel.csv` → sheet **Conversion Funnel**: `stage` on Rows, SUM(`count`) on Columns (horizontal bars), `pct_of_sessions` on Label.
3. Add data source `tableau/extracts/monthly_sales_by_referrer.csv` → sheet **Revenue by Channel**: `month_label` Columns, SUM(`total_sales`) Rows, `order_referrer_source` on Color (stacked bars).
4. Add data source `tableau/extracts/cohort_retention.csv` → sheet **Cohort Heatmap**: `cohort_label` Rows, `months_since` Columns (convert to discrete dimension), mark = Square, AVG(`retention_pct`) on Color and Label.
5. Optional sheet **Revenue by Segment** (customers_rfm): `segment` Rows, SUM(`monetary`) Columns, sorted desc.
6. Create **4 dashboards** (Show dashboard title on; add title text with the insight):
   - *Executive Overview*: Monthly Revenue + Monthly Orders. Insight: "Revenue grew 6x Mar→Jun (204K→1.28M PKR), all volume-driven; AOV flat ~4,200."
   - *Customer Intelligence*: RFM Scatter + Revenue by Segment + Cohort Heatmap. Insight: "45% of customers Hibernating; repeat buyers reorder in median 8 days; 11% repeat rate."
   - *Product Performance*: Product Pareto. Insight: "8 of 28 products = 80% of sales; top 2 wine-red tops = 31% and near stockout."
   - *Growth & Channels*: Conversion Funnel + Revenue by Channel + Sessions by Month + Conversion Rate Trend. Insight: "June sessions 3x'd but conversion fell 2.8%→1.7%; search converts ~9x better than social."
7. **Publish** (blue Publish button, top right) after each milestone — web sessions time out (~10–15 min idle) and unsaved work is lost. This has happened once already.
8. Update `README.md`: the Tableau link is already inserted; verify it resolves after final publish.
9. Optionally push the repo to GitHub (user does the `git push` and any account actions).

## Hard-won technique notes for web authoring automation

- **Drag-and-drop does NOT work** with synthetic browser input. Use instead: double-click a field (adds to view), **Show Me** panel (assigns chart type + encodings), right-click field → "Add to ▸" submenu (Rows/Columns/Marks), and the **pill icon menu** on marks-card pills to change encoding (Color/Size/Label/Detail/Tooltip).
- To upload a CSV data source: toolbar "New Data Source" → Files → locate the **hidden `input[type=file]`** element and set files on it directly (don't click "Upload from computer" — native dialog).
- Fields typed into dialogs sometimes don't register — click the input via its accessibility ref first, then type; verify the Publish button turns blue before clicking.
- "Aggregate Measures" toggle is under the **Analysis** menu (needed for the disaggregated RFM scatter).
- Rename sheets by double-clicking the tab; the new-worksheet icon is the FIRST small icon right of the last tab (the second creates a Dashboard — a misclick here once created "Dashboard 1" that had to be deleted).
- Sheet/tab pixel positions shift as tabs are added — re-screenshot before clicking.
- The user must do all sign-ins personally (never handle credentials).

## Key numbers (for dashboard titles / verification)

Revenue (valid) PKR 2,531,596 · 632 total / 602 valid orders · 531 customers · 60 repeat (11.3%) · AOV 4,205 · cancellation 3.8% · 29,888 sessions · CVR 1.97% · funnel 29,888→2,010→1,167→588 · top-2 products PKR 855K (31%) · month-1 retention Mar 5.1% / Apr 10.7% / May 8.6% · median 2nd-purchase gap 8 days.
