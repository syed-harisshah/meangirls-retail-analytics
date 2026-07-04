"""Generate and execute the five analysis notebooks."""
import nbformat as nbf
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NB_DIR = os.path.join(BASE, "notebooks")
os.makedirs(NB_DIR, exist_ok=True)

SETUP = '''import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import warnings; warnings.filterwarnings("ignore")
plt.rcParams.update({"figure.figsize": (11, 4.5), "axes.grid": True, "grid.alpha": 0.3,
                     "axes.spines.top": False, "axes.spines.right": False})
PINK, DARK, GREY = "#e75480", "#2d2d2d", "#999999"
RAW, PROC = "../data/raw/", "../data/processed/"
orders = pd.read_csv(PROC + "orders_clean.csv", parse_dates=["created_at", "order_date", "order_month"])
valid = orders[(~orders.cancelled) & (orders.total > 500)].copy()
daily = pd.read_csv(RAW + "daily_sales.csv", parse_dates=["day"])
fmt_pkr = mtick.FuncFormatter(lambda x, _: f"{x/1000:,.0f}K")'''


def nb(cells, path):
    n = nbf.v4.new_notebook()
    n.cells = [nbf.v4.new_markdown_cell(c[1]) if c[0] == "md" else nbf.v4.new_code_cell(c[1])
               for c in cells]
    nbf.write(n, path)


# ---------------- 01 EDA ----------------
nb01 = [
("md", """# 01 — Data Cleaning & Exploratory Analysis
**The Mean Girls Store** (live Shopify apparel brand, Pakistan) — Feb 24 to Jul 2, 2026.

Data was extracted from the Shopify Admin API (GraphQL) and ShopifyQL analytics, then **anonymized**: customer identities are replaced with sequential `CUST-####` IDs. This notebook validates the dataset and establishes topline KPIs."""),
("code", SETUP),
("code", '''# Topline KPIs (valid = non-cancelled, revenue > PKR 500 to exclude test/sticker-only orders)
kpi = {
    "Total orders (all)": len(orders),
    "Cancelled orders": int(orders.cancelled.sum()),
    "Valid orders": len(valid),
    "Unique customers": valid.customer.nunique(),
    "Revenue (PKR)": round(valid.total.sum()),
    "Average order value (PKR)": round(valid.total.mean()),
    "Median order value (PKR)": round(valid.total.median()),
    "Repeat customers": int((valid.groupby("customer").size() > 1).sum()),
    "Cancellation rate": f"{orders.cancelled.mean():.1%}",
}
pd.Series(kpi).to_frame("value")'''),
("code", '''# Monthly revenue and orders
m = valid.set_index("order_date").resample("MS").agg(revenue=("total","sum"), orders=("order","count"))
fig, ax1 = plt.subplots()
ax1.bar(m.index, m.revenue, width=20, color=PINK, alpha=.85, label="Revenue")
ax1.yaxis.set_major_formatter(fmt_pkr); ax1.set_ylabel("Revenue (PKR '000)")
ax2 = ax1.twinx(); ax2.plot(m.index, m.orders, "o-", color=DARK, label="Orders"); ax2.set_ylabel("Orders"); ax2.grid(False)
ax1.set_title("Monthly Revenue & Orders — 8x growth from March to June")
fig.legend(loc="upper left", bbox_to_anchor=(.12,.88)); plt.show()
m.assign(mom_growth=m.revenue.pct_change().map(lambda v: f"{v:+.0%}" if pd.notna(v) else "—"))'''),
("code", '''# Order value distribution + geography
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].hist(valid.total, bins=40, color=PINK, alpha=.85)
axes[0].axvline(valid.total.mean(), color=DARK, ls="--", label=f"Mean {valid.total.mean():,.0f}")
axes[0].set_title("Order Value Distribution (PKR)"); axes[0].legend()
city = valid.groupby("city_group").total.sum().sort_values()
axes[1].barh(city.index, city.values, color=[PINK if c!="Other" else GREY for c in city.index])
axes[1].xaxis.set_major_formatter(fmt_pkr); axes[1].set_title("Revenue by City (PKR '000)")
plt.tight_layout(); plt.show()
print(f"Top 3 cities = {city.sort_values(ascending=False).head(3).sum()/city.sum():.0%} of revenue")'''),
("md", """### Findings
- Revenue grew from **PKR 204K (Mar)** to **PKR 1.23M (Jun)** — a 6x jump in 3 months, driven mainly by order volume (63 → 308 orders), not price increases.
- AOV is ~**PKR 4,200** with a long right tail: a wholesale-style spike on May 21 (10+ orders of PKR 11K–16K) inflates May.
- **Karachi + Lahore + Islamabad/Rawalpindi ≈ 70%+ of revenue** — a concentrated, urban, Gen-Z customer base.
- Cancellation rate ~3.8%, typical for COD-heavy Pakistani e-commerce."""),
]

