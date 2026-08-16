#!/usr/bin/env python3
"""Live digital-arbitrage scanner.

Pulls public best-bid/ask + 24h volume from 11 crypto exchanges, funding
rates from 3 derivatives venues, and order books from Polymarket/Kalshi,
then computes executable cross-venue spreads net of taker fees.

Only public endpoints, no API keys. Run: python3 scan.py
Outputs: data/merged_tickers.json, data/opportunities.json, data/opportunities.csv
"""

import json
import os
import re
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT_DIR, exist_ok=True)

S = requests.Session()
S.headers.update({"User-Agent": "arb-research/1.0"})
TIMEOUT = 25

# Base-tier spot taker fees (fraction). Approximations of published
# lowest-tier schedules as of mid-2026; most venues discount with volume
# or native-token fee payment.
TAKER_FEE = {
    "kraken": 0.0040,
    "coinbase": 0.0060,
    "kucoin": 0.0010,
    "okx": 0.0010,
    "gate": 0.0020,
    "mexc": 0.0005,
    "htx": 0.0020,
    "bitfinex": 0.0020,
    "bitstamp": 0.0040,
    "bitget": 0.0010,
    "cryptocom": 0.0050,
}

USD_QUOTES = ("USDT", "USDC", "USD")   # cross-exchange comparison groups
QUOTES = ("USDT", "USDC", "USD", "BTC", "ETH")  # fetched (BTC/ETH for triangles)
LEVERAGED_RE = re.compile(r".*(3L|3S|5L|5S|4L|4S|2L|2S|UP|DOWN|BULL|BEAR)$")


