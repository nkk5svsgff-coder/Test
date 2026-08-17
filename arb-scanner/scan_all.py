#!/usr/bin/env python3
"""Master aggregator: normalize every opportunity class from all scanner
outputs into one ranked dataset -> data/master_opportunities.json.

Each row: category, name, where, edge_value, edge_unit, cycle_time,
repeats_per_day, capacity_usd, verified, ease (1-5 from Greece/EU),
risk (1-5), risk_notes, how, usd_per_day_10k, measured_at.

Subscores (0-10) are precomputed here; the Excel ranks with a live
SUMPRODUCT over user-adjustable weights.
"""

import json
import math
import os
import time

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load(name):
    p = os.path.join(D, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        data = json.load(f)
    age_h = (time.time() - os.path.getmtime(p)) / 3600
    return data, age_h


def row(cat, name, where, edge, unit, cycle, repeats, cap, verified, ease, risk,
        risk_notes, how, usd_day_10k, measured):
    return {"category": cat, "name": name, "where": where,
            "edge_value": edge, "edge_unit": unit, "cycle_time": cycle,
            "repeats_per_day": repeats, "capacity_usd": cap,
            "verified": verified, "ease": ease, "risk": risk,
            "risk_notes": risk_notes, "how": how,
            "usd_per_day_10k": usd_day_10k, "measured_at": measured}


rows = []
now_iso = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())

# ---- neg-risk conversion sweeps ----
nr = load("negrisk_instant.json")
if nr:
    data, age = nr
    ts = data["ts"]
    live = [e for e in data["verified"]
            if e.get("live", {}).get("status") == "ok" and e["live"]["edge_per_set"] > 0.002]
    seen = set()
    for e in live[:6]:
        if e["title"] in seen:
            continue
        seen.add(e["title"])
        lv = e["live"]
        rows.append(row(
            "Prediction structural", f"Neg-risk sweep: {e['title'][:45]}",
            "Polymarket", lv["ret_pct"], "% per cycle (riskless)", "minutes",
            "5-20 (as books refill)", round(lv["capital_per_set"] * lv["sets_at_best_bid"]),
            "live CLOB, every outcome book", 4, 1,
            "Depth-capped; edge locked at fill; no-fee venue",
            f"Buy NO on all {e['n']} outcomes, convert set to USDC instantly via NegRiskAdapter, repeat",
            round(min(20, lv["profit_at_best_depth"] * 8), 1), ts))

# ---- SOL ladder logic violations ----
bo = load("beyond_obvious.json")
if bo:
    data, age = bo
    ts = data["ts"]
    for r in data.get("ladders", [])[:2]:
        rows.append(row(
            "Prediction structural", f"Ladder violation: {r['strong'][:40]}",
            "Polymarket", r["ret_pct"], "% locked at fill", "instant fill; pays at resolution",
            "when flagged (few/week)", 50, "live CLOB depth", 4, 1,
            "Riskless at fill; capital returns at event resolution; ~$50 size",
            "Buy YES weaker strike + NO stronger strike for < $1/set; min payout $1, $2 if between strikes",
            2, ts))
    # ---- PM vs Deribit gap ----
    g62 = [r for r in data.get("pm_vs_deribit", []) if r["strike"] == 62000]
    if g62:
        gap = max(abs(r["gap"]) for r in g62) * 100
        rows.append(row(
            "Cross-market relative value", "BTC digital: Polymarket vs Deribit options",
            "Polymarket + Deribit", round(gap, 1), "prob-points gap", "hours-days",
            "daily (new expiries)", 5000, "options marks vs CLOB", 2, 3,
            "Hedged not riskless: 9h resolution-time gap, different price feeds",
            "Buy cheap PM digital, hedge with Deribit call spread at same strike",
            10, data["ts"]))
    # ---- dated basis ----
    for r in data.get("basis", [])[:3]:
        if r["apr_pct"] <= 0:
            continue
        rows.append(row(
            "Locked carry", f"Delivery basis: {r['contract']}",
            "Gate futures", r["apr_pct"], "% APR locked to expiry", f"{r['days']}d to delivery",
            "weekly (new contracts)", 100000, "mark vs spot mid", 3, 2,
            "Margin on short leg; locked only if held to delivery",
            "Buy spot + short dated future; converge at delivery regardless of price",
            round(10000 * r["apr_pct"] / 100 / 365, 1), data["ts"]))
    # ---- funding spreads ----
    for r in data.get("funding_spread", [])[:3]:
        rows.append(row(
            "Delta-neutral carry", f"Double-perp funding: {r['coin']}",
            f"{r['long_on']} + {r['short_on']}", r["net_daily_pct"], "% per day while spread lasts",
            "continuous", "continuous (rate 8h/4h/1h)", 50000, "funding feeds both venues", 3, 3,
            "Rates converge in days; liquidation buffers both legs; 4 fees round trip",
            f"Long {r['coin']} perp on {r['long_on']}, short on {r['short_on']} - zero price exposure",
            round(5000 * r["net_daily_pct"] / 100, 1), data["ts"]))

