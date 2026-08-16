#!/usr/bin/env python3
"""Beyond-the-obvious digital arbitrage scanner.

Eight structural opportunity classes that plain cross-exchange scans miss:
  1. DEX aggregator round-trips (Jupiter, executable quotes w/ price impact)
  2. CEX<->DEX dislocations on Solana (transfers settle in seconds)
  3. Prediction-market ladder violations (P(>=K_hi) priced above P(>=K_lo))
  4. Deribit put-call parity violations (inverse options)
  5. Options-implied digitals vs Polymarket prices (same strike, same date)
  6. Dated-futures basis (locked carry to expiry, not floating funding)
  7. Cross-venue funding spread (same coin, both perps, no spot leg)
  8. Tokenized gold (PAXG/XAUT) + kimchi premium + Pendle fixed yields + stETH

Public endpoints only. Writes data/beyond_obvious.json.
"""

import json
import os
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
S = requests.Session()
S.headers.update({"User-Agent": "arb-research/1.0"})


def get_json(url, **kw):
    kw.setdefault("timeout", 25)
    r = S.get(url, **kw)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------- Jupiter
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
MINTS = {
    "SOL": ("So11111111111111111111111111111111111111112", 9),
    "WIF": ("EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm", 6),
    "JUP": ("JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN", 6),
    "BONK": ("DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", 5),
    "JTO": ("jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL", 9),
    "PYTH": ("HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3", 6),
    "RAY": ("4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R", 6),
    "POPCAT": ("7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr", 9),
    "TRUMP": ("6p6xgHyF7AeE6TZkSmFsko444wqoP15icUSqi2jfGiPN", 6),
    "FARTCOIN": ("9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump", 6),
    "PENGU": ("2zMMhcVQEXDtdE6vsFS7S7D5oUodfJHE8vd1gnBouauv", 6),
    "MEW": ("MEW1gQWJ3nEXg2qgERiKu7FAFj79PHvQVREQUzScPP5", 5),
}
NOTIONAL_USD = 2000


def jup_quote(in_mint, out_mint, amount):
    q = get_json("https://lite-api.jup.ag/swap/v1/quote",
                 params={"inputMint": in_mint, "outputMint": out_mint,
                         "amount": str(amount), "slippageBps": "50"})
    return int(q["outAmount"])


def scan_jupiter():
    """USDC -> token -> USDC round trips + per-token dex buy/sell prices."""
    out = {}
    usdc_in = NOTIONAL_USD * 10**6
    for name, (mint, dec) in MINTS.items():
        try:
            tok = jup_quote(USDC, mint, usdc_in)          # buy leg
            time.sleep(0.55)
            back = jup_quote(mint, USDC, tok)             # sell leg
            time.sleep(0.55)
            out[name] = {
                "buy_px": usdc_in / 10**6 / (tok / 10**dec),   # USD per token
                "sell_px": (back / 10**6) / (tok / 10**dec),
                "roundtrip_pct": (back / usdc_in - 1) * 100,
            }
            print(f"  [jup] {name}: roundtrip {out[name]['roundtrip_pct']:+.3f}%", flush=True)
        except Exception as e:
            print(f"  [jup] {name}: {type(e).__name__}", flush=True)
    return out


def scan_cex_dex(jup):
    """Compare Jupiter executable prices vs CEX best bid/ask from merged tickers."""
    ticks = json.load(open(os.path.join(D, "merged_tickers.json")))
    rows = []
    for t in ticks:
        if t["base"] in jup and t["quote"] in ("USDT", "USDC") and t["qvol"] > 200_000:
            j = jup[t["base"]]
            # buy on CEX at ask, sell on DEX at Jupiter sell price
            cex_to_dex = (j["sell_px"] / t["ask"] - 1) * 100
            # buy on DEX, sell on CEX at bid
            dex_to_cex = (t["bid"] / j["buy_px"] - 1) * 100
            rows.append({
                "asset": t["base"], "cex": t["ex"], "quote": t["quote"],
                "cex_bid": t["bid"], "cex_ask": t["ask"],
                "dex_buy": j["buy_px"], "dex_sell": j["sell_px"],
                "cex_to_dex_pct": round(cex_to_dex, 3),
                "dex_to_cex_pct": round(dex_to_cex, 3),
                "cex_qvol": round(t["qvol"]),
            })
    rows.sort(key=lambda r: max(r["cex_to_dex_pct"], r["dex_to_cex_pct"]), reverse=True)
    return rows