def get_json(url, **kw):
    r = S.get(url, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r.json()


def split_concat(symbol, quotes=("USDT", "USDC", "USD", "FDUSD", "TUSD", "DAI", "BTC", "ETH", "EUR")):
    for q in quotes:
        if symbol.endswith(q) and len(symbol) > len(q):
            return symbol[: -len(q)], q
    return None, None


def row(ex, base, quote, bid, ask, last, qvol, sym=None):
    try:
        bid, ask = float(bid), float(ask)
        last = float(last) if last else (bid + ask) / 2
        qvol = float(qvol) if qvol else 0.0
    except (TypeError, ValueError):
        return None
    if bid <= 0 or ask <= 0 or ask < bid * 0.5:
        return None
    if LEVERAGED_RE.match(base):
        return None
    return {"ex": ex, "base": base, "quote": quote, "bid": bid, "ask": ask,
            "last": last, "qvol": qvol, "sym": sym or f"{base}{quote}"}


# ---------------- spot fetchers ----------------

def fetch_kucoin():
    data = get_json("https://api.kucoin.com/api/v1/market/allTickers")["data"]["ticker"]
    out = []
    for t in data:
        if "-" not in t["symbol"]:
            continue
        base, quote = t["symbol"].split("-", 1)
        if quote not in QUOTES:
            continue
        r = row("kucoin", base, quote, t.get("buy"), t.get("sell"), t.get("last"), t.get("volValue"), t["symbol"])
        if r:
            out.append(r)
    return out


def fetch_okx():
    data = get_json("https://www.okx.com/api/v5/market/tickers?instType=SPOT")["data"]
    out = []
    for t in data:
        parts = t["instId"].split("-")
        if len(parts) != 2 or parts[1] not in QUOTES:
            continue
        r = row("okx", parts[0], parts[1], t.get("bidPx"), t.get("askPx"), t.get("last"), t.get("volCcy24h"), t["instId"])
        if r:
            out.append(r)
    return out


def fetch_gate():
    data = get_json("https://api.gateio.ws/api/v4/spot/tickers")
    out = []
    for t in data:
        parts = t["currency_pair"].split("_")
        if len(parts) != 2 or parts[1] not in QUOTES:
            continue
        r = row("gate", parts[0], parts[1], t.get("highest_bid"), t.get("lowest_ask"), t.get("last"), t.get("quote_volume"), t["currency_pair"])
        if r:
            out.append(r)
    return out


def fetch_mexc():
    book = get_json("https://api.mexc.com/api/v3/ticker/bookTicker")
    day = {t["symbol"]: t for t in get_json("https://api.mexc.com/api/v3/ticker/24hr")}
    out = []
    for t in book:
        base, quote = split_concat(t["symbol"])
        if not base or quote not in QUOTES:
            continue
        d = day.get(t["symbol"], {})
        r = row("mexc", base, quote, t.get("bidPrice"), t.get("askPrice"), d.get("lastPrice"), d.get("quoteVolume"), t["symbol"])
        if r:
            out.append(r)
    return out


def fetch_htx():
    data = get_json("https://api.huobi.pro/market/tickers")["data"]
    out = []
    for t in data:
        base, quote = split_concat(t["symbol"].upper())
        if not base or quote not in QUOTES:
            continue
        r = row("htx", base, quote, t.get("bid"), t.get("ask"), t.get("close"), t.get("vol"), t["symbol"])
        if r:
            out.append(r)
    return out


def fetch_bitfinex():
    data = get_json("https://api-pub.bitfinex.com/v2/tickers?symbols=ALL")
    out = []
    for t in data:
        sym = t[0]
        if not sym.startswith("t"):
            continue
        body = sym[1:]
        if ":" in body:
            base, quote = body.split(":", 1)
        elif len(body) == 6:
            base, quote = body[:3], body[3:]
        else:
            continue
        if quote == "UST":
            quote = "USDT"
        if base == "UST":
            base = "USDT"
        if quote not in QUOTES:
            continue
        bid, ask, last, vol = t[1], t[3], t[7], t[8]
        r = row("bitfinex", base, quote, bid, ask, last, (vol or 0) * (last or 0), sym)
        if r:
            out.append(r)
    return out


def fetch_bitstamp():
    data = get_json("https://www.bitstamp.net/api/v2/ticker/")
    out = []
    for t in data:
        base, quote = t["pair"].split("/")
        if quote not in QUOTES:
            continue
        last = float(t.get("last") or 0)
        r = row("bitstamp", base, quote, t.get("bid"), t.get("ask"), last, float(t.get("volume") or 0) * last, t["pair"].replace("/", "").lower())
        if r:
            out.append(r)
    return out


def fetch_bitget():
    data = get_json("https://api.bitget.com/api/v2/spot/market/tickers")["data"]
    out = []
    for t in data:
        base, quote = split_concat(t["symbol"])
        if not base or quote not in QUOTES:
            continue
        r = row("bitget", base, quote, t.get("bidPr"), t.get("askPr"), t.get("lastPr"), t.get("usdtVolume"), t["symbol"])
        if r:
            out.append(r)
    return out


def fetch_cryptocom():
    data = get_json("https://api.crypto.com/exchange/v1/public/get-tickers")["result"]["data"]
    out = []
    for t in data:
        inst = t["i"]
        if "-" in inst:  # perps/options like BTCUSD-PERP
            continue
        parts = inst.split("_")
        if len(parts) != 2 or parts[1] not in QUOTES:
            continue
        r = row("cryptocom", parts[0], parts[1], t.get("b"), t.get("k"), t.get("a"), t.get("vv"), inst)
        if r:
            out.append(r)
    return out


KRAKEN_ALIAS = {"XBT": "BTC", "XDG": "DOGE"}


def fetch_kraken():
    pairs = get_json("https://api.kraken.com/0/public/AssetPairs")["result"]
    wsname = {k: v.get("wsname") for k, v in pairs.items() if v.get("wsname")}
    tick = get_json("https://api.kraken.com/0/public/Ticker")["result"]
    out = []
    for k, t in tick.items():
        ws = wsname.get(k)
        if not ws:
            continue
        base, quote = ws.split("/")
        base = KRAKEN_ALIAS.get(base, base)
        quote = KRAKEN_ALIAS.get(quote, quote)
        if quote not in QUOTES:
            continue
        last = float(t["c"][0])
        r = row("kraken", base, quote, t["b"][0], t["a"][0], last, float(t["v"][1]) * last, k)
        if r:
            out.append(r)
    return out


def fetch_coinbase(symbol_whitelist):
    """Per-product ticker; restricted to symbols seen elsewhere to stay
    within public rate limits."""
    products = get_json("https://api.exchange.coinbase.com/products")
    wanted = [
        p["id"] for p in products
        if p.get("quote_currency") in ("USD", "USDT", "USDC")
        and p.get("base_currency") in symbol_whitelist
        and not p.get("trading_disabled")
        and p.get("status") == "online"
    ]
    out = []

    def one(pid):
        try:
            t = get_json(f"https://api.exchange.coinbase.com/products/{pid}/ticker")
            base, quote = pid.split("-")
            last = float(t.get("price") or 0)
            return row("coinbase", base, quote, t.get("bid"), t.get("ask"), last,
                       float(t.get("volume") or 0) * last, pid)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = [pool.submit(one, pid) for pid in wanted]
        for f in as_completed(futs):
            r = f.result()
            if r:
                out.append(r)
    return out


# ---------------- transfer-status (public where available) ----------------

def fetch_gate_currency_status():
    try:
        data = get_json("https://api.gateio.ws/api/v4/spot/currencies")
    except Exception:
        return {}
    status = {}
    for c in data:
        chains = c.get("chains") or []
        dep_ok = any(not ch.get("deposit_disabled", True) for ch in chains) if chains else not c.get("deposit_disabled", False)
        wd_ok = any(not ch.get("withdraw_disabled", True) for ch in chains) if chains else not c.get("withdraw_disabled", False)
        status[c["currency"]] = {"deposit": dep_ok, "withdraw": wd_ok}
    return status


def fetch_kucoin_currency_status():
    try:
        data = get_json("https://api.kucoin.com/api/v3/currencies")["data"]
    except Exception:
        return {}
    status = {}
    for c in data:
        chains = c.get("chains") or []
        dep_ok = any(ch.get("isDepositEnabled") for ch in chains)
        wd_ok = any(ch.get("isWithdrawEnabled") for ch in chains)
        status[c["currency"]] = {"deposit": dep_ok, "withdraw": wd_ok}
    return status


def fetch_htx_currency_status():
    try:
        data = get_json("https://api.huobi.pro/v2/reference/currencies")["data"]
    except Exception:
        return {}
    status = {}
    for c in data:
        chains = c.get("chains") or []
        dep_ok = any(ch.get("depositStatus") == "allowed" for ch in chains)
        wd_ok = any(ch.get("withdrawStatus") == "allowed" for ch in chains)
        status[c["currency"].upper()] = {"deposit": dep_ok, "withdraw": wd_ok}
    return status


def fetch_bitget_currency_status():
    try:
        data = get_json("https://api.bitget.com/api/v2/spot/public/coins")["data"]
    except Exception:
        return {}
    status = {}
    for c in data:
        chains = c.get("chains") or []
        dep_ok = any(ch.get("rechargeable") == "true" for ch in chains)
        wd_ok = any(ch.get("withdrawable") == "true" for ch in chains)
        status[c["coin"]] = {"deposit": dep_ok, "withdraw": wd_ok}
    return status


# ---------------- funding rates ----------------

def fetch_funding():
    rows = []
    try:
        for c in get_json("https://api.gateio.ws/api/v4/futures/usdt/contracts"):
            fr = float(c.get("funding_rate") or 0)
            interval_h = (c.get("funding_interval") or 28800) / 3600
            rows.append({
                "ex": "gate", "symbol": c["name"], "rate": fr, "interval_h": interval_h,
                "apr": fr * (24 / interval_h) * 365,
                "volume_usd": float(c.get("trade_size") or 0) * float(c.get("quanto_multiplier") or 1) * float(c.get("last_price") or 0),
            })
    except Exception:
        traceback.print_exc()
    try:
        for t in get_json("https://api.bitget.com/api/v2/mix/market/tickers?productType=USDT-FUTURES")["data"]:
            fr = float(t.get("fundingRate") or 0)
            rows.append({
                "ex": "bitget", "symbol": t["symbol"], "rate": fr, "interval_h": 8,
                "apr": fr * 3 * 365, "volume_usd": float(t.get("usdtVolume") or 0),
            })
    except Exception:
        traceback.print_exc()
    # OKX: per-instrument, majors only
    okx_majors = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "LINK", "AVAX", "LTC", "BCH",
                  "TON", "SUI", "APT", "ARB", "OP", "NEAR", "PEPE", "WIF", "ENA", "TIA"]
    def okx_one(coin):
        try:
            d = get_json(f"https://www.okx.com/api/v5/public/funding-rate?instId={coin}-USDT-SWAP")["data"]
            if d:
                fr = float(d[0]["fundingRate"])
                return {"ex": "okx", "symbol": f"{coin}-USDT-SWAP", "rate": fr, "interval_h": 8,
                        "apr": fr * 3 * 365, "volume_usd": None}
        except Exception:
            return None
    with ThreadPoolExecutor(max_workers=6) as pool:
        for f in as_completed([pool.submit(okx_one, c) for c in okx_majors]):
            r = f.result()
            if r:
                rows.append(r)
    return rows


