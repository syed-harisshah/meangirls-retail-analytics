"""
Build processed, anonymized datasets from raw Shopify extracts.

Pipeline:
  1. Combine paginated order extracts
  2. Anonymize customer IDs (sequential CUST-#### by first purchase date)
  3. Clean city names, flag cancellations
  4. Engineer RFM features + K-means segments
  5. Build monthly cohort retention matrix
  6. Export Tableau-ready extracts

Author: Syed Haris Shah
"""

import glob
import os

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
PROCESSED = os.path.join(BASE, "data", "processed")
TABLEAU = os.path.join(BASE, "tableau", "extracts")
os.makedirs(PROCESSED, exist_ok=True)
os.makedirs(TABLEAU, exist_ok=True)

SNAPSHOT_DATE = pd.Timestamp("2026-07-02")

CITY_FIXES = {
    "karachi": "Karachi", "lahore": "Lahore", "islamabad": "Islamabad",
    "rawalpindi": "Rawalpindi", "hyderabad": "Hyderabad", "faisalabad": "Faisalabad",
    "faislabad": "Faisalabad", "hyd": "Hyderabad", "karchi": "Karachi",
    "quetta": "Quetta", "sialkot": "Sialkot", "multan": "Multan",
    "gujranwala": "Gujranwala", "peshawar": "Peshawar", "okara": "Okara",
    "rwp,isb": "Rawalpindi", "lahore , green city": "Lahore",
    "hyderabad sindh": "Hyderabad", "sindh mirpurkhas": "Mirpurkhas",
    "lahore bahria town": "Lahore", "lahore iqbal town": "Lahore",
    "model town lahore": "Lahore", "punjab, multan": "Multan",
    "mansehra, kpk": "Mansehra", "wah, taxila": "Taxila",
    "rahim yaar khan": "Rahim Yar Khan", "khairpur mirs": "Khairpur",
    "chistian": "Chishtian", "gojra, punjab": "Gojra", "sheikhpura": "Sheikhupura",
    "muzzafargarh": "Muzaffargarh", "abbotabad": "Abbottabad",
    "naudeor": "Naudero", "kahuta": "Kahuta", "punjab": "Other (Punjab)",
    "renala khurd district okara": "Renala Khurd",
    "lalchandabad, mirpurkhas": "Mirpurkhas", "karachi by": "Karachi",
    "rawalpindi street number 5 kahut house west shabeer lane": "Rawalpindi",
    "village saghar pur": "Other (Punjab)", "mirpur ajk": "Mirpur (AJK)",
    "muzaffarabad": "Muzaffarabad (AJK)",
}

MAJOR_CITIES = {
    "Karachi", "Lahore", "Islamabad", "Rawalpindi", "Hyderabad",
    "Faisalabad", "Multan", "Gujranwala", "Peshawar", "Sialkot",
}


def clean_city(c):
    if not isinstance(c, str) or not c.strip():
        return "Unknown"
    key = c.strip().lower()
    return CITY_FIXES.get(key, c.strip().title())


def load_orders():
    files = sorted(
        glob.glob(os.path.join(RAW, "orders_p*.csv")),
        key=lambda f: int("".join(filter(str.isdigit, os.path.basename(f)))),
    )
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["cancelled"] = df["cancelled_at"].notna()
    df["city"] = df["city"].apply(clean_city)
    df["city_group"] = df["city"].where(df["city"].isin(MAJOR_CITIES), "Other")
    df["order_date"] = df["created_at"].dt.tz_localize(None).dt.normalize()
    df["order_month"] = df["order_date"].dt.to_period("M").dt.to_timestamp()
    return df


def anonymize(df):
    """Map raw Shopify customer IDs to CUST-#### ordered by first purchase.

    The committed raw files are already anonymized (column `customer`);
    this step only runs on a fresh extract that still has `customer_id`.
    """
    if "customer" in df.columns:
        return df
    first_seen = df.groupby("customer_id")["created_at"].min().sort_values()
    mapping = {cid: f"CUST-{i+1:04d}" for i, cid in enumerate(first_seen.index)}
    df["customer"] = df["customer_id"].map(mapping)
    return df.drop(columns=["customer_id"])