# ------------------------------------------------- Polymarket ladders
THRESH_RE = re.compile(r"\$?([0-9][0-9,\.]*)\s*(k|K)?")


def parse_threshold(question):
    """Extract the dollar threshold from questions like
    'Will Bitcoin reach $130,000 in August?' / 'Bitcoin above $64K on ...'"""
    m = re.findall(r"\$([0-9][0-9,\.]*)\s*([kKmMbBtT])?", question)
    if not m:
        return None
    num, suf = m[0]
    v = float(num.replace(",", ""))
    v *= {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}.get(suf.lower(), 1) if suf else 1
    return v


def scan_polymarket_ladders():
    """Within threshold-ladder events: 'above K_hi' implies 'above K_lo', so
    ask(K_lo) must be >= bid(K_hi). ask(K_lo) < bid(K_hi) = riskless pair."""
    events = []
    for off in range(0, 900, 100):
        batch = get_json("https://gamma-api.polymarket.com/events",
                         params={"closed": "false", "limit": 100, "offset": off,
                                 "order": "volume24hr", "ascending": "false"})
        if not batch:
            break
        events.extend(batch)
    rows = []
    for ev in events:
        slug = ev.get("slug") or ""
        # only cumulative-threshold families; 'price-on' events are exclusive RANGES
        if not re.search(r"(above-on|price-will|-hit-|reach)", slug):
            continue
        ups, downs = [], []
        for m in ev.get("markets") or []:
            if m.get("closed"):
                continue
            q = m.get("question") or ""
            k = parse_threshold(q)
            try:
                bid, ask = float(m["bestBid"]), float(m["bestAsk"])
            except (KeyError, TypeError, ValueError):
                continue
            if not k:
                continue
            if re.search(r"(dip|drop|fall|below|crash|\(LOW\))", q, re.I):
                downs.append((k, bid, ask, q))
            else:
                ups.append((k, bid, ask, q))
        for ms, reverse in ((ups, False), (downs, True)):
            if len(ms) < 3:
                continue
            ms.sort(reverse=reverse)
            # after sort, index i is implied BY index j>i (weaker first)
            for i in range(len(ms)):
                for jx in range(i + 1, len(ms)):
                    k_lo, bid_lo, ask_lo, q_lo = ms[i]
                    k_hi, bid_hi, ask_hi, q_hi = ms[jx]
                    # outcome hi implies outcome lo => P(lo) >= P(hi)
                    edge = bid_hi - ask_lo
                    if edge > 0.002 and ask_lo > 0 and bid_hi < 1:
                        rows.append({
                            "event": ev.get("title"), "slug": slug,
                            "weak": q_lo, "weak_ask": ask_lo,
                            "strong": q_hi, "strong_bid": bid_hi,
                            "edge_per_set": round(edge, 4),
                            "ret_pct": round(edge / (ask_lo + 1 - bid_hi) * 100, 2),
                            "vol24h": ev.get("volume24hr"),
                        })
    rows.sort(key=lambda r: -r["edge_per_set"])
    return rows