# ---------------- prediction markets ----------------

def fetch_polymarket_events():
    """Multi-outcome (neg-risk) events: sum of YES asks < $1 => guaranteed
    profit buying every outcome; sum of YES bids > $1 => profit selling all."""
    events = []
    offset = 0
    while offset < 2000:
        try:
            batch = get_json(
                "https://gamma-api.polymarket.com/events",
                params={"closed": "false", "limit": 100, "offset": offset,
                        "order": "volume24hr", "ascending": "false"})
        except requests.HTTPError:
            break
        if not batch:
            break
        events.extend(batch)
        offset += 100
        if len(batch) < 100:
            break
    out = []
    for ev in events:
        markets = ev.get("markets") or []
        if len(markets) < 2 or not ev.get("negRisk"):
            continue
        asks, bids, ok = [], [], True
        for m in markets:
            if m.get("closed"):
                continue
            try:
                ask = float(m.get("bestAsk"))
                bid = float(m.get("bestBid"))
            except (TypeError, ValueError):
                ok = False
                break
            asks.append(ask)
            bids.append(bid)
        if not ok or len(asks) < 2:
            continue
        out.append({
            "platform": "polymarket", "title": ev.get("title"),
            "slug": ev.get("slug"), "n_outcomes": len(asks),
            "sum_yes_ask": round(sum(asks), 4), "sum_yes_bid": round(sum(bids), 4),
            "volume24h": ev.get("volume24hr"),
        })
    return out


