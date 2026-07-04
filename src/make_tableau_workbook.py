"""Generate meangirls_dashboard.twb — a 4-dashboard Tableau workbook.

A .twb is XML: datasources (connections to the extract CSVs), worksheets
(shelf definitions), and dashboards (layout zones). All heavy computation was
pre-baked into the CSVs by build_dashboard_data.py, so every worksheet here is
a simple mark type + two shelves.
"""

import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTS = "/Users/harisshah/Documents/Meangirls/meangirls-retail-analytics/tableau/extracts"
OUT = os.path.join(BASE, "tableau", "meangirls_dashboard.twb")

PINK = "#e75480"

# ---------- datasource definitions ----------
# name -> (filename, caption, {field: (datatype, role, type)})
DATASOURCES = {
    "federated.mk": ("monthly_kpis.csv", "Monthly KPIs", {
        "month_label": ("string", "dimension", "nominal"),
        "revenue": ("real", "measure", "quantitative"),
        "orders": ("integer", "measure", "quantitative"),
        "sessions": ("integer", "measure", "quantitative"),
        "aov": ("real", "measure", "quantitative"),
        "conversion_rate": ("real", "measure", "quantitative"),
    }),
    "federated.rf": ("customers_rfm.csv", "Customers RFM", {
        "customer": ("string", "dimension", "nominal"),
        "recency_days": ("integer", "measure", "quantitative"),
        "frequency": ("integer", "measure", "quantitative"),
        "monetary": ("real", "measure", "quantitative"),
        "segment": ("string", "dimension", "nominal"),
        "clv_6m_proxy": ("real", "measure", "quantitative"),
    }),
    "federated.co": ("cohort_retention.csv", "Cohort Retention", {
        "cohort_label": ("string", "dimension", "nominal"),
        "months_since": ("integer", "dimension", "ordinal"),
        "retention_pct": ("real", "measure", "quantitative"),
        "cohort_size": ("integer", "measure", "quantitative"),
    }),
    "federated.pp": ("product_pareto.csv", "Product Pareto", {
        "product_label": ("string", "dimension", "nominal"),
        "gross_sales": ("real", "measure", "quantitative"),
        "rank": ("integer", "measure", "quantitative"),
        "cum_share_pct": ("real", "measure", "quantitative"),
    }),
    "federated.fn": ("funnel.csv", "Funnel", {
        "stage": ("string", "dimension", "nominal"),
        "count": ("integer", "measure", "quantitative"),
        "pct_of_sessions": ("real", "measure", "quantitative"),
    }),
    "federated.ch": ("monthly_sales_by_referrer.csv", "Channel Revenue", {
        "month_label": ("string", "dimension", "nominal"),
        "order_referrer_source": ("string", "dimension", "nominal"),
        "total_sales": ("real", "measure", "quantitative"),
    }),
}


def ds_xml(name, filename, caption, fields):
    conn = name.replace("federated.", "textscan.")
    table = filename.replace(".csv", "#csv")
    cols = "\n".join(
        f"      <column datatype='{dt}' name='[{f}]' role='{role}' type='{tp}' />"
        for f, (dt, role, tp) in fields.items())
    return f"""  <datasource caption='{caption}' inline='true' name='{name}' version='18.1'>
    <connection class='federated'>
      <named-connections>
        <named-connection caption='extracts' name='{conn}'>
          <connection class='textscan' directory='{EXTRACTS}' filename='{filename}' password='' server='' />
        </named-connection>
      </named-connections>
      <relation connection='{conn}' name='{filename}' table='[{table}]' type='table' />
    </connection>
    <aliases enabled='yes' />
{cols}
  </datasource>"""


# ---------- worksheet builder ----------
def inst(ds, field, agg, tp):
    """column-instance name, e.g. [sum:revenue:qk]"""
    suffix = {"quantitative": "qk", "nominal": "nk", "ordinal": "ok"}[tp]
    return f"[{agg}:{field}:{suffix}]"