# ------------------------------------------------- Deribit
def scan_deribit():
    opts = get_json("https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
                    params={"currency": "BTC", "kind": "option"})["result"]
    futs = get_json("https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
                    params={"currency": "BTC", "kind": "future"})["result"]
    fut_px = {}
    for f in futs:
        name = f["instrument_name"]          # BTC-28AUG26 or BTC-PERPETUAL
        if name.count("-") == 1 and f.get("mark_price"):
            fut_px[name.split("-")[1]] = f["mark_price"]

    chain = {}
    for o in opts:
        parts = o["instrument_name"].split("-")   # BTC-28AUG26-60000-C
        if len(parts) != 4:
            continue
        _, exp, k, cp = parts
        chain.setdefault((exp, float(k)), {})[cp] = o

    parity = []
    for (exp, k), legs in chain.items():
        c, p = legs.get("C"), legs.get("P")
        F = fut_px.get(exp)
        if not (c and p and F):
            continue
        cb, ca = c.get("bid_price") or 0, c.get("ask_price") or 0
        pb, pa = p.get("bid_price") or 0, p.get("ask_price") or 0
        if not (cb and ca and pb and pa):
            continue
        rhs = (F - k) / F                     # BTC-terms parity for inverse options
        fee = 0.0006                          # ~2 legs of 0.0003 BTC/contract
        v1 = (cb - pa) - rhs - fee            # sell call, buy put, buy future
        v2 = -(ca - pb) + rhs - fee           # buy call, sell put, sell future
        viol = max(v1, v2)
        if viol > 0:
            parity.append({
                "expiry": exp, "strike": k, "future": round(F, 1),
                "call_bid": cb, "call_ask": ca, "put_bid": pb, "put_ask": pa,
                "viol_btc": round(viol, 5),
                "viol_usd": round(viol * F, 2),
                "direction": "sell C / buy P / long F" if v1 > v2 else "buy C / sell P / short F",
            })
    parity.sort(key=lambda r: -r["viol_usd"])

    # options-implied digital probabilities per expiry (call-spread mids)
    digitals = {}
    for (exp, k), legs in chain.items():
        c = legs.get("C")
        if not c:
            continue
        mark = c.get("mark_price")
        if mark is not None:
            digitals.setdefault(exp, []).append((k, mark))
    digital_curves = {}
    for exp, pts in digitals.items():
        pts.sort()
        F = fut_px.get(exp)
        if not F or len(pts) < 4:
            continue
        curve = []
        for (k1, m1), (k2, m2) in zip(pts, pts[1:]):
            gap = k2 - k1
            if gap <= 0 or gap > 4000:
                continue
            # convert BTC-denominated marks to USD, then digital = -dC/dK
            p_digital = min(1.0, max(0.0, (m1 - m2) * F / gap))
            curve.append({"k_mid": (k1 + k2) / 2, "p_above": round(p_digital, 4)})
        digital_curves[exp] = {"future": F, "curve": curve}
    return parity, digital_curves


def scan_pm_vs_deribit(digital_curves):
    """Match Polymarket 'bitcoin above K on DATE' to nearest Deribit expiry."""
    MONTHS = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
              "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}
    events = get_json("https://gamma-api.polymarket.com/events",
                      params={"closed": "false", "limit": 100, "order": "volume24hr",
                              "ascending": "false", "tag_slug": "crypto"})
    rows = []
    for ev in events:
        slug = ev.get("slug") or ""
        m = re.match(r"bitcoin-above-on-([a-z]+)-(\d+)-2026", slug)
        if not m:
            continue
        month, day = m.group(1)[:3].upper(), int(m.group(2))
        # find a Deribit expiry on the same day (Polymarket resolves 12:00 ET,
        # Deribit 08:00 UTC — 9h apart, flagged in output)
        exp_match = None
        for exp in digital_curves:
            em = re.match(r"(\d+)([A-Z]{3})26", exp)
            if em and MONTHS.get(em.group(2)) == MONTHS.get(month) and int(em.group(1)) == day:
                exp_match = exp
        if not exp_match:
            continue
        curve = digital_curves[exp_match]["curve"]
        for mk in ev.get("markets") or []:
            k = parse_threshold(mk.get("question") or "")
            try:
                bid, ask = float(mk["bestBid"]), float(mk["bestAsk"])
            except (KeyError, TypeError, ValueError):
                continue
            if not k or not curve:
                continue
            nearest = min(curve, key=lambda c: abs(c["k_mid"] - k))
            if abs(nearest["k_mid"] - k) > 3000:
                continue
            rows.append({
                "question": mk.get("question"), "strike": k,
                "pm_bid": bid, "pm_ask": ask,
                "deribit_expiry": exp_match,
                "deribit_p": nearest["p_above"],
                "gap": round(nearest["p_above"] - (bid + ask) / 2, 4),
            })
    rows.sort(key=lambda r: -abs(r["gap"]))
    return rows