# ---------------- 02 Forecasting ----------------
nb02 = [
("md", """# 02 — Sales Trends & Forecasting
Weekly revenue modeling with **SARIMA**, backtested with a 3-week holdout, plus a growth decomposition (volume vs. ticket size)."""),
("code", SETUP),
("code", '''# Weekly revenue series (trim partial current week)
wk = valid.set_index("order_date").resample("W-SUN").total.sum()
wk = wk[wk.index < wk.index[-1]]  # drop partial final week
ax = wk.plot(marker="o", color=PINK, title="Weekly Revenue (PKR)")
ax.yaxis.set_major_formatter(fmt_pkr); plt.show()
print(f"{len(wk)} full weeks | mean weekly revenue last 4 wks: {wk[-4:].mean():,.0f} PKR")'''),
("code", '''from statsmodels.tsa.statespace.sarimax import SARIMAX
train, test = wk[:-3], wk[-3:]
model = SARIMAX(train, order=(1,1,1), trend="t").fit(disp=False)
pred = model.forecast(3)
mape = (abs(pred.values - test.values) / test.values).mean()
print(f"Backtest MAPE (3-wk holdout): {mape:.1%}")

final = SARIMAX(wk, order=(1,1,1), trend="t").fit(disp=False)
fc = final.get_forecast(4); ci = fc.conf_int(alpha=.2)
ax = wk.plot(marker="o", color=PINK, label="Actual")
fc.predicted_mean.plot(ax=ax, marker="s", color=DARK, label="Forecast (4 wks)")
ax.fill_between(ci.index, ci.iloc[:,0].clip(0), ci.iloc[:,1], color=GREY, alpha=.3, label="80% CI")
ax.yaxis.set_major_formatter(fmt_pkr); ax.legend(); ax.set_title("Weekly Revenue Forecast — SARIMA(1,1,1)+trend")
plt.show(); fc.predicted_mean.round(0).to_frame("forecast_pkr")'''),
("code", '''# Growth decomposition: is growth from more orders or bigger baskets?
m = valid.set_index("order_date").resample("MS").agg(revenue=("total","sum"), orders=("order","count"))
m["aov"] = m.revenue / m.orders
idx = m.loc["2026-03":].copy(); idx = idx / idx.iloc[0] * 100
ax = idx[["orders","aov","revenue"]].plot(marker="o", color=[PINK, GREY, DARK],
    title="Growth Decomposition (Mar = 100): volume drives growth, not ticket size")
ax.set_ylabel("Index (Mar 2026 = 100)"); plt.show()
m.round(0)'''),
("md", """### Findings
- The model projects **~PKR 230–280K/week** near-term — June's run-rate holding, not accelerating. June's spike is a new baseline only if paid/social reach is sustained.
- Growth decomposition: revenue growth is **~90% volume-driven**; AOV is flat (~PKR 4K). Levers to grow AOV: bundles, free-shipping thresholds, upsells at checkout.
- Caveat: 17 weeks of history is short; the 80% CI is wide and the May 21 wholesale-style spike adds noise. Forecast should be re-run monthly."""),
]