def ws_xml(name, ds, mark, rows, cols, color=None, size=None, text=None,
           aggregated=True, sort=None):
    """rows/cols/color/size/text are (field, agg, type) tuples."""
    fields = DATASOURCES[ds][2]
    used = [t for t in [rows, cols, color, size, text] if t]
    dep_cols, dep_inst, seen = [], [], set()
    for f, agg, tp in used:
        dt, role, ftp = fields[f]
        if f not in seen:
            dep_cols.append(f"        <column datatype='{dt}' name='[{f}]' role='{role}' type='{ftp}' />")
            seen.add(f)
        iname = inst(ds, f, agg, tp)
        if iname not in [d[0] for d in dep_inst]:
            deriv = {"none": "None", "sum": "Sum", "avg": "Avg"}[agg]
            dep_inst.append((iname,
                f"        <column-instance column='[{f}]' derivation='{deriv}' "
                f"name='{iname}' pivot='key' type='{tp}' />"))
    deps = "\n".join(dep_cols + [d[1] for d in dep_inst])

    enc = ""
    if color or size or text:
        parts = []
        if color:
            parts.append(f"            <color column='[{ds}].{inst(ds, *color)}' />")
        if size:
            parts.append(f"            <size column='[{ds}].{inst(ds, *size)}' />")
        if text:
            parts.append(f"            <text column='[{ds}].{inst(ds, *text)}' />")
        enc = "          <encodings>\n" + "\n".join(parts) + "\n          </encodings>"

    sort_xml = ""  # <sort> is rejected by the workbook XML schema; sorting is applied in the UI instead

    style = ("      <style>\n        <style-rule element='mark'>\n"
             f"          <format attr='mark-color' value='{PINK}' />\n"
             "        </style-rule>\n      </style>" if not color else "      <style />")

    return f"""  <worksheet name='{name}'>
    <table>
      <view>
        <datasources>
          <datasource caption='{DATASOURCES[ds][1]}' name='{ds}' />
        </datasources>
        <datasource-dependencies datasource='{ds}'>
{deps}
        </datasource-dependencies>
        <aggregation value='{"true" if aggregated else "false"}' />
      </view>
{sort_xml}
{style}
      <panes>
        <pane selection-relaxation-option='selection-relaxation-allow'>
          <view>
            <breakdown value='auto' />
          </view>
          <mark class='{mark}' />
{enc}
        </pane>
      </panes>
      <rows>[{ds}].{inst(ds, *rows)}</rows>
      <cols>[{ds}].{inst(ds, *cols)}</cols>
    </table>
  </worksheet>"""


WORKSHEETS = [
    # Executive
    ws_xml("Monthly Revenue", "federated.mk", "Bar",
           rows=("revenue", "sum", "quantitative"), cols=("month_label", "none", "nominal")),
    ws_xml("Monthly Orders", "federated.mk", "Line",
           rows=("orders", "sum", "quantitative"), cols=("month_label", "none", "nominal")),
    # Customers
    ws_xml("RFM Scatter", "federated.rf", "Circle",
           rows=("monetary", "none", "quantitative"), cols=("recency_days", "none", "quantitative"),
           color=("segment", "none", "nominal"), size=("frequency", "none", "quantitative"),
           aggregated=False),
    ws_xml("Revenue by Segment", "federated.rf", "Bar",
           rows=("segment", "none", "nominal"), cols=("monetary", "sum", "quantitative"),
           sort=("segment", "nominal", "monetary")),
    ws_xml("Cohort Heatmap", "federated.co", "Square",
           rows=("cohort_label", "none", "nominal"), cols=("months_since", "none", "ordinal"),
           color=("retention_pct", "avg", "quantitative"), text=("retention_pct", "avg", "quantitative")),
    ws_xml("Avg CLV by Segment", "federated.rf", "Bar",
           rows=("segment", "none", "nominal"), cols=("clv_6m_proxy", "avg", "quantitative"),
           sort=("segment", "nominal", "clv_6m_proxy")),
    # Products
    ws_xml("Product Pareto", "federated.pp", "Bar",
           rows=("product_label", "none", "nominal"), cols=("gross_sales", "sum", "quantitative")),
    ws_xml("Cumulative Share", "federated.pp", "Line",
           rows=("cum_share_pct", "avg", "quantitative"), cols=("rank", "none", "quantitative"),
           aggregated=False),
    # Growth
    ws_xml("Conversion Funnel", "federated.fn", "Bar",
           rows=("stage", "none", "nominal"), cols=("count", "sum", "quantitative"),
           text=("pct_of_sessions", "avg", "quantitative")),
    ws_xml("Sessions by Month", "federated.mk", "Bar",
           rows=("sessions", "sum", "quantitative"), cols=("month_label", "none", "nominal")),
    ws_xml("Conversion Rate by Month", "federated.mk", "Line",
           rows=("conversion_rate", "avg", "quantitative"), cols=("month_label", "none", "nominal")),
    ws_xml("Revenue by Channel", "federated.ch", "Bar",
           rows=("total_sales", "sum", "quantitative"), cols=("month_label", "none", "nominal"),
           color=("order_referrer_source", "none", "nominal")),
]

# ---------- dashboards ----------
_zid = [100]
def zid():
    _zid[0] += 1
    return _zid[0]