# ---- spread capture MM (CEX) ----
sc = load("spread_capture.json")
if sc:
    data, age = sc
    cands = data.get("candidates", data) if isinstance(data, dict) else data
    best = [c for c in cands if isinstance(c, dict)][:3] if isinstance(cands, list) else []
    for c in best:
        rows.append(row(
            "Market-making", f"Spread capture: {c.get('symbol')} ({c.get('exchange')})",
            c.get("exchange", ""), c.get("roundtrip_capture_pct", 0), "% per round trip",
            "minutes per RT", "10-100 fills", 500, "live books + trade tape", 3, 4,
            "INVENTORY RISK: one-sided fills accumulate positions; microcaps gap hard; sim showed +/-$90 swings vs $8 capture",
            "Post maker bid+ask inside the spread (0% maker on MEXC); manage inventory",
            15, now_iso))

# ---- Polymarket in-play MM ----
pm = load("pm_mm_candidates.json")
if pm:
    rows.append(row(
        "Market-making", "In-play sports MM (nightly games)",
        "Polymarket", 1.5, "% of mid per round trip", "seconds-minutes per RT",
        "100s during games", 2000, "CLOB depth + trade tape", 3, 4,
        "Adverse selection on goals/rounds; must pull quotes near resolution; no fees",
        "Quote both sides of live game books (1-4c spreads, 1000s prints/hr); fresh books daily",
        25, now_iso))

# ---- P2P corridors ----
ns = load("new_sectors.json")
if ns:
    data, age = ns
    ts = data["ts"]
    p2p = {r["currency"]: r for r in data.get("p2p_corridors", [])}
    if "UAH" in p2p:
        rows.append(row(
            "P2P fiat corridor", "Ukraine in-country loop (PrivatBank both legs)",
            "OKX P2P", 2.8, "% per cycle", "5-15 min per leg", "20-40",
            20000, "offer-level check incl. depth+banks", 1, 3,
            "REQUIRES Ukrainian bank rails - not executable from Greece; counterparty/chargeback risk",
            "Buy USDT from merchant A, sell to merchant B, same bank transfers", 0, ts))
    for ccy, prem_note in (("VES", "Venezuela structural premium"), ("ARS", "Argentina premium")):
        if ccy in p2p and abs(p2p[ccy]["sell_premium_pct"]) > 3:
            r = p2p[ccy]
            rows.append(row(
                "P2P fiat corridor", f"{prem_note} ({ccy})", "OKX P2P vs official FX",
                r["sell_premium_pct"], "% premium per corridor pass", "hours",
                "daily", 10000, "P2P books vs FX fix", 1, 4,
                "Needs banking on both corridor ends; AML/licensing if done commercially",
                "Structural: USD in, sell USDT locally at premium", 0, ts))
    rows.append(row(
        "P2P fiat corridor", "EUR clean same-platform loop", "OKX P2P (Dukascopy legs)",
        0.34, "% per cycle", "10-30 min per leg", "5-15", 5000,
        "live books", 4, 3,
        "Thin EUR books; above-fair offers are fraud bait (mule risk) - trade only at fair prices",
        "Buy/sell USDT vs EUR on same payment platform at the clean spread", 5, ts))
    # ---- DeFi lending ----
    blue = [r for r in data.get("defi_lending", [])
            if r["borrow_on"] in ("compound-v3", "morpho-blue", "kamino-lend", "euler-v2", "aave-v3", "fluid-lending", "liquity-v1")
            and r["lend_on"] not in ("accountable",)][:3]
    for r in blue:
        rows.append(row(
            "DeFi rate arbitrage", f"Borrow-lend spread: {r['asset']} on {r['chain']}",
            f"{r['borrow_on']} -> {r['lend_on']}", r["spread_pct_yr"], "% per year on borrowed notional",
            "instant entry/exit", "continuous", r["borrow_avail_usd"],
            "DefiLlama live rates", 3, 3,
            "Protocol solvency + rate moves + liquidation; obscure lenders = risk premium",
            f"Borrow {r['asset']} at {r['borrow_apy_pct']}% on {r['borrow_on']}, lend at {r['supply_apy_pct']}% on {r['lend_on']}",
            round(10000 * 0.7 * r["spread_pct_yr"] / 100 / 365, 1), ts))
    # ---- skins ----
    if data.get("skins"):
        med = data.get("skins_median_discount_pct")
        rows.append(row(
            "Gaming items", f"CS2 skins spend-discount (median {med}% off Steam)",
            "Skinport -> Steam ecosystem", med or 22, "% discount on Steam spend", "instant",
            "unlimited for own spending", 1000, "full 21k-item catalog", 4, 3,
            "ONE-WAY: Steam wallet cannot cash out - only worth it for money you'd spend on Steam anyway",
            "Buy discounted items on Skinport instead of paying Steam prices", 0, ts))