def fetch_kalshi_events():
    """Mutually-exclusive Kalshi events: buy YES on every outcome for
    sum(yes_ask) < $1, or buy NO on every outcome when sum(yes_bid) > $1."""
    events = []
    cursor = None
    for _ in range(20):
        params = {"limit": 200, "status": "open", "with_nested_markets": "true"}
        if cursor:
            params["cursor"] = cursor
        d = get_json("https://api.elections.kalshi.com/trade-api/v2/events", params=params)
        events.extend(d.get("events") or [])
        cursor = d.get("cursor")
        if not cursor:
            break
    out = []
    for ev in events:
        if not ev.get("mutually_exclusive"):
            continue
        ms = [m for m in (ev.get("markets") or []) if m.get("status") == "active"]
        if len(ms) < 2:
            continue
        try:
            asks = [float(m["yes_ask_dollars"]) for m in ms]
            bids = [float(m["yes_bid_dollars"]) for m in ms]
        except (TypeError, KeyError, ValueError):
            continue
        if any(a <= 0 for a in asks):  # can't buy every outcome
            continue
        vol = sum(m.get("volume_24h") or 0 for m in ms)
        out.append({
            "platform": "kalshi", "title": ev.get("title"), "event_ticker": ev.get("event_ticker"),
            "n_outcomes": len(ms), "sum_yes_ask": round(sum(asks), 4),
            "sum_yes_bid": round(sum(bids), 4), "volume24h": vol,
        })
    return out


