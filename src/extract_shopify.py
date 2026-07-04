"""
Reference extraction script — Shopify Admin GraphQL API.

The committed raw data was pulled with these exact queries (orders paginated
50 at a time) plus ShopifyQL analytics queries for aggregates (daily sales,
sessions/funnel, device & referrer mixes).

To re-run against your own store:
    export SHOPIFY_SHOP="your-store.myshopify.com"
    export SHOPIFY_TOKEN="shpat_..."   # Admin API access token (read_orders)
    python src/extract_shopify.py
"""

import csv
import os

import requests

SHOP = os.environ.get("SHOPIFY_SHOP")
TOKEN = os.environ.get("SHOPIFY_TOKEN")
API = f"https://{SHOP}/admin/api/2026-01/graphql.json"

ORDERS_QUERY = """
query($first: Int!, $after: String) {
  orders(first: $first, after: $after, query: "created_at:>=2026-02-01") {
    edges {
      node {
        name
        createdAt
        cancelledAt
        totalPriceSet { shopMoney { amount } }
        customer { id }
        shippingAddress { city }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def run(query, variables):
    r = requests.post(
        API,
        json={"query": query, "variables": variables},
        headers={"X-Shopify-Access-Token": TOKEN},
        timeout=30,
    )
    r.raise_for_status()
    payload = r.json()
    if "errors" in payload:
        raise RuntimeError(payload["errors"])
    return payload["data"]


def extract_orders(out_path="data/raw/orders_all.csv"):
    rows, cursor = [], None
    while True:
        data = run(ORDERS_QUERY, {"first": 50, "after": cursor})["orders"]
        for edge in data["edges"]:
            n = edge["node"]
            rows.append({
                "order": n["name"],
                "created_at": n["createdAt"],
                "cancelled_at": n["cancelledAt"] or "",
                "total": n["totalPriceSet"]["shopMoney"]["amount"],
                "customer_id": (n["customer"] or {}).get("id", "").split("/")[-1],
                "city": (n["shippingAddress"] or {}).get("city", ""),
            })
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} orders -> {out_path}")


if __name__ == "__main__":
    if not (SHOP and TOKEN):
        raise SystemExit("Set SHOPIFY_SHOP and SHOPIFY_TOKEN env vars first.")
    extract_orders()