# ---- EUR rate arbitrage (measured today) ----
rows.append(row(
    "Rate arbitrage", "Idle EUR: money-market ETF vs Greek deposit",
    "XEON/CSH2 via EU broker", 1.9, "% per year (2.19% ESTR - ~0.3% bank)", "one-time setup",
    "continuous", 10_000_000, "ECB ESTR fix 2.188% (fetched)", 5, 1,
    "Near-riskless (o/n rates); ETF spread ~2bp; ESTR moves with ECB policy",
    "Move idle EUR from Greek bank deposit to an overnight-rate MMF ETF", 0.5, now_iso))
rows.append(row(
    "Rate arbitrage", "EURC on-chain vs Greek deposit",
    "Aave v3 Ethereum", 2.6, "% per year net of bank rate", "instant",
    "continuous", 11_000_000, "DefiLlama: EURC 2.93% APY, $11M TVL", 3, 2,
    "Smart-contract + stablecoin issuer risk; beats ESTR slightly",
    "Hold EURC, supply on Aave", 0.7, now_iso))

# ---- Pendle fixed ----
rows.append(row(
    "Fixed-rate lock", "Pendle PT stable yields (best liquid: 14-18% APY)",
    "Pendle (Ethereum)", 16, "% APY fixed at purchase", "instant buy; hold to maturity",
    "monthly (new maturities)", 5_000_000, "Pendle API implied APY", 3, 3,
    "Underlying protocol/stablecoin solvency is the paid risk; yield locked only to maturity",
    "Buy discounted principal token, redeem at par at maturity", 4.4, now_iso))

# ---- monitors (near-zero now, fat in dislocations) ----
rows.append(row(
    "Dislocation monitor", "Stablecoin depeg / triangle / CEX-DEX watchlist",
    "11 CEX + Jupiter + books", 0, "% now; 1-30% in stress events", "seconds when open",
    "rare, event-driven", 100000, "6 scanners, order-book verified", 4, 2,
    "The USDC depeg (Mar 2023) paid 3-8% riskless for a weekend to whoever was ready; loops all negative at rest",
    "Run the scanner loop; act only when it flags a verified positive", 0, now_iso))

# ---- subscores ----
def clamp(x, lo, hi):
    return max(lo, min(hi, x))

for r in rows:
    unit = r["edge_unit"]
    e = r["edge_value"]
    if "per cycle" in unit or "round trip" in unit or "per day" in unit or "locked at fill" in unit:
        eff = e * (3 if "per day" in unit else 1)
        r["edge_score"] = clamp(round(2 + 2.2 * math.log10(max(eff, 0.01) * 10), 1), 0, 10)
    elif "APR" in unit or "year" in unit or "APY" in unit:
        r["edge_score"] = clamp(round(e / 5, 1), 0, 10)
    else:
        r["edge_score"] = clamp(round(e / 4, 1), 0, 10)
    rep = str(r["repeats_per_day"])
    r["repeat_score"] = 9 if "continuous" in rep else 8 if "100" in rep else 6 if any(c.isdigit() for c in rep) else 3
    r["capacity_score"] = clamp(round(1.5 * math.log10(max(r["capacity_usd"], 10)), 1), 0, 10)
    r["ease_score"] = r["ease"] * 2
    r["risk_score"] = r["risk"] * 2   # higher = worse; subtracted by weights

W = {"edge": 0.30, "repeat": 0.15, "capacity": 0.15, "ease": 0.25, "risk": 0.15}
for r in rows:
    r["score_default"] = round(
        W["edge"] * r["edge_score"] + W["repeat"] * r["repeat_score"]
        + W["capacity"] * r["capacity_score"] + W["ease"] * r["ease_score"]
        - W["risk"] * r["risk_score"], 2)
rows.sort(key=lambda r: -r["score_default"])

out = {"generated": now_iso, "weights_default": W, "rows": rows}
with open(os.path.join(D, "master_opportunities.json"), "w") as f:
    json.dump(out, f, indent=1)
print(f"{len(rows)} master rows written")
for i, r in enumerate(rows[:10], 1):
    print(f"  {i:2d}. [{r['score_default']:5.2f}] {r['category']:26s} {r['name'][:52]}")