# ---------------- order-book verification ----------------

def _norm_book(bids, asks):
    """bids/asks as [[price, qty], ...] floats, best first."""
    b = sorted(([float(p), float(q)] for p, q in bids), key=lambda x: -x[0])
    a = sorted(([float(p), float(q)] for p, q in asks), key=lambda x: x[0])
    return {"bids": b, "asks": a}


def fetch_book(ex, sym):
    if ex == "kucoin":
        d = get_json(f"https://api.kucoin.com/api/v1/market/orderbook/level2_20?symbol={sym}")["data"]
        return _norm_book(d["bids"], d["asks"])
    if ex == "okx":
        d = get_json(f"https://www.okx.com/api/v5/market/books?instId={sym}&sz=20")["data"][0]
        return _norm_book([x[:2] for x in d["bids"]], [x[:2] for x in d["asks"]])
    if ex == "gate":
        d = get_json(f"https://api.gateio.ws/api/v4/spot/order_book?currency_pair={sym}&limit=20")
        return _norm_book(d["bids"], d["asks"])
    if ex == "mexc":
        d = get_json(f"https://api.mexc.com/api/v3/depth?symbol={sym}&limit=20")
        return _norm_book(d["bids"], d["asks"])
    if ex == "htx":
        d = get_json(f"https://api.huobi.pro/market/depth?symbol={sym}&type=step0&depth=20")["tick"]
        return _norm_book([x[:2] for x in d["bids"]], [x[:2] for x in d["asks"]])
    if ex == "bitfinex":
        d = get_json(f"https://api-pub.bitfinex.com/v2/book/{sym}/P0?len=25")
        bids = [[x[0], x[2]] for x in d if x[2] > 0]
        asks = [[x[0], -x[2]] for x in d if x[2] < 0]
        return _norm_book(bids, asks)
    if ex == "bitstamp":
        d = get_json(f"https://www.bitstamp.net/api/v2/order_book/{sym}/")
        return _norm_book(d["bids"][:25], d["asks"][:25])
    if ex == "bitget":
        d = get_json(f"https://api.bitget.com/api/v2/spot/market/orderbook?symbol={sym}&type=step0&limit=20")["data"]
        return _norm_book(d["bids"], d["asks"])
    if ex == "cryptocom":
        d = get_json(f"https://api.crypto.com/exchange/v1/public/get-book?instrument_name={sym}&depth=20")["result"]["data"][0]
        return _norm_book([x[:2] for x in d["bids"]], [x[:2] for x in d["asks"]])
    if ex == "kraken":
        d = get_json(f"https://api.kraken.com/0/public/Depth?pair={sym}&count=20")["result"]
        book = next(iter(d.values()))
        return _norm_book([x[:2] for x in book["bids"]], [x[:2] for x in book["asks"]])
    if ex == "coinbase":
        d = get_json(f"https://api.exchange.coinbase.com/products/{sym}/book?level=2")
        return _norm_book([x[:2] for x in d["bids"][:25]], [x[:2] for x in d["asks"][:25]])
    raise ValueError(ex)


def vwap_fill(levels, notional):
    """Average price to trade `notional` (quote units) against book levels.
    Returns (vwap, filled_notional)."""
    remaining, cost, qty = notional, 0.0, 0.0
    for price, size in levels:
        take_q = min(remaining / price, size)
        cost += take_q * price
        qty += take_q
        remaining -= take_q * price
        if remaining <= 1e-9:
            break
    if qty == 0:
        return None, 0.0
    return cost / qty, cost


