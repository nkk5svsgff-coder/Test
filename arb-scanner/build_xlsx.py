#!/usr/bin/env python3
"""Build Arbitrage_Ledger.xlsx from data/master_opportunities.json."""

import json
import os

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
data = json.load(open(os.path.join(D, "master_opportunities.json")))
rows, W = data["rows"], data["weights_default"]

ARIAL = "Arial"
F = lambda **kw: Font(name=ARIAL, **kw)
HDR_FILL = PatternFill("solid", fgColor="1C2321")
TIER1 = PatternFill("solid", fgColor="E1F0E7")
TIER2 = PatternFill("solid", fgColor="F4F7F2")
INPUT_FILL = PatternFill("solid", fgColor="FFFF00")
WARN_FILL = PatternFill("solid", fgColor="F7EDDC")
THIN = Border(bottom=Side(style="thin", color="D9D9D9"))
WRAP = Alignment(wrap_text=True, vertical="top")

wb = Workbook()

# ---------------- READ ME ----------------
rm = wb.active
rm.title = "READ ME"
rm.column_dimensions["A"].width = 118
lines = [
    ("ARBITRAGE LEDGER - ranked live opportunities", 14, True),
    (f"Generated {data['generated']} from six live scanners: 11 crypto exchanges (~9,500 pairs), Polymarket + Kalshi order books,", 10, False),
    ("Deribit options (818 instruments), Gate delivery futures, OKX P2P fiat books (18 currencies), DefiLlama (15,588 pools),", 10, False),
    ("Skinport (21k items), ECB ESTR. Every row was measured, and the top rows verified against live order-book depth.", 10, False),
    ("", 10, False),
    ("HOW THE RANKING WORKS", 12, True),
    ("Score = w1*EdgeScore + w2*RepeatScore + w3*CapacityScore + w4*EaseScore - w5*RiskScore  (all subscores 0-10).", 10, False),
    ("The five weights are YELLOW input cells on the 'Ranked Master' sheet (row 2) - change them and every Score recalculates.", 10, False),
    ("Rows are ordered by the default weighting. The 'Score' column is the default-weight value; the last column", 10, False),
    ("'Score (your weights)' is a live formula that recomputes from the yellow weight cells when opened in Excel/Sheets.", 10, False),
    ("Ease = practical accessibility for an EU/Greece-based individual (5 = one afternoon, 1 = needs rails you don't have).", 10, False),
    ("Risk = 1 riskless-at-fill ... 5 speculative. 'Verified' names the primary evidence behind the numbers.", 10, False),
    ("", 10, False),
    ("READ THIS BEFORE TRADING ANYTHING", 12, True),
    ("1. No row in this file makes anyone a millionaire fast. That claim was tested six ways and is arithmetically impossible:", 10, False),
    ("   a repeatable riskless 1% edge compounding freely would exceed global wealth within days - so every real edge is", 10, False),
    ("   capacity-capped, and the caps are printed per row. Anyone selling a faster version is selling you exit liquidity.", 10, False),
    ("2. The honest fast-wealth path this data supports: (a) harvest the small verified edges daily, (b) keep the scanner loop", 10, False),
    ("   running so you are FIRST into rare dislocations (the Mar-2023 USDC depeg paid ~3-8% riskless at size to whoever was", 10, False),
    ("   ready), (c) compound and scale skill into market-making, which is how every real arbitrage fortune was built.", 10, False),
    ("3. Rows marked risk>=3 can lose money. Inventory risk in market-making is larger than the per-cycle edge.", 10, False),
    ("4. Numbers age fast: sweeps refill/vanish in hours, funding flips in days, basis converges at expiry.", 10, False),
    ("   The refresh loop regenerates this file; check 'Measured at' per row.", 10, False),
    ("5. Greek tax applies to gains; commercial-scale P2P activity can require licensing. This is research, not advice.", 10, False),
]
for i, (txt, size, bold) in enumerate(lines, 1):
    c = rm.cell(row=i, column=1, value=txt)
    c.font = F(size=size, bold=bold)
    c.alignment = Alignment(wrap_text=False)

# ---------------- Ranked Master ----------------
ms = wb.create_sheet("Ranked Master")
headers = ["Rank", "Score", "Category", "Opportunity", "Where", "Edge", "Edge unit",
           "Cycle time", "Repeats per day", "Capacity ($)", "Verified by", "Ease 1-5",
           "Risk 1-5", "Risk notes", "How to execute", "Est $ per day @ $10k", "Measured at",
           "EdgeScore", "RepeatScore", "CapacityScore", "EaseScore", "RiskScore", "Score (your weights)"]
widths = [5, 7, 20, 42, 22, 8, 26, 16, 16, 12, 24, 7, 7, 46, 52, 12, 17, 8, 8, 8, 8, 8, 11]

# weight inputs row 1-2
ms.cell(row=1, column=18, value="Weights:").font = F(bold=True, size=9)
wnames = ["edge", "repeat", "capacity", "ease", "risk (subtracted)"]
for j, (wn, wv) in enumerate(zip(wnames, [W["edge"], W["repeat"], W["capacity"], W["ease"], W["risk"]])):
    lab = ms.cell(row=1, column=19 + j, value=wn)
    lab.font = F(size=8); lab.alignment = Alignment(horizontal="center")
    c = ms.cell(row=2, column=19 + j, value=wv)
    c.font = F(color="0000FF", bold=True); c.fill = INPUT_FILL
    c.number_format = "0.00"; c.alignment = Alignment(horizontal="center")
ms.cell(row=2, column=18, value="edit these ->").font = F(size=8, italic=True)