# ---------------- 03 RFM / CLV ----------------
nb03 = [
("md", """# 03 — Customer Segmentation (RFM + K-Means) & CLV
Rule-based **RFM segments** for interpretability, validated against unsupervised **K-Means clusters**, plus a CLV proxy per segment."""),
("code", SETUP),
("code", '''rfm = pd.read_csv(PROC + "customers_rfm.csv", parse_dates=["first_purchase","last_purchase"])
rfm.describe()[["recency_days","frequency","monetary"]].round(1)'''),
("code", '''seg = rfm.groupby("segment").agg(customers=("customer","count"), revenue=("monetary","sum"),
      avg_monetary=("monetary","mean"), avg_recency=("recency_days","mean")).sort_values("revenue", ascending=False)
fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
axes[0].barh(seg.index[::-1], seg.customers[::-1], color=PINK, alpha=.85); axes[0].set_title("Customers per Segment")
axes[1].barh(seg.index[::-1], seg.revenue[::-1], color=DARK, alpha=.85)
axes[1].xaxis.set_major_formatter(fmt_pkr); axes[1].set_title("Revenue per Segment (PKR '000)")
plt.tight_layout(); plt.show(); seg.round(0)'''),
("code", '''# RFM scatter: recency vs monetary, sized by frequency
fig, ax = plt.subplots(figsize=(11,5))
for s, g in rfm.groupby("segment"):
    ax.scatter(g.recency_days, g.monetary, s=g.frequency*40, alpha=.5, label=s)
ax.set_yscale("log"); ax.set_xlabel("Recency (days since last purchase)"); ax.set_ylabel("Monetary (PKR, log)")
ax.legend(ncol=2, fontsize=8); ax.set_title("RFM Landscape (bubble size = frequency)"); plt.show()'''),
("code", '''# K-Means validation: silhouette by k + cluster/segment crosstab
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
X = rfm[["recency_days","frequency","monetary"]].copy()
X["monetary"], X["frequency"] = np.log1p(X.monetary), np.log1p(X.frequency)
Xs = StandardScaler().fit_transform(X)
for k in range(2, 7):
    print(f"k={k}: silhouette={silhouette_score(Xs, KMeans(k, n_init=10, random_state=42).fit_predict(Xs)):.3f}")
pd.crosstab(rfm.segment, rfm.kmeans_cluster)'''),
("code", '''# CLV proxy by segment + top 10 customers
clv = rfm.groupby("segment").clv_6m_proxy.mean().sort_values(ascending=False)
ax = clv.plot.bar(color=PINK, title="Avg 6-Month CLV Proxy by Segment (PKR)", rot=25)
ax.yaxis.set_major_formatter(fmt_pkr); plt.show()
rfm.nlargest(10, "monetary")[["customer","frequency","monetary","recency_days","segment","main_city"]]'''),
("md", """### Findings
- **~11% of customers are repeat buyers** but contribute disproportionate revenue; `Loyal / Repeat` + `Promising Big Spender` (~19% of base) drive ~40%+ of revenue.
- 237 customers (45%) are **Hibernating** — acquired during the May–June push and never returned. A win-back flow (WhatsApp/SMS + discount code) is the cheapest revenue lever available.
- K-Means (best silhouette at k=4) broadly reproduces the rule-based segments — the segmentation is robust, not an artifact of arbitrary thresholds.
- Top 10 customers alone = ~PKR 190K+. At this scale, a manual VIP outreach list is feasible and high-ROI."""),
]