def build_rfm(orders):
    """RFM on valid (non-cancelled, revenue > 0) orders."""
    valid = orders[(~orders["cancelled"]) & (orders["total"] > 500)].copy()
    rfm = valid.groupby("customer").agg(
        first_purchase=("order_date", "min"),
        last_purchase=("order_date", "max"),
        frequency=("order", "count"),
        monetary=("total", "sum"),
        avg_order_value=("total", "mean"),
        main_city=("city_group", lambda s: s.mode().iloc[0]),
    ).reset_index()
    rfm["recency_days"] = (SNAPSHOT_DATE - rfm["last_purchase"]).dt.days
    rfm["tenure_days"] = (SNAPSHOT_DATE - rfm["first_purchase"]).dt.days

    # Quintile scores (5 = best). Frequency is heavily skewed to 1 → rank-based.
    rfm["R_score"] = pd.qcut(rfm["recency_days"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F_score"] = rfm["frequency"].clip(upper=5).astype(int)
    rfm["M_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 5,
                             labels=[1, 2, 3, 4, 5]).astype(int)

    def label(row):
        r, f, m = row["R_score"], row["F_score"], row["M_score"]
        if f >= 2 and r >= 4:
            return "Loyal / Repeat"
        if f >= 2 and r <= 3:
            return "At-Risk Repeat"
        if r >= 4 and m >= 4:
            return "Promising Big Spender"
        if r >= 4:
            return "Recent One-Timer"
        if r <= 2 and m >= 4:
            return "Lost Big Spender"
        return "Hibernating"

    rfm["segment"] = rfm.apply(label, axis=1)

    # K-means (k=4) on scaled log features as an ML complement
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    X = rfm[["recency_days", "frequency", "monetary"]].copy()
    X["monetary"] = np.log1p(X["monetary"])
    X["frequency"] = np.log1p(X["frequency"])
    Xs = StandardScaler().fit_transform(X)
    km = KMeans(n_clusters=4, n_init=10, random_state=42).fit(Xs)
    rfm["kmeans_cluster"] = km.labels_

    # Simple historical CLV proxy: monetary * expected repeat multiplier
    repeat_rate = (rfm["frequency"] > 1).mean()
    rfm["clv_6m_proxy"] = rfm["monetary"] * (1 + repeat_rate * (rfm["F_score"] / 2))
    return rfm


def build_cohorts(orders):
    valid = orders[(~orders["cancelled"]) & (orders["total"] > 500)].copy()
    first_month = valid.groupby("customer")["order_month"].min().rename("cohort_month")
    valid = valid.join(first_month, on="customer")
    valid["months_since"] = (
        (valid["order_month"].dt.year - valid["cohort_month"].dt.year) * 12
        + (valid["order_month"].dt.month - valid["cohort_month"].dt.month)
    )
    cohort = (
        valid.groupby(["cohort_month", "months_since"])["customer"]
        .nunique().reset_index(name="customers")
    )
    sizes = cohort[cohort["months_since"] == 0][["cohort_month", "customers"]]
    sizes = sizes.rename(columns={"customers": "cohort_size"})
    cohort = cohort.merge(sizes, on="cohort_month")
    cohort["retention_rate"] = cohort["customers"] / cohort["cohort_size"]
    return cohort


def main():
    orders = anonymize(load_orders())
    orders.to_csv(os.path.join(PROCESSED, "orders_clean.csv"), index=False)

    rfm = build_rfm(orders)
    rfm.to_csv(os.path.join(PROCESSED, "customers_rfm.csv"), index=False)

    cohort = build_cohorts(orders)
    cohort.to_csv(os.path.join(PROCESSED, "cohort_retention.csv"), index=False)

    # Tableau extracts (copies + already-aggregated raw pulls)
    orders.to_csv(os.path.join(TABLEAU, "orders.csv"), index=False)
    rfm.to_csv(os.path.join(TABLEAU, "customers_rfm.csv"), index=False)
    cohort.to_csv(os.path.join(TABLEAU, "cohort_retention.csv"), index=False)
    for f in ["daily_sales.csv", "daily_sessions_funnel.csv", "product_sales.csv",
              "sessions_by_device.csv", "sessions_by_referrer.csv",
              "monthly_sales_by_referrer.csv"]:
        pd.read_csv(os.path.join(RAW, f)).to_csv(os.path.join(TABLEAU, f), index=False)

    print("Orders:", len(orders), "| Cancelled:", orders["cancelled"].sum())
    print("Customers:", rfm.shape[0], "| Repeat:", (rfm["frequency"] > 1).sum())
    print("Segments:\n", rfm["segment"].value_counts())
    print("Revenue (valid):", orders.loc[(~orders.cancelled) & (orders.total > 500), "total"].sum())


if __name__ == "__main__":
    main()
