#!/usr/bin/env python3
"""Spread-capture market-making candidate scanner.

Finds USDT spot pairs on low/zero-maker-fee venues (MEXC, Gate, KuCoin,
Bitget) where the bid-ask spread is wide (0.3%..3%) AND trades actually
print frequently, so posting maker orders on both sides can capture the
spread repeatedly.

Run: cd /home/user/Test/arb-scanner && python3 scan5.py
Output: data/spread_capture.json + printed table.
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from scan import (S, get_json, fetch_mexc, fetch_gate, fetch_kucoin,
                  fetch_bitget, fetch_book, OUT_DIR)

MAKER_FEE = {          # fraction per side
    "mexc": 0.000,     # MEXC spot maker = 0.000%
    "gate": 0.001,     # classic-account 0.1% (often promo 0%)
    "kucoin": 0.001,
    "bitget": 0.001,
}

MIN_SPREAD = 0.003
MAX_SPREAD = 0.03
MIN_QVOL = 150_000
TARGET_KEPT = 25        # keep digging down the ranked list until this many
MAX_CHECKED = 150       # ... or this many trade-history lookups
BATCH = 25
MIN_TRADES_PER_HOUR = 10


# ---------------- recent-trade fetchers ----------------
# Each returns a list of (ts_ms, side) tuples; side in {"buy","sell",None}
# side = aggressor (taker) side where the venue reports it.

def trades_mexc(sym):
    data = get_json(f"https://api.mexc.com/api/v3/trades?symbol={sym}&limit=500")
    out = []
    for t in data:
        # isBuyerMaker True => taker sold (aggressive sell)
        ibm = t.get("isBuyerMaker")
        side = None if ibm is None else ("sell" if ibm else "buy")
        out.append((float(t["time"]), side))
    return out


def trades_gate(sym):
    data = get_json(f"https://api.gateio.ws/api/v4/spot/trades?currency_pair={sym}&limit=100")
    return [(float(t["create_time_ms"]), t.get("side")) for t in data]


def trades_kucoin(sym):
    data = get_json(f"https://api.kucoin.com/api/v1/market/histories?symbol={sym}")["data"]
    return [(float(t["time"]) / 1e6, t.get("side")) for t in data]  # ns -> ms


def trades_bitget(sym):
    data = get_json(f"https://api.bitget.com/api/v2/spot/market/fills?symbol={sym}&limit=100")["data"]
    return [(float(t["ts"]), t.get("side")) for t in data]


TRADE_FETCHERS = {"mexc": trades_mexc, "gate": trades_gate,
                  "kucoin": trades_kucoin, "bitget": trades_bitget}


def trade_stats(ex, sym):
    """Fetch recent prints and compute frequency + flow stats."""
    trades = TRADE_FETCHERS[ex](sym)
    if not trades:
        return {"n_trades": 0, "trades_per_hour": 0.0}
    ts = [t[0] for t in trades]
    now_ms = time.time() * 1000
    span_h = (max(ts) - min(ts)) / 3_600_000
    # A single print (or all prints in the same ms) gives span 0; floor the
    # span at 1 minute so we never divide by ~0 and inflate frequency.
    span_h = max(span_h, 1 / 60)
    sides = [t[1] for t in trades if t[1] in ("buy", "sell")]
    buys = sum(1 for s in sides if s == "buy")
    return {
        "n_trades": len(trades),
        "span_hours": round(span_h, 3),
        "trades_per_hour": len(trades) / span_h,
        "last_trade_age_min": round((now_ms - max(ts)) / 60_000, 1),
        "buy_fraction": round(buys / len(sides), 3) if sides else None,
    }


def bitget_tokenized_stock_symbols():
    """Bitget lists tokenized equities (baseCoin 'rGLD', 'rTSLA', ...).
    They only print during US stock-market hours, and the ticker feed
    reports wildly implausible 24h quote volumes for them, so they flood
    the (spread * volume) ranking with dead books. Identify them via the
    lowercase-'r' baseCoin prefix in the symbols metadata."""
    try:
        syms = get_json("https://api.bitget.com/api/v2/spot/public/symbols")["data"]
        return {s["symbol"] for s in syms
                if len(s.get("baseCoin", "")) > 1
                and s["baseCoin"][0] == "r" and s["baseCoin"][1:].isupper()}
    except Exception as e:
        print(f"[warn] bitget symbols metadata failed ({e}); relying on "
              f"trade-frequency filter only", flush=True)
        return set()


def main():
    started = time.time()
    fetchers = {"mexc": fetch_mexc, "gate": fetch_gate,
                "kucoin": fetch_kucoin, "bitget": fetch_bitget}
    tickers = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(fn): name for name, fn in fetchers.items()}
        for f in as_completed(futs):
            name = futs[f]
            try:
                rows = f.result()
                print(f"[tickers] {name}: {len(rows)} pairs", flush=True)
                tickers.extend(rows)
            except Exception as e:
                print(f"[tickers] {name}: FAILED {type(e).__name__}: {e}", flush=True)

    tokenized = bitget_tokenized_stock_symbols()
    print(f"[filter] excluding {len(tokenized)} bitget tokenized-stock pairs",
          flush=True)

    # ---- filter: USDT quote, spread in band, enough 24h quote volume ----
    cands = []
    for t in tickers:
        if t["quote"] != "USDT":
            continue
        if t["ex"] == "bitget" and t["sym"] in tokenized:
            continue
        spread = (t["ask"] - t["bid"]) / t["bid"]
        if not (MIN_SPREAD <= spread <= MAX_SPREAD):
            continue
        if t["qvol"] < MIN_QVOL:
            continue
        cands.append({
            "exchange": t["ex"], "symbol": t["sym"], "base": t["base"],
            "bid": t["bid"], "ask": t["ask"],
            "spread_pct": round(spread * 100, 4),
            "qvol_24h_usd": round(t["qvol"]),
            "score": spread * t["qvol"],
        })
    cands.sort(key=lambda c: -c["score"])
    print(f"[filter] {len(cands)} pairs in spread band with qvol>=${MIN_QVOL:,}",
          flush=True)

    # ---- measure real trade frequency, walking down the ranked list ----
    # The very top of (spread*volume) is dominated by instruments whose
    # printed 24h volume is not matched by any actual prints (e.g. Bitget
    # tokenized-stock R* pairs on a weekend: giant reported volume, dead
    # book). We therefore check in ranked batches and keep digging until
    # TARGET_KEPT live candidates are found or MAX_CHECKED are examined.
    def enrich(c):
        try:
            c.update(trade_stats(c["exchange"], c["symbol"]))
        except Exception as e:
            c["trade_error"] = f"{type(e).__name__}: {e}"
            c["trades_per_hour"] = 0.0
        return c

    top, idx = [], 0
    while idx < min(len(cands), MAX_CHECKED):
        batch = cands[idx:idx + BATCH]
        idx += len(batch)
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(enrich, batch))
        top.extend(batch)
        n_live = sum(1 for c in top
                     if c.get("trades_per_hour", 0) >= MIN_TRADES_PER_HOUR)
        print(f"[trades] checked {idx}, live so far: {n_live}", flush=True)
        if n_live >= TARGET_KEPT:
            break

    # ---- economics ----
    for c in top:
        fee = MAKER_FEE[c["exchange"]]
        c["maker_fee_pct"] = fee * 100
        c["roundtrip_capture_pct"] = round(c["spread_pct"] - 2 * fee * 100, 4)
        tph = c.get("trades_per_hour", 0.0)
        c["trades_per_hour"] = round(tph, 1)
        # conservative: participate in ~a quarter of prints, and a round
        # trip needs both a buy fill and a sell fill
        c["est_roundtrips_per_day"] = round(min(tph, 20) * 24 / 4, 1)
        c["est_daily_capture_bps_per_unit"] = round(
            c["est_roundtrips_per_day"] * c["roundtrip_capture_pct"] * 100, 0)

    kept = [c for c in top if c.get("trades_per_hour", 0) >= MIN_TRADES_PER_HOUR
            and "trade_error" not in c]
    dropped = [c for c in top if c not in kept]
    kept.sort(key=lambda c: -(c["roundtrip_capture_pct"] * c["est_roundtrips_per_day"]))

    # ---- live order-book sanity check on kept candidates ----
    # Ticker spreads can be stale; also measure resting depth within 1% of
    # best on each side so a "huge spread but dead book" is visible.
    def check_book(c):
        try:
            book = fetch_book(c["exchange"], c["symbol"])
            bb, ba = book["bids"][0][0], book["asks"][0][0]
            c["live_spread_pct"] = round((ba - bb) / bb * 100, 4)
            c["bid_depth_1pct_usd"] = round(sum(
                p * q for p, q in book["bids"] if p >= bb * 0.99))
            c["ask_depth_1pct_usd"] = round(sum(
                p * q for p, q in book["asks"] if p <= ba * 1.01))
        except Exception as e:
            c["book_error"] = f"{type(e).__name__}"

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(check_book, kept))

    out = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "params": {"min_spread": MIN_SPREAD, "max_spread": MAX_SPREAD,
                   "min_qvol_usd": MIN_QVOL, "min_trades_per_hour": MIN_TRADES_PER_HOUR,
                   "maker_fee": MAKER_FEE},
        "candidates": kept,
        "dropped_low_activity": dropped,
    }
    path = os.path.join(OUT_DIR, "spread_capture.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=1)

    print(f"\nDone in {time.time()-started:.0f}s. {len(kept)} kept, "
          f"{len(dropped)} dropped (<{MIN_TRADES_PER_HOUR} trades/h or error). -> {path}\n")
    hdr = (f"{'ex':7s} {'symbol':16s} {'spread%':>8s} {'live%':>7s} {'qvol24h':>12s} "
           f"{'tr/h':>7s} {'lastTr':>7s} {'buy%':>5s} {'capture%':>9s} {'rt/day':>7s} "
           f"{'depth b/a $':>15s}")
    print(hdr)
    print("-" * len(hdr))
    for c in kept:
        bf = c.get("buy_fraction")
        live = c.get("live_spread_pct")
        depth = (f"{c['bid_depth_1pct_usd']:,}/{c['ask_depth_1pct_usd']:,}"
                 if "bid_depth_1pct_usd" in c else c.get("book_error", "?"))
        print(f"{c['exchange']:7s} {c['symbol']:16s} {c['spread_pct']:8.3f} "
              f"{live if live is not None else float('nan'):7.3f} "
              f"{c['qvol_24h_usd']:12,d} {c['trades_per_hour']:7.1f} "
              f"{str(c.get('last_trade_age_min','?'))+'m':>7s} "
              f"{'' if bf is None else format(bf*100,'.0f'):>5s} "
              f"{c['roundtrip_capture_pct']:9.3f} {c['est_roundtrips_per_day']:7.1f} "
              f"{depth:>15s}")
    if dropped:
        print("\nDropped (low prints / errors):")
        for c in dropped:
            print(f"  {c['exchange']:7s} {c['symbol']:16s} spread {c['spread_pct']:.3f}% "
                  f"qvol ${c['qvol_24h_usd']:,} tr/h {c.get('trades_per_hour',0):.1f} "
                  f"{c.get('trade_error','')}")


if __name__ == "__main__":
    main()