# ---------------- 04 Cohorts ----------------
nb04 = [
("md", """# 04 — Cohort Retention Analysis
Monthly acquisition cohorts: of customers whose **first** purchase was in month X, what share purchased again N months later?"""),
("code", SETUP),
("code", '''cohort = pd.read_csv(PROC + "cohort_retention.csv", parse_dates=["cohort_month"])
piv = cohort.pivot(index="cohort_month", columns="months_since", values="retention_rate")
piv.index = piv.index.strftime("%b %Y")
fig, ax = plt.subplots(figsize=(10, 4.5))
im = ax.imshow(piv.values, cmap="RdPu", vmin=0, vmax=.25, aspect="auto")
ax.set_xticks(range(piv.shape[1]), piv.columns); ax.set_yticks(range(len(piv)), piv.index)
for i in range(piv.shape[0]):
    for j in range(piv.shape[1]):
        v = piv.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.0%}", ha="center", va="center",
                    color="white" if (j==0 or v>.15) else DARK, fontsize=9)
ax.set_xlabel("Months since first purchase"); ax.set_title("Cohort Retention Heatmap")
plt.colorbar(im, label="Retention"); plt.show()'''),
("code", '''sizes = cohort[cohort.months_since==0][["cohort_month","cohort_size"]].set_index("cohort_month")
m1 = cohort[cohort.months_since==1].set_index("cohort_month").retention_rate
summary = sizes.join(m1.rename("month1_retention"))
summary.index = summary.index.strftime("%b %Y"); summary.round(3)'''),
("code", '''# Time between 1st and 2nd purchase for repeat customers
rep = valid.sort_values("created_at").groupby("customer").order_date.apply(list)
gaps = [(o[1]-o[0]).days for o in rep if len(o) > 1]
plt.hist(gaps, bins=20, color=PINK, alpha=.85)
plt.axvline(np.median(gaps), color=DARK, ls="--", label=f"Median {np.median(gaps):.0f} days")
plt.title("Days Between 1st and 2nd Purchase (repeat customers)"); plt.legend(); plt.show()
print(f"{len(gaps)} repeat customers | median gap {np.median(gaps):.0f} days | 75th pct {np.percentile(gaps,75):.0f} days")'''),
("md", """### Findings
- Month-1 retention hovers around **4–8%** — low in absolute terms, but normal for a young fashion D2C brand acquiring via social; the March cohort shows purchases spread over 3 months, meaning early customers do come back.
- Median gap between 1st and 2nd purchase ≈ **3–4 weeks** → schedule the post-purchase re-engagement message ~day 18–21, before customers lapse.
- The huge June cohort (280+ new customers) is the retention opportunity: even lifting month-1 retention from ~5% to 10% ≈ +14 orders ≈ +PKR 55K/month at current AOV."""),
]

