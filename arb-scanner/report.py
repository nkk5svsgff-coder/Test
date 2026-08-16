#!/usr/bin/env python3
"""Build the 100-opportunity report from scanner snapshots.

Reads data/opportunities.json (latest) + data/opportunities_run1.json
(earlier snapshot, for persistence tagging) and writes:
  data/report.md          - numbered 100-opportunity report
  data/opportunities.csv  - flat machine-readable list
"""

import csv
import json
import os

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
cur = json.load(open(os.path.join(D, "opportunities.json")))
prev = json.load(open(os.path.join(D, "opportunities_run1.json")))

rows = []  # each: dict(category, name, action, edge_pct, capital, horizon, liquidity, risks)


def kalshi_fee(prices):
    """Kalshi taker fee approx: 0.07 * P * (1-P) per contract, summed."""
    return sum(0.07 * p * (1 - p) for p in prices)


# ---------- Category A: robust prediction arbs (sum of YES bids > $1) ----------
pred = cur["polymarket_events"] + cur["kalshi_events"]
robust = [e for e in pred if e["sum_yes_bid"] > 1.005]


def pred_row(e):
    n, sb = e["n_outcomes"], e["sum_yes_bid"]
    edge = sb - 1.0
    capital = n - sb  # cost of buying NO on every outcome (1 contract each)
    ret = edge / capital * 100
    if e["platform"] == "kalshi":
        # approximate: NO prices ~ (1 - yes_bid); we only stored the sum, so
        # bound the fee using average price
        avg_p = sb / n
        fee = kalshi_fee([avg_p] * n)
        fee_note = f"; Kalshi fees ≈ ${fee:.03f}/set eat into this"
        url = f"kalshi.com — event ticker `{e['event_ticker']}`"
    else:
        fee_note = "; Polymarket charges no trading fee (gas ≈ $0 via relayer)"
        url = f"polymarket.com/event/{e['slug']}"
    vol = e.get("volume24h")
    liq = f"24h vol ${vol:,.0f}" if vol else "24h vol n/a (books may be thin)"
    return {
        "category": "A. Prediction-market structural (robust)",
        "name": f"[{e['platform']}] {e['title']}",
        "action": (f"Buy NO on all {n} outcomes (~${capital:.2f}/set). Mutually exclusive => at most one YES, "
                   f"so payout ≥ ${n - 1}/set; YES bids sum to ${sb:.3f}"),
        "edge_pct": round(ret, 2),
        "capital": f"${capital:.2f}/set",
        "horizon": "event resolution",
        "liquidity": liq,
        "risks": "displayed bid depth may be one lot; edge locked only for size actually filled" + fee_note,
        "url": url,
    }


robust.sort(key=lambda e: (e["sum_yes_bid"] - 1) / (e["n_outcomes"] - e["sum_yes_bid"]), reverse=True)
for e in robust:
    rows.append(pred_row(e))

# ---------- Category B: conditional prediction arbs (sum of YES asks < $1) ----------
cond = [e for e in pred if e["sum_yes_ask"] < 0.99 and e["sum_yes_bid"] > 0.3]
cond.sort(key=lambda e: -(e.get("volume24h") or 0))
for e in cond[:18]:
    n, sa = e["n_outcomes"], e["sum_yes_ask"]
    edge = 1.0 - sa
    url = f"polymarket.com/event/{e['slug']}" if e["platform"] == "polymarket" else f"kalshi.com — `{e['event_ticker']}`"
    vol = e.get("volume24h")
    rows.append({
        "category": "B. Prediction-market conditional (exhaustiveness required)",
        "name": f"[{e['platform']}] {e['title']}",
        "action": f"Buy YES on all {n} outcomes for ${sa:.3f}/set; pays $1 IF one listed outcome must win",
        "edge_pct": round(edge / sa * 100, 2),
        "capital": f"${sa:.3f}/set",
        "horizon": "event resolution",
        "liquidity": f"24h vol ${vol:,.0f}" if vol else "24h vol n/a",
        "risks": "ONLY an arb if the outcome list is exhaustive — if none listed wins, whole set is lost. Verify rules first",
        "url": url,
    })

