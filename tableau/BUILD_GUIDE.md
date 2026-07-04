# Tableau Public Build Guide — Mean Girls Store Analytics

Step-by-step instructions to build the 4-tab dashboard in Tableau Public from the CSVs in `tableau/extracts/`. Estimated time: 60–90 minutes.

## Setup

1. Open Tableau Public → **Connect → Text file** → select `daily_sales.csv`.
2. In the Data Source pane, click **Add** next to Connections and add the other CSVs the same way as you need them (each dashboard tab below lists its data source). Keep them as separate data sources — no joins needed.
3. Set field types: every `day`/`month`/date column → **Date**; `total`, `gross_sales`, revenue columns → **Number (decimal)**.
4. Colors used throughout: pink `#E75480` (primary), dark grey `#2D2D2D`, light grey `#999999`.

---

## Tab 1 — Executive Overview  (source: `daily_sales.csv`, `orders.csv`)

**Sheet 1.1 KPI cards** (4 separate sheets, each a single Text mark):
- Total Revenue: `SUM(total_sales)` — format as currency, custom prefix "PKR ".
- Orders: `SUM(orders)`.
- AOV: `SUM(gross_sales)/SUM(orders)`.
- Repeat rate (source `customers_rfm.csv`): create calc `Repeat = IF frequency > 1 THEN 1 ELSE 0 END`, show `SUM(Repeat)/COUNT(customer)` as %.

**Sheet 1.2 Revenue trend:** Columns = `MONTH(day)` (continuous), Rows = `SUM(total_sales)`. Add `SUM(orders)` on dual axis as a line (dark grey); bars pink. Title: "Monthly Revenue & Orders".

**Sheet 1.3 Daily revenue with moving average:** Columns = `DAY(day)` continuous, Rows = `SUM(total_sales)` as light grey bars + Table Calculation "Moving Average, previous 6" as a pink line.

**Layout:** KPI cards in a row on top, 1.2 left, 1.3 right.

---

## Tab 2 — Customer Intelligence  (source: `customers_rfm.csv`, `cohort_retention.csv`)

**Sheet 2.1 RFM scatter:** Columns = `recency_days`, Rows = `monetary` (right-click axis → Logarithmic). Marks: Circle; Color = `segment`; Size = `frequency`. Title: "RFM Landscape".

**Sheet 2.2 Segment revenue:** Rows = `segment` (sorted by revenue desc), Columns = `SUM(monetary)`. Add `COUNT(customer)` as label. Pink bars.

**Sheet 2.3 Cohort heatmap:** Source `cohort_retention.csv`. Columns = `months_since` (discrete), Rows = `MONTH(cohort_month)` (discrete). Marks: Square; Color = `AVG(retention_rate)` (Red-Pink palette, 0–25%); Label = `AVG(retention_rate)` formatted as %.

**Sheet 2.4 CLV by segment:** Rows = `segment`, Columns = `AVG(clv_6m_proxy)`.

**Layout:** 2.1 top-left, 2.2 top-right, 2.3 bottom-left, 2.4 bottom-right. Add a segment filter that applies to 2.1/2.2/2.4.

---

## Tab 3 — Product Performance  (source: `product_sales.csv`)

**Sheet 3.1 Pareto:** Columns = `product_title` sorted by `SUM(gross_sales)` desc. Rows = `SUM(gross_sales)` (pink bars). Dual axis: `SUM(gross_sales)` with two table calcs stacked — "Running Total" then "Percent of Total" — as a dark line. Add 80% reference line on the right axis.

**Sheet 3.2 Product table:** Rows = `product_title`; Measures: `gross_sales`, `discounts`, `net_sales`, `orders`, `net_items_sold`. Sort by gross_sales desc. Color `net_sales` cells with a pink gradient.

**Sheet 3.3 Discount dependence:** Columns = `SUM(gross_sales)`, Rows = `-SUM(discounts)/SUM(gross_sales)` per product (scatter). Products in the upper area only sell when discounted (the tote-bag freebie will be the extreme point — annotate it).

**Layout:** 3.1 full-width top, 3.2 bottom-left, 3.3 bottom-right.

---

## Tab 4 — Growth & Channels  (sources: `daily_sessions_funnel.csv`, `sessions_by_device.csv`, `sessions_by_referrer.csv`, `monthly_sales_by_referrer.csv`)

**Sheet 4.1 Funnel:** From `daily_sessions_funnel.csv`, create 4 calculated fields: `SUM(sessions)`, `SUM(sessions_with_cart_additions)`, `SUM(sessions_that_reached_checkout)`, `SUM(sessions_that_completed_checkout)`. Use **Measure Names / Measure Values** on Rows/Columns as horizontal bars, sorted. Label each bar with value + % of sessions.

**Sheet 4.2 Traffic vs conversion:** Columns = `MONTH(day)`; Rows = `SUM(sessions)` (grey bars) with dual axis `SUM(sessions_that_completed_checkout)/SUM(sessions)` (pink line, % format). Title: "Traffic tripled, conversion fell".

**Sheet 4.3 Device & referrer donuts:** Two pie charts from `sessions_by_device.csv` and `sessions_by_referrer.csv` (Angle = sessions, Color = category).

**Sheet 4.4 Revenue by channel:** From `monthly_sales_by_referrer.csv`: Columns = `MONTH(month)`, Rows = `SUM(total_sales)`, Color = `order_referrer_source` (stacked bars).

**Layout:** 4.1 top-left, 4.2 top-right, 4.3 bottom-left, 4.4 bottom-right.

---

## Publish

1. Assemble each tab as a Dashboard (1300×800, tiled). Add a title banner: "The Mean Girls Store — Retail Analytics | Feb–Jul 2026 | PKR".
2. **File → Save to Tableau Public** (it publishes to your profile).
3. Copy the public URL and paste it into the README badge/link at the top of the repo.

Tip: on each dashboard add a floating text box with the 1–2 sentence takeaway (copy from `reports/executive_summary.md`) — recruiters read the insight, not the chart.