HR = 3  # header row
for j, (h, w) in enumerate(zip(headers, widths), 1):
    c = ms.cell(row=HR, column=j, value=h)
    c.font = F(bold=True, color="FFFFFF", size=9)
    c.fill = HDR_FILL
    c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    ms.column_dimensions[get_column_letter(j)].width = w
ms.freeze_panes = f"E{HR+1}"

wcell = lambda j: f"${get_column_letter(19 + j)}$2"
for i, r in enumerate(rows):
    rr = HR + 1 + i
    subs = [r["edge_score"], r["repeat_score"], r["capacity_score"], r["ease_score"], r["risk_score"]]
    vals = [i + 1, r["score_default"], r["category"], r["name"], r["where"], r["edge_value"], r["edge_unit"],
            r["cycle_time"], str(r["repeats_per_day"]), r["capacity_usd"], r["verified"],
            r["ease"], r["risk"], r["risk_notes"], r["how"], r["usd_per_day_10k"],
            r["measured_at"], *subs]
    for j, v in enumerate(vals, 1):
        c = ms.cell(row=rr, column=j, value=v)
        c.font = F(size=9)
        c.border = THIN
        if j in (4, 7, 8, 9, 11, 14, 15):
            c.alignment = WRAP
        if j == 6:
            c.number_format = "0.00"
        if j == 10:
            c.number_format = "#,##0"
        if j == 16:
            c.number_format = "0.0"
    ms.cell(row=rr, column=2).font = F(size=9, bold=True)
    ms.cell(row=rr, column=2).number_format = "0.00"
    # live formula column: recomputes with the yellow weights when opened in Excel
    sc = ms.cell(row=rr, column=23,
                 value=(f"={wcell(0)}*R{rr}+{wcell(1)}*S{rr}+{wcell(2)}*T{rr}"
                        f"+{wcell(3)}*U{rr}-{wcell(4)}*V{rr}"))
    sc.font = F(size=9)
    sc.number_format = "0.00"
    sc.border = THIN
    fill = TIER1 if i < 8 else TIER2 if i < 16 else None
    if fill:
        for j in range(1, 18):
            ms.cell(row=rr, column=j).fill = fill
    if r["ease"] <= 1:
        ms.cell(row=rr, column=12).fill = WARN_FILL
ms.cell(row=HR, column=1).comment = Comment(
    "Rows ordered by default-weight score. Edit the yellow weights (row 2) to re-score; "
    "sort manually if you want a new order.", "Arbitrage Ledger")

# ---------------- category sheets (raw data) ----------------
def raw_sheet(title, header, data_rows):
    sh = wb.create_sheet(title[:31])
    for j, h in enumerate(header, 1):
        c = sh.cell(row=1, column=j, value=h)
        c.font = F(bold=True, color="FFFFFF", size=9)
        c.fill = HDR_FILL
        sh.column_dimensions[get_column_letter(j)].width = max(12, min(44, len(h) + 6))
    for i, dr in enumerate(data_rows, 2):
        for j, v in enumerate(dr, 1):
            c = sh.cell(row=i, column=j, value=v)
            c.font = F(size=9)
    sh.freeze_panes = "A2"

def jload(name):
    p = os.path.join(D, name)
    return json.load(open(p)) if os.path.exists(p) else None

nr = jload("negrisk_instant.json")
if nr:
    raw_sheet("Polymarket sweeps",
              ["Event", "Outcomes", "Sum YES bids (live)", "Edge $/set", "Capital $/set",
               "Return %", "Sets at top", "Profit $/cycle", "Status"],
              [[e["title"], e["n"],
                e.get("live", {}).get("sum_bid_live"), e.get("live", {}).get("edge_per_set"),
                e.get("live", {}).get("capital_per_set"), e.get("live", {}).get("ret_pct"),
                e.get("live", {}).get("sets_at_best_bid"), e.get("live", {}).get("profit_at_best_depth"),
                e.get("live", {}).get("status")] for e in nr["verified"]])
bo = jload("beyond_obvious.json")
if bo:
    raw_sheet("Basis + funding",
              ["Type", "Instrument", "Detail", "Value", "Unit"],
              [["delivery basis", b["contract"], f"{b['days']}d, spot {b['spot']} fut {b['future']}",
                b["apr_pct"], "% APR"] for b in bo.get("basis", [])[:15]] +
              [["funding spread", f["coin"], f"long {f['long_on']} short {f['short_on']}",
                f["net_daily_pct"], "% per day"] for f in bo.get("funding_spread", [])[:15]])
ns = jload("new_sectors.json")
if ns:
    raw_sheet("P2P corridors",
              ["Currency", "Official FX", "P2P buy USDT", "P2P sell USDT",
               "Buy premium %", "Sell premium %", "In-country roundtrip %", "Offers"],
              [[p["currency"], p["official_fx"], p["p2p_buy_usdt"], p["p2p_sell_usdt"],
                p["buy_premium_pct"], p["sell_premium_pct"],
                p["onramp_offramp_spread_pct"], p["offers"]] for p in ns.get("p2p_corridors", [])])
    raw_sheet("DeFi lending",
              ["Chain", "Asset", "Borrow on", "Borrow APY %", "Borrow avail $",
               "Lend on", "Supply APY %", "Supply TVL $", "Spread %-yr"],
              [[d["chain"], d["asset"], d["borrow_on"], d["borrow_apy_pct"], d["borrow_avail_usd"],
                d["lend_on"], d["supply_apy_pct"], d["supply_tvl_usd"], d["spread_pct_yr"]]
               for d in ns.get("defi_lending", [])[:30]])

out = os.path.join(D, "Arbitrage_Ledger.xlsx")
wb.save(out)
print("saved", out)