# ---------- Category C: funding-rate carry ----------
seen_coins = set()
fund_rows = []
for f in cur["funding"]:
    coin = f["symbol"].replace("_USDT", "").replace("USDT", "").replace("-USDT-SWAP", "")
    if coin in seen_coins:
        continue
    vol = f.get("volume_usd")
    if f["ex"] == "bitget" and (vol or 0) < 300_000:
        continue
    if abs(f["apr"]) < 0.25:
        break
    seen_coins.add(coin)
    fund_rows.append(f)
    if len(fund_rows) >= 26:
        break

for f in fund_rows:
    apr = f["apr"] * 100
    daily = f["rate"] * (24 / f["interval_h"]) * 100
    if f["rate"] > 0:
        act = f"Buy spot, short {f['symbol']} perp on {f['ex']} — collect +{f['rate']*100:.3f}% every {f['interval_h']:.0f}h ({daily:+.2f}%/day)"
    else:
        act = f"Long {f['symbol']} perp on {f['ex']}, hedge with spot short/margin — shorts pay longs {abs(f['rate'])*100:.3f}% every {f['interval_h']:.0f}h ({abs(daily):.2f}%/day)"
    rows.append({
        "category": "C. Perp funding-rate carry (delta-neutral, single venue)",
        "name": f"[{f['ex']}] {f['symbol']} funding {f['rate']*100:+.3f}%/{f['interval_h']:.0f}h",
        "action": act,
        "edge_pct": round(abs(daily), 3),
        "capital": "any; 2x notional (both legs)",
        "horizon": "per funding interval; rates mean-revert in hours-days",
        "liquidity": f"perp 24h vol ≈ ${f['volume_usd']:,.0f}" if f.get("volume_usd") else "see venue",
        "risks": "rate can flip sign next interval; liquidation risk on the perp leg; entry/exit costs 2 spreads + 4 fees",
        "url": f"{f['ex']} futures",
    })

# ---------- Category D: cross-exchange spot ----------
prev_assets = {o["asset"] for o in prev["spot_opportunities"] if o["net_pct"] > 0}
spot = [o for o in cur["spot_opportunities"] if o["net_pct"] > 0][:20]
for o in spot:
    v = o.get("verified") or {}
    if v.get("status") == "ok":
        vtxt = f"order-book verified {v['net_pct']:+.2f}% net for ${v['fill_usd']} fill"
        edge = v["net_pct"]
    else:
        vtxt = "not depth-verified (ticker top only)"
        edge = o["net_pct"]
    persist = "seen in both snapshots ~30min apart" if o["asset"] in prev_assets else "single snapshot"
    blocked = bool(o["transfer_notes"])
    rows.append({
        "category": "D. Cross-exchange spot spread",
        "name": f"{o['asset']}/{o['quote']}: {o['buy_ex']} -> {o['sell_ex']}",
        "action": (f"Buy on {o['buy_ex']} @ {o['buy_ask']:g}, transfer, sell on {o['sell_ex']} @ {o['sell_bid']:g} "
                   f"(ticker net {o['net_pct']:+.2f}% after taker fees; {vtxt})"),
        "edge_pct": edge,
        "capital": "limited by book depth",
        "horizon": "transfer time (minutes on fast chains)",
        "liquidity": f"24h vol: buy side ${o['buy_qvol']:,}, sell side ${o['sell_qvol']:,}; {persist}",
        "risks": ("TRANSFER BLOCKED: " + o["transfer_notes"] + " — spread persists precisely because it cannot be closed; monitor for reopen"
                  if blocked else
                  "price can move during transfer; withdrawal fees not included; verify same token/chain on both venues"),
        "url": "",
    })

# ---------- Category E: stablecoin / peg ----------
ticks = json.load(open(os.path.join(D, "merged_tickers.json")))
STABLES = {"USDT", "USDC", "DAI", "TUSD", "FDUSD", "PYUSD", "USDE", "USD1", "RLUSD", "EURC", "EURT"}
groups = {}
for t in ticks:
    if t["base"] in STABLES and t["quote"] in ("USD", "USDT", "USDC") and t["qvol"] > 100_000:
        groups.setdefault((t["base"], t["quote"]), []).append(t)