def verify_opportunities(opps, tickers, top_n=40, notional=2000):
    """Re-check top spot opportunities against live depth minutes after the
    ticker snapshot: executable VWAP spread for `notional` per leg."""
    sym_map = {(t["ex"], t["base"], t["quote"]): t["sym"] for t in tickers}

    def verify_one(o):
        try:
            buy_book = fetch_book(o["buy_ex"], sym_map[(o["buy_ex"], o["asset"], o["quote"])])
            sell_book = fetch_book(o["sell_ex"], sym_map[(o["sell_ex"], o["asset"], o["quote"])])
            buy_vwap, buy_fill = vwap_fill(buy_book["asks"], notional)
            sell_vwap, sell_fill = vwap_fill(sell_book["bids"], notional)
            if not buy_vwap or not sell_vwap:
                o["verified"] = {"status": "no_depth"}
                return
            gross = (sell_vwap - buy_vwap) / buy_vwap * 100
            o["verified"] = {
                "status": "ok",
                "buy_vwap": buy_vwap, "sell_vwap": sell_vwap,
                "fill_usd": round(min(buy_fill, sell_fill)),
                "gross_pct": round(gross, 3),
                "net_pct": round(gross - o["fees_pct"], 3),
            }
        except Exception as e:
            o["verified"] = {"status": f"error: {type(e).__name__}"}

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(verify_one, opps[:top_n]))


# ---------------- analysis ----------------

def build_triangles(tickers, min_leg_qvol_usd=50_000):
    """Same-exchange triangular cycles: stable -> X -> BTC/ETH -> stable and
    the reverse. No transfers involved; three taker fills."""
    by_ex = {}
    for t in tickers:
        by_ex.setdefault(t["ex"], {})[(t["base"], t["quote"])] = t
    out = []
    for ex, pairs in by_ex.items():
        fee = 1 - TAKER_FEE[ex]
        for cross in ("BTC", "ETH"):
            for stable in USD_QUOTES:
                cs = pairs.get((cross, stable))
                if not cs or cs["qvol"] < min_leg_qvol_usd:
                    continue
                for (base, quote), xs in pairs.items():
                    if quote != stable or base == cross:
                        continue
                    xc = pairs.get((base, cross))
                    if not xc:
                        continue
                    xc_qvol_usd = xc["qvol"] * cs["last"]
                    if xs["qvol"] < min_leg_qvol_usd or xc_qvol_usd < min_leg_qvol_usd:
                        continue
                    # path A: stable -> buy X -> sell X for cross -> sell cross
                    mult_a = (1 / xs["ask"]) * xc["bid"] * cs["bid"] * fee ** 3
                    # path B: stable -> buy cross -> buy X with cross -> sell X
                    mult_b = (1 / cs["ask"]) * (1 / xc["ask"]) * xs["bid"] * fee ** 3
                    for mult, path in ((mult_a, f"{stable}->{base}->{cross}->{stable}"),
                                       (mult_b, f"{stable}->{cross}->{base}->{stable}")):
                        net = (mult - 1) * 100
                        if net > -0.5:  # keep near-misses for context
                            out.append({
                                "type": "triangular", "ex": ex, "path": path,
                                "asset": base, "cross": cross, "stable": stable,
                                "net_pct": round(net, 4),
                                "min_leg_qvol_usd": round(min(xs["qvol"], xc_qvol_usd, cs["qvol"])),
                            })
    out.sort(key=lambda o: o["net_pct"], reverse=True)
    return out