# ------------------------------------------------- dated futures basis
def scan_basis():
    spot = {}
    for t in json.load(open(os.path.join(D, "merged_tickers.json"))):
        if t["quote"] == "USDT" and t["ex"] == "gate":
            spot[t["base"]] = (t["bid"] + t["ask"]) / 2
    rows = []
    now = time.time()
    for c in get_json("https://api.gateio.ws/api/v4/delivery/usdt/contracts"):
        base = c["name"].split("_")[0]
        s = spot.get(base)
        mark = float(c.get("mark_price") or 0)
        exp = c.get("expire_time") or 0
        if not (s and mark and exp and exp > now):
            continue
        days = (exp - now) / 86400
        basis = (mark - s) / s
        rows.append({
            "contract": c["name"], "spot": s, "future": mark,
            "days": round(days, 1), "basis_pct": round(basis * 100, 3),
            "apr_pct": round(basis / days * 365 * 100, 2),
        })
    rows.sort(key=lambda r: -abs(r["apr_pct"]))
    return rows


# ------------------------------------------------- cross-venue funding spread
def scan_funding_spread():
    cur = json.load(open(os.path.join(D, "opportunities.json")))
    per_coin = {}
    for f in cur["funding"]:
        coin = f["symbol"].replace("_USDT", "").replace("-USDT-SWAP", "")
        if coin.endswith("USDT"):
            coin = coin[:-4]
        daily = f["rate"] * (24 / f["interval_h"])
        per_coin.setdefault(coin, {})[f["ex"]] = daily
    rows = []
    for coin, venues in per_coin.items():
        if len(venues) < 2:
            continue
        hi_ex = max(venues, key=venues.get)
        lo_ex = min(venues, key=venues.get)
        spread = venues[hi_ex] - venues[lo_ex]
        if spread * 100 > 0.15:
            rows.append({
                "coin": coin,
                "short_on": hi_ex, "short_daily_pct": round(venues[hi_ex] * 100, 3),
                "long_on": lo_ex, "long_daily_pct": round(venues[lo_ex] * 100, 3),
                "net_daily_pct": round(spread * 100, 3),
            })
    rows.sort(key=lambda r: -r["net_daily_pct"])
    return rows


# ------------------------------------------------- gold / kimchi / pendle / lst
def scan_gold():
    rows = []
    for t in json.load(open(os.path.join(D, "merged_tickers.json"))):
        if t["base"] in ("PAXG", "XAUT") and t["quote"] in ("USD", "USDT"):
            rows.append({k: t[k] for k in ("ex", "base", "quote", "bid", "ask", "qvol")})
    return rows