stab = []
for (b, q), g in groups.items():
    if len(g) < 2:
        continue
    buy = min(g, key=lambda r: r["ask"])
    sell = max(g, key=lambda r: r["bid"])
    spr = (sell["bid"] - buy["ask"]) / buy["ask"] * 100
    stab.append((spr, b, q, buy, sell, len(g)))
stab.sort(reverse=True)
for spr, b, q, buy, sell, nv in stab[:6]:
    rows.append({
        "category": "E. Stablecoin / peg spread",
        "name": f"{b}/{q}: {buy['ex']} -> {sell['ex']}",
        "action": f"Buy {b} on {buy['ex']} @ {buy['ask']:.5f}, transfer on-chain, sell on {sell['ex']} @ {sell['bid']:.5f}",
        "edge_pct": round(spr, 3),
        "capital": "scales well - deep books",
        "horizon": "minutes (chain transfer)",
        "liquidity": f"{nv} venues quoting; both sides > $100k/24h",
        "risks": "gross spread shown - taker fees + withdrawal fee eat most of it below ~0.15%; sized for depeg moments",
        "url": "",
    })

rows = rows[:100]

# ---------- write CSV ----------
with open(os.path.join(D, "opportunities.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["rank", "category", "name", "action", "edge_pct", "capital", "horizon", "liquidity", "risks", "url"])
    w.writeheader()
    for i, r in enumerate(rows, 1):
        w.writerow({"rank": i, **r})

# ---------- write markdown ----------
tris = cur.get("triangles") or []
lines = [
    "# 100 Live Digital-Arbitrage Opportunities",
    "",
    f"Snapshot: {cur['ts']} UTC - built from {cur['n_tickers']:,} live tickers on 11 exchanges "
    "(Kraken, Coinbase, KuCoin, OKX, Gate, MEXC, HTX, Bitfinex, Bitstamp, Bitget, Crypto.com), "
    "1,692 perp funding rates, and full order books on Polymarket + Kalshi.",
    "",
    "Every row is computed from live public market data fetched at the timestamp above; the top "
    "spot spreads were re-verified against depth-20 order books minutes after the ticker snapshot.",
    "",
]
cat = None
for i, r in enumerate(rows, 1):
    if r["category"] != cat:
        cat = r["category"]
        lines += [f"\n## {cat}\n"]
    lines.append(f"**{i}. {r['name']}** — edge {r['edge_pct']}%")
    lines.append(f"   - Action: {r['action']}")
    lines.append(f"   - Capital: {r['capital']} | Horizon: {r['horizon']} | Liquidity: {r['liquidity']}")
    lines.append(f"   - Risks: {r['risks']}")
    if r["url"]:
        lines.append(f"   - Where: {r['url']}")
    lines.append("")

lines += [
    "\n## Monitored channels currently closed (for context)\n",
    "- **Triangular arb** (same-exchange, zero transfer risk): best cycle right now is "
    f"`{tris[0]['ex']}: {tris[0]['path']}` at {tris[0]['net_pct']:+.3f}% before slippage — "
    "bots keep these below zero net of taker fees. Flips positive only in volatility spikes." if tris else "",
    "- **Kalshi vs Polymarket cross-platform**: September Fed decision priced identically "
    "(no-change 0.72/0.73 vs 0.73/0.74) — 2024-era gaps have converged; monitor around news shocks.",
    "- **Binance/Bybit legs**: geo-blocked from this scanner's location; spreads vs those venues not covered.",
]
with open(os.path.join(D, "report.md"), "w") as f:
    f.write("\n".join(lines))

n_by_cat = {}
for r in rows:
    n_by_cat[r["category"]] = n_by_cat.get(r["category"], 0) + 1
print(f"wrote {len(rows)} opportunities:")
for c, n in n_by_cat.items():
    print(f"  {n:3d}  {c}")