def text_zone(x, y, w, h, runs):
    body = "".join(f"<run{attrs}>{txt}</run>" for attrs, txt in runs)
    return (f"      <zone h='{h}' id='{zid()}' type-v2='text' w='{w}' x='{x}' y='{y}'>\n"
            f"        <formatted-text>{body}</formatted-text>\n      </zone>")


def sheet_zone(name, x, y, w, h):
    return f"      <zone h='{h}' id='{zid()}' name='{name}' w='{w}' x='{x}' y='{y}' />"


def dashboard(name, zones):
    inner = "\n".join(zones)
    return f"""  <dashboard name='{name}'>
    <style />
    <size maxheight='850' maxwidth='1350' minheight='850' minwidth='1350' />
    <zones>
      <zone h='100000' id='{zid()}' type-v2='layout-basic' w='100000' x='0' y='0'>
{inner}
      </zone>
    </zones>
  </dashboard>"""


def title(text_):
    return text_zone(0, 0, 100000, 7000,
                     [(" bold='true' fontsize='16'", text_)])


DASHBOARDS = [
    dashboard("1 · Executive Overview", [
        title("The Mean Girls Store — Executive Overview (Feb–Jul 2026, PKR)"),
        text_zone(0, 7000, 100000, 8000, [(" fontsize='11'",
            "Revenue PKR 2.53M · 602 valid orders · 531 customers · AOV PKR 4,205 · repeat rate 11% · cancellation 3.8%")]),
        sheet_zone("Monthly Revenue", 0, 15000, 50000, 80000),
        sheet_zone("Monthly Orders", 50000, 15000, 50000, 80000),
        text_zone(0, 95000, 100000, 5000, [(" fontsize='10' italic='true'",
            "Insight: revenue grew 6x Mar-Jun, driven by order volume - AOV stayed flat.")]),
    ]),
    dashboard("2 · Customer Intelligence", [
        title("Customer Intelligence — RFM Segments, Cohorts &amp; CLV"),
        sheet_zone("RFM Scatter", 0, 7000, 55000, 45000),
        sheet_zone("Revenue by Segment", 55000, 7000, 45000, 45000),
        sheet_zone("Cohort Heatmap", 0, 52000, 55000, 43000),
        sheet_zone("Avg CLV by Segment", 55000, 52000, 45000, 43000),
        text_zone(0, 95000, 100000, 5000, [(" fontsize='10' italic='true'",
            "Insight: 45% of customers are Hibernating; repeat buyers reorder within a median of 8 days.")]),
    ]),
    dashboard("3 · Product Performance", [
        title("Product Performance — Pareto &amp; Cumulative Share"),
        sheet_zone("Product Pareto", 0, 7000, 60000, 88000),
        sheet_zone("Cumulative Share", 60000, 7000, 40000, 60000),
        text_zone(60000, 67000, 40000, 28000, [(" fontsize='10' italic='true'",
            "Insight: 8 of 28 products = 80% of gross sales. The two wine-red tops alone = PKR 855K (31%) - and both are near stockout.")]),
    ]),
    dashboard("4 · Growth &amp; Channels", [
        title("Growth &amp; Channels — Funnel, Traffic Quality, Attribution"),
        sheet_zone("Conversion Funnel", 0, 7000, 50000, 44000),
        sheet_zone("Revenue by Channel", 50000, 7000, 50000, 44000),
        sheet_zone("Sessions by Month", 0, 51000, 50000, 44000),
        sheet_zone("Conversion Rate by Month", 50000, 51000, 50000, 44000),
        text_zone(0, 95000, 100000, 5000, [(" fontsize='10' italic='true'",
            "Insight: June sessions tripled but conversion fell 2.8% to 1.7%. Search converts ~9x better than social.")]),
    ]),
]

WINDOWS = ""  # <windows> requires nested cards/viewpoint structure; omit — Tableau rebuilds it

xml = f"""<?xml version='1.0' encoding='utf-8' ?>
<workbook source-build='2023.1.0 (20231.23.0308.1636)' source-platform='mac' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <preferences>
    <preference name='ui.encoding.shelf.height' value='24' />
  </preferences>
  <datasources>
{chr(10).join(ds_xml(n, *d[:2], d[2]) for n, d in DATASOURCES.items())}
  </datasources>
  <worksheets>
{chr(10).join(WORKSHEETS)}
  </worksheets>
  <dashboards>
{chr(10).join(DASHBOARDS)}
  </dashboards>
</workbook>
"""

with open(OUT, "w", encoding="utf-8") as f:
    f.write(xml)

from lxml import etree
etree.parse(OUT)  # raises if malformed
print("Workbook written and XML-validated:", OUT)