def verify_triangles(tris, tickers, top_n=15, notional=1000):
    """Re-check triangle legs against live order books."""
    sym_map = {(t["ex"], t["base"], t["quote"]): t["sym"] for t in tickers}

    def one(tr):
        try:
            legs = tr["path"].split("->")  # [stable, a, b, stable]
            stable, mid1, mid2 = legs[0], legs[1], legs[2]
            fee = 1 - TAKER_FEE[tr["ex"]]
            if mid1 == tr["asset"]:  # path A: buy X/S, sell X/C, sell C/S
                xs = fetch_book(tr["ex"], sym_map[(tr["ex"], tr["asset"], stable)])
                xc = fetch_book(tr["ex"], sym_map[(tr["ex"], tr["asset"], tr["cross"])])
                cs = fetch_book(tr["ex"], sym_map[(tr["ex"], tr["cross"], stable)])
                v1, _ = vwap_fill(xs["asks"], notional)
                x_amt = notional / v1
                v2, _ = vwap_fill(xc["bids"], x_amt * xc["bids"][0][0])
                c_amt = x_amt * v2
                v3, _ = vwap_fill(cs["bids"], c_amt * cs["bids"][0][0])
                end = c_amt * v3 * fee ** 3
            else:  # path B: buy C/S, buy X/C, sell X/S
                cs = fetch_book(tr["ex"], sym_map[(tr["ex"], tr["cross"], stable)])
                xc = fetch_book(tr["ex"], sym_map[(tr["ex"], tr["asset"], tr["cross"])])
                xs = fetch_book(tr["ex"], sym_map[(tr["ex"], tr["asset"], stable)])
                v1, _ = vwap_fill(cs["asks"], notional)
                c_amt = notional / v1
                v2, _ = vwap_fill(xc["asks"], c_amt)
                x_amt = c_amt / v2
                v3, _ = vwap_fill(xs["bids"], x_amt * xs["bids"][0][0])
                end = x_amt * v3 * fee ** 3
            tr["verified"] = {"status": "ok", "net_pct": round((end / notional - 1) * 100, 4)}
        except Exception as e:
            tr["verified"] = {"status": f"error: {type(e).__name__}"}

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(one, tris[:top_n]))


def build_spot_opportunities(tickers, min_qvol=150_000, max_spread_pct=30.0):
    groups = {}
    for t in tickers:
        if t["quote"] not in USD_QUOTES:
            continue
        groups.setdefault((t["base"], t["quote"]), []).append(t)
    opps = []
    for (base, quote), rows in groups.items():
        liquid = [r for r in rows if r["qvol"] >= min_qvol]
        if len(liquid) < 2:
            continue
        buy = min(liquid, key=lambda r: r["ask"])
        sell = max(liquid, key=lambda r: r["bid"])
        if buy["ex"] == sell["ex"]:
            continue
        gross = (sell["bid"] - buy["ask"]) / buy["ask"] * 100
        if gross <= 0 or gross > max_spread_pct:
            continue
        fees = (TAKER_FEE[buy["ex"]] + TAKER_FEE[sell["ex"]]) * 100
        opps.append({
            "type": "spot_cross_exchange",
            "asset": base, "quote": quote,
            "buy_ex": buy["ex"], "buy_ask": buy["ask"], "buy_qvol": round(buy["qvol"]),
            "sell_ex": sell["ex"], "sell_bid": sell["bid"], "sell_qvol": round(sell["qvol"]),
            "gross_pct": round(gross, 3),
            "fees_pct": round(fees, 3),
            "net_pct": round(gross - fees, 3),
            "n_venues": len(liquid),
        })
    opps.sort(key=lambda o: o["net_pct"], reverse=True)
    return opps