def scan_kimchi():
    fx = get_json("https://api.frankfurter.app/latest?from=USD&to=KRW")["rates"]["KRW"]
    markets = "KRW-BTC,KRW-ETH,KRW-XRP,KRW-SOL,KRW-DOGE"
    up = get_json(f"https://api.upbit.com/v1/ticker?markets={markets}")
    glob = {}
    for t in json.load(open(os.path.join(D, "merged_tickers.json"))):
        if t["quote"] == "USDT" and t["ex"] in ("okx", "gate", "kucoin") and t["base"] in ("BTC", "ETH", "XRP", "SOL", "DOGE"):
            glob.setdefault(t["base"], []).append((t["bid"] + t["ask"]) / 2)
    rows = []
    for u in up:
        base = u["market"].split("-")[1]
        if base not in glob:
            continue
        g = sorted(glob[base])[len(glob[base]) // 2]
        krw_usd = u["trade_price"] / fx
        rows.append({
            "asset": base, "upbit_krw": u["trade_price"], "usdkrw": fx,
            "upbit_usd": round(krw_usd, 2), "global_usd": round(g, 2),
            "premium_pct": round((krw_usd / g - 1) * 100, 3),
        })
    return rows


def scan_pendle():
    rows = []
    for chain in (1, 42161):
        try:
            mks = get_json(f"https://api-v2.pendle.finance/core/v1/{chain}/markets/active")
            mks = mks.get("markets") or mks
        except Exception:
            continue
        for m in mks:
            det = m.get("details") or {}
            liq = det.get("liquidity") or 0
            apy = det.get("impliedApy")
            if apy is None or liq < 1_000_000:
                continue
            rows.append({
                "chain": chain, "name": m["name"], "expiry": m["expiry"][:10],
                "implied_apy_pct": round(apy * 100, 2),
                "liquidity_usd": round(liq),
            })
    rows.sort(key=lambda r: -r["implied_apy_pct"])
    return rows


STETH = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
PAXG_E = "0x45804880De22913dAFE09f4980848ECE6EcbAf78"
XAUT_E = "0x68749665FF8D2d112Fa859AA293F07A622782F38"


def kyber_out(token_in, token_out, amount_in):
    r = get_json("https://aggregator-api.kyberswap.com/ethereum/api/v1/routes",
                 params={"tokenIn": token_in, "tokenOut": token_out, "amountIn": str(amount_in)})
    return int(r["data"]["routeSummary"]["amountOut"])


def scan_onchain_pairs():
    rows = []
    try:
        out = kyber_out(STETH, WETH, 25 * 10**18)   # 25 stETH -> WETH
        rows.append({"pair": "stETH->WETH (25)", "rate": out / (25 * 10**18),
                     "note": "redeemable 1:1 via Lido queue (days)"})
    except Exception:
        traceback.print_exc()
    try:
        out = kyber_out(PAXG_E, XAUT_E, 10 * 10**18)  # PAXG 18d -> XAUT 6d
        rows.append({"pair": "PAXG->XAUT (10oz)", "rate": out / (10 * 10**6),
                     "note": "both claim 1 fine troy oz"})
        out2 = kyber_out(XAUT_E, PAXG_E, 10 * 10**6)
        rows.append({"pair": "XAUT->PAXG (10oz)", "rate": out2 / (10 * 10**18),
                     "note": "reverse leg"})
    except Exception:
        traceback.print_exc()
    return rows


def main():
    t0 = time.time()
    result = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    print("[1/8] Jupiter round-trips...", flush=True)
    jup = scan_jupiter()
    result["jupiter"] = jup
    print("[2/8] CEX<->DEX dislocations...", flush=True)
    result["cex_dex"] = scan_cex_dex(jup)

    print("[3/8] Polymarket ladder violations...", flush=True)
    try:
        result["ladders"] = scan_polymarket_ladders()
    except Exception:
        traceback.print_exc(); result["ladders"] = []

    print("[4/8] Deribit parity + digitals...", flush=True)
    try:
        parity, curves = scan_deribit()
        result["deribit_parity"] = parity
        print("[5/8] Polymarket vs Deribit digitals...", flush=True)
        result["pm_vs_deribit"] = scan_pm_vs_deribit(curves)
    except Exception:
        traceback.print_exc(); result["deribit_parity"] = []; result["pm_vs_deribit"] = []

    print("[6/8] Dated-futures basis...", flush=True)
    try:
        result["basis"] = scan_basis()
    except Exception:
        traceback.print_exc(); result["basis"] = []

    print("[7/8] Funding spreads / gold / kimchi...", flush=True)
    try:
        result["funding_spread"] = scan_funding_spread()
    except Exception:
        traceback.print_exc(); result["funding_spread"] = []
    try:
        result["gold"] = scan_gold()
        result["kimchi"] = scan_kimchi()
    except Exception:
        traceback.print_exc()

    print("[8/8] Pendle + on-chain pairs...", flush=True)
    try:
        result["pendle"] = scan_pendle()
    except Exception:
        traceback.print_exc(); result["pendle"] = []
    try:
        result["onchain_pairs"] = scan_onchain_pairs()
    except Exception:
        traceback.print_exc(); result["onchain_pairs"] = []

    with open(os.path.join(D, "beyond_obvious.json"), "w") as f:
        json.dump(result, f, indent=1)

    print(f"\nDone in {time.time()-t0:.0f}s")
    print(f"  cex_dex rows: {len(result['cex_dex'])}, ladders: {len(result['ladders'])}, "
          f"parity: {len(result['deribit_parity'])}, pm_vs_deribit: {len(result['pm_vs_deribit'])}, "
          f"basis: {len(result['basis'])}, funding_spread: {len(result['funding_spread'])}, "
          f"pendle: {len(result['pendle'])}, onchain: {len(result['onchain_pairs'])}")


if __name__ == "__main__":
    main()