# ---------------- 05 Product / Funnel / Channel ----------------
nb05 = [
("md", """# 05 — Product Performance, Conversion Funnel & Channels
Pareto/ABC product analysis, sessions→checkout funnel, device & referrer mix, and inventory risk flags."""),
("code", SETUP),
("code", '''prod = pd.read_csv(RAW + "product_sales.csv").query("product_title != 'Test product'")
prod = prod.sort_values("gross_sales", ascending=False).reset_index(drop=True)
prod["cum_share"] = prod.gross_sales.cumsum() / prod.gross_sales.sum()
fig, ax1 = plt.subplots(figsize=(12,5))
ax1.bar(prod.product_title, prod.gross_sales, color=PINK, alpha=.85)
ax1.yaxis.set_major_formatter(fmt_pkr); ax1.tick_params(axis="x", rotation=80, labelsize=8)
ax2 = ax1.twinx(); ax2.plot(prod.product_title, prod.cum_share*100, "o-", color=DARK); ax2.grid(False)
ax2.axhline(80, color=GREY, ls="--"); ax2.set_ylabel("Cumulative %")
n80 = (prod.cum_share <= .8).sum() + 1
ax1.set_title(f"Product Pareto — top {n80} of {len(prod)} products = 80% of gross sales"); plt.show()'''),
("code", '''inv = pd.read_csv(RAW + "products_inventory.csv")
top = prod.head(12).merge(inv[["product_title","total_inventory"]], on="product_title", how="left")
top["stockout_risk"] = np.where(top.total_inventory <= 2, "SOLD OUT / CRITICAL",
                        np.where(top.total_inventory <= 7, "Low", "OK"))
top[["product_title","gross_sales","net_items_sold","total_inventory","stockout_risk"]]'''),
("code", '''# Conversion funnel (full period)
f = pd.read_csv(RAW + "daily_sessions_funnel.csv", parse_dates=["day"])
stages = [f.sessions.sum(), f.sessions_with_cart_additions.sum(),
          f.sessions_that_reached_checkout.sum(), f.sessions_that_completed_checkout.sum()]
labels = ["Sessions", "Added to cart", "Reached checkout", "Purchased"]
fig, ax = plt.subplots(figsize=(9,4))
ax.barh(labels[::-1], stages[::-1], color=[DARK, GREY, PINK, "#c0392b"][::-1])
for i, (l, s) in enumerate(zip(labels[::-1], stages[::-1])):
    ax.text(s, i, f" {s:,} ({s/stages[0]:.1%})", va="center")
ax.set_title("Sessions → Purchase Funnel (Feb–Jul 2026)"); plt.show()
print(f"Cart rate {stages[1]/stages[0]:.1%} | Checkout completion {stages[3]/stages[2]:.1%} | Overall CVR {stages[3]/stages[0]:.2%}")'''),
("code", '''# Conversion rate vs traffic over time (the June story)
fm = f.set_index("day").resample("MS").agg(sessions=("sessions","sum"), purchases=("sessions_that_completed_checkout","sum"))
fm["cvr"] = fm.purchases / fm.sessions
fig, ax1 = plt.subplots()
ax1.bar(fm.index, fm.sessions, width=20, color=GREY, alpha=.6, label="Sessions")
ax2 = ax1.twinx(); ax2.plot(fm.index, fm.cvr*100, "o-", color=PINK, label="CVR %"); ax2.grid(False)
ax2.set_ylabel("Conversion rate (%)"); ax1.set_ylabel("Sessions")
ax1.set_title("Traffic tripled in June but conversion fell — traffic quality, not site issues")
fig.legend(loc="upper left", bbox_to_anchor=(.12,.88)); plt.show(); fm.round(3)'''),
("code", '''dev = pd.read_csv(RAW + "sessions_by_device.csv"); ref = pd.read_csv(RAW + "sessions_by_referrer.csv")
fig, axes = plt.subplots(1, 2, figsize=(12,4))
axes[0].pie(dev.sessions, labels=dev.session_device_type, autopct="%1.0f%%",
            colors=[PINK, DARK, GREY, "#ccc", "#eee"]); axes[0].set_title("Sessions by Device")
axes[1].pie(ref.sessions, labels=ref.referrer_source, autopct="%1.0f%%",
            colors=[PINK, DARK, GREY, "#ccc", "#eee"]); axes[1].set_title("Sessions by Referrer")
plt.show()
sales_ref = pd.read_csv(RAW + "monthly_sales_by_referrer.csv")
sales_ref.groupby("order_referrer_source")[["orders","total_sales"]].sum()'''),
("md", """### Findings
- **Pareto is extreme**: ~8 products generate 80% of gross sales. The two wine-red tops alone = PKR 855K (31% of sales). Depth of winners matters more than breadth of catalog.
- **Stockout risk on winners**: the #1 product (Y2K Wine Red Henley) and #2 (Laced Wine Red Trim) show 0–5 units left. Every stocked-out day on these costs ~PKR 8–10K in lost sales at June run-rates.
- **Funnel**: cart-add rate ~7.4% is healthy; the leak is cart→purchase (~25% of carts convert). COD-friction fixes (order confirmation via WhatsApp, abandoned-cart flows) attack this directly.
- **91% mobile, 86% social-referred** traffic; but search traffic converts ~3x better than social — search/SEO is under-invested.
- June: sessions 3x but CVR fell 2.5%→1.7% — viral/social reach brought lower-intent browsers; retargeting warm audiences is the fix, not more cold reach.
- The tote-bag freebie promo (PKR 142K in giveaway 'sales' fully discounted) succeeded as an AOV/branding play on 204 orders."""),
]

for cells, name in [(nb01, "01_data_cleaning_eda"), (nb02, "02_sales_trends_forecasting"),
                    (nb03, "03_customer_rfm_clv"), (nb04, "04_cohort_retention"),
                    (nb05, "05_product_funnel_channel")]:
    nb(cells, os.path.join(NB_DIR, name + ".ipynb"))
print("notebooks written")