def main():
    started = time.time()
    fetchers = {
        "kucoin": fetch_kucoin, "okx": fetch_okx, "gate": fetch_gate,
        "mexc": fetch_mexc, "htx": fetch_htx, "bitfinex": fetch_bitfinex,
        "bitstamp": fetch_bitstamp, "bitget": fetch_bitget,
        "cryptocom": fetch_cryptocom, "kraken": fetch_kraken,
    }
    tickers = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {pool.submit(fn): name for name, fn in fetchers.items()}
        for f in as_completed(futs):
            name = futs[f]
            try:
                rows = f.result()
                print(f"[spot] {name}: {len(rows)} pairs", flush=True)
                tickers.extend(rows)
            except Exception:
                print(f"[spot] {name}: FAILED", flush=True)
                traceback.print_exc()

    bases_elsewhere = {t["base"] for t in tickers}
    try:
        cb = fetch_coinbase(bases_elsewhere)
        print(f"[spot] coinbase: {len(cb)} pairs", flush=True)
        tickers.extend(cb)
    except Exception:
        print("[spot] coinbase: FAILED", flush=True)
        traceback.print_exc()

    print("[status] fetching transfer status (gate, kucoin, htx, bitget)...", flush=True)
    statuses = {
        "gate": fetch_gate_currency_status(),
        "kucoin": fetch_kucoin_currency_status(),
        "htx": fetch_htx_currency_status(),
        "bitget": fetch_bitget_currency_status(),
    }

    print("[funding] fetching funding rates...", flush=True)
    funding = fetch_funding()

    print("[prediction] fetching polymarket + kalshi...", flush=True)
    try:
        poly = fetch_polymarket_events()
    except Exception:
        traceback.print_exc()
        poly = []
    try:
        kalshi = fetch_kalshi_events()
    except Exception:
        traceback.print_exc()
        kalshi = []

    opps = build_spot_opportunities(tickers)
    print(f"[verify] re-checking top {min(40, len(opps))} against live order books...", flush=True)
    verify_opportunities(opps, tickers)
    for o in opps:
        notes = []
        for ex in (o["buy_ex"], o["sell_ex"]):
            st = statuses.get(ex, {})
            if o["asset"] in st:
                s = st[o["asset"]]
                if not s["deposit"] or not s["withdraw"]:
                    notes.append(f"{ex}: deposit={'on' if s['deposit'] else 'OFF'} withdraw={'on' if s['withdraw'] else 'OFF'}")
        o["transfer_notes"] = "; ".join(notes)

    print("[triangles] scanning same-exchange triangular cycles...", flush=True)
    triangles = build_triangles(tickers)
    verify_triangles(triangles, tickers)

    snapshot = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_tickers": len(tickers),
        "spot_opportunities": opps,
        "triangles": triangles[:200],
        "funding": sorted(funding, key=lambda r: abs(r["apr"]), reverse=True),
        "polymarket_events": poly,
        "kalshi_events": kalshi,
    }
    with open(os.path.join(OUT_DIR, "merged_tickers.json"), "w") as f:
        json.dump(tickers, f)
    with open(os.path.join(OUT_DIR, "opportunities.json"), "w") as f:
        json.dump(snapshot, f, indent=1)

    print(f"\nDone in {time.time()-started:.0f}s: {len(tickers)} tickers, "
          f"{len(opps)} spot opps, {len(funding)} funding rows, "
          f"{len(poly)} poly events, {len(kalshi)} kalshi events", flush=True)
    print("\nTop 30 spot spreads (ticker net vs order-book-verified net for $2k):")
    for o in opps[:30]:
        v = o.get("verified") or {}
        vtxt = f"verified {v['net_pct']:+.2f}% (${v['fill_usd']} fillable)" if v.get("status") == "ok" else v.get("status", "-")
        print(f"  {o['asset']}/{o['quote']:5s} buy {o['buy_ex']:9s} sell {o['sell_ex']:9s} "
              f"ticker {o['net_pct']:+.2f}% | {vtxt} {o['transfer_notes']}")

    print("\nTop triangular cycles (same exchange, no transfers):")
    for tr in triangles[:15]:
        v = tr.get("verified") or {}
        vtxt = f"verified {v['net_pct']:+.3f}%" if v.get("status") == "ok" else v.get("status", "-")
        print(f"  [{tr['ex']}] {tr['path']:28s} ticker {tr['net_pct']:+.3f}% | {vtxt} "
              f"(min leg vol ${tr['min_leg_qvol_usd']:,})")

    # sum_yes_bid > 1: buy NO on every outcome — robust even if outcome list
    # is not exhaustive (mutual exclusivity alone suffices).
    robust = [e for e in poly + kalshi if e["sum_yes_bid"] > 1.005]
    print(f"\nPrediction-market robust arbs (sum of YES bids > $1): {len(robust)}")
    for e in sorted(robust, key=lambda x: -x["sum_yes_bid"])[:15]:
        print(f"  [{e['platform']}] sum_bid={e['sum_yes_bid']:.3f} n={e['n_outcomes']} "
              f"vol24h={e.get('volume24h')} :: {str(e['title'])[:70]}")


if __name__ == "__main__":
    main()
