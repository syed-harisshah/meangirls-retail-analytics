"""Build simplified, pre-computed datasets for the Tableau dashboard.

All 'table calculations' (cumulative shares, funnel %, cohort labels, sort keys)
are computed here in pandas so the Tableau worksheets stay simple and robust.
"""

import os
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
PROC = os.path.join(BASE, "data", "processed")
OUT = os.path.join(BASE, "tableau", "extracts")
os.makedirs(OUT, exist_ok=True)

# 1. Monthly KPIs (sales + traffic joined)
daily = pd.read_csv(os.path.join(RAW, "daily_sales.csv"), parse_dates=["day"])
fun = pd.read_csv(os.path.join(RAW, "daily_sessions_funnel.csv"), parse_dates=["day"])
m1 = daily.set_index("day").resample("MS").agg(
    revenue=("total_sales", "sum"), orders=("orders", "sum"))
m2 = fun.set_index("day").resample("MS").agg(
    sessions=("sessions", "sum"),
    purchases=("sessions_that_completed_checkout", "sum"))
monthly = m1.join(m2).reset_index().rename(columns={"day": "month"})
monthly = monthly[monthly.orders > 0]
monthly["aov"] = (monthly.revenue / monthly.orders).round(0)
monthly["conversion_rate"] = (monthly.purchases / monthly.sessions).round(4)
monthly["month_label"] = monthly.month.dt.strftime("%Y-%m (%b)")
monthly.to_csv(os.path.join(OUT, "monthly_kpis.csv"), index=False)

# 2. Product Pareto with pre-computed rank + cumulative share
prod = pd.read_csv(os.path.join(RAW, "product_sales.csv"))
prod = prod[prod.product_title != "Test product"].sort_values(
    "gross_sales", ascending=False).reset_index(drop=True)
prod["rank"] = prod.index + 1
prod["cum_share_pct"] = (prod.gross_sales.cumsum() / prod.gross_sales.sum() * 100).round(1)
prod["product_label"] = prod["rank"].map("{:02d} · ".format) + prod.product_title
prod.to_csv(os.path.join(OUT, "product_pareto.csv"), index=False)

# 3. Funnel stages (long format, pre-ordered labels)
stages = [
    ("1. Sessions", fun.sessions.sum()),
    ("2. Added to cart", fun.sessions_with_cart_additions.sum()),
    ("3. Reached checkout", fun.sessions_that_reached_checkout.sum()),
    ("4. Purchased", fun.sessions_that_completed_checkout.sum()),
]
fdf = pd.DataFrame(stages, columns=["stage", "count"])
fdf["pct_of_sessions"] = (fdf["count"] / fdf["count"].iloc[0] * 100).round(1)
fdf.to_csv(os.path.join(OUT, "funnel.csv"), index=False)

# 4. Cohorts with lexically-sortable labels
coh = pd.read_csv(os.path.join(PROC, "cohort_retention.csv"), parse_dates=["cohort_month"])
coh["cohort_label"] = coh.cohort_month.dt.strftime("%Y-%m (%b)")
coh["retention_pct"] = (coh.retention_rate * 100).round(1)
coh.to_csv(os.path.join(OUT, "cohort_retention.csv"), index=False)

# 5. RFM — trim to fields the dashboard uses
rfm = pd.read_csv(os.path.join(PROC, "customers_rfm.csv"))
rfm[["customer", "recency_days", "frequency", "monetary", "avg_order_value",
     "segment", "main_city", "clv_6m_proxy"]].to_csv(
    os.path.join(OUT, "customers_rfm.csv"), index=False)

# 6. Channel revenue by month (labels)
ch = pd.read_csv(os.path.join(RAW, "monthly_sales_by_referrer.csv"), parse_dates=["month"])
ch["month_label"] = ch.month.dt.strftime("%Y-%m (%b)")
ch.to_csv(os.path.join(OUT, "monthly_sales_by_referrer.csv"), index=False)

print("dashboard extracts ready:")
for f in sorted(os.listdir(OUT)):
    print(" -", f)
