#!/usr/bin/env python3
"""Instantly-repeatable loop scanner.

Only structures where capital returns in seconds and the cycle can repeat:
  1. Same-venue stable-cross loops: X/USDT vs X/USDC (vs the venue's own
     USDC/USDT rate) - 2-3 taker fills, no transfers, repeat immediately.
  2. Two-venue simultaneous loops with pre-positioned inventory: buy on A,
     sell on B at the same instant; transfers only to rebalance. Requires
     open deposit+withdraw both sides and a verified positive spread.
  3. BTC/ETH-cross triangles (re-run for completeness).

Writes data/instant_loops.json.
"""

import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from scan import (TAKER_FEE, fetch_kucoin, fetch_okx, fetch_gate, fetch_mexc,
                  fetch_htx, fetch_bitfinex, fetch_bitstamp, fetch_bitget,
                  fetch_cryptocom, fetch_kraken, fetch_coinbase,
                  fetch_gate_currency_status, fetch_kucoin_currency_status,
                  fetch_htx_currency_status, fetch_bitget_currency_status,
                  fetch_book, vwap_fill, build_triangles, verify_triangles,
                  build_spot_opportunities, verify_opportunities)

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def fetch_all_tickers():
    fetchers = {"kucoin": fetch_kucoin, "okx": fetch_okx, "gate": fetch_gate,
                "mexc": fetch_mexc, "htx": fetch_htx, "bitfinex": fetch_bitfinex,
                "bitstamp": fetch_bitstamp, "bitget": fetch_bitget,
                "cryptocom": fetch_cryptocom, "kraken": fetch_kraken}
    tickers = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {pool.submit(fn): n for n, fn in fetchers.items()}
        for f in as_completed(futs):
            try:
                tickers.extend(f.result())
            except Exception:
                print(f"[tick] {futs[f]} failed", flush=True)
    try:
        tickers.extend(fetch_coinbase({t["base"] for t in tickers}))
    except Exception:
        traceback.print_exc()
    return tickers


# ---------------- stable-cross loops ----------------

def build_stable_cross(tickers, min_leg_qvol=25_000):
    """X/USDT vs X/USDC on one venue. Loop: USDT -> X (ask X/USDT) ->
    sell X/USDC (bid) -> USDC -> USDT (bid USDC/USDT), and the reverse."""
    by_ex = {}
    for t in tickers:
        by_ex.setdefault(t["ex"], {})[(t["base"], t["quote"])] = t
    out = []
    for ex, pairs in by_ex.items():
        fee = 1 - TAKER_FEE[ex]
        conv = pairs.get(("USDC", "USDT"))
        conv_bid = conv["bid"] if conv else 1.0
        conv_ask = conv["ask"] if conv else 1.0
        conv_legs = 3 if conv else 2  # without a USDC/USDT pair treat 1:1 (2 legs)
        for (base, quote), xt in pairs.items():
            if quote != "USDT" or base in ("USDC",):
                continue
            xc = pairs.get((base, "USDC"))
            if not xc:
                continue
            if xt["qvol"] < min_leg_qvol or xc["qvol"] < min_leg_qvol:
                continue
            f = fee ** conv_legs
            # loop A: USDT -> buy X against USDT -> sell X against USDC -> USDC -> USDT
            mult_a = (1 / xt["ask"]) * xc["bid"] * conv_bid * f
            # loop B: USDT -> USDC -> buy X against USDC -> sell X against USDT
            mult_b = (1 / conv_ask) * (1 / xc["ask"]) * xt["bid"] * f
            for mult, path in ((mult_a, f"USDT->{base}->USDC->USDT"),
                               (mult_b, f"USDT->USDC->{base}->USDT")):
                net = (mult - 1) * 100
                if net > -0.4:
                    out.append({
                        "ex": ex, "path": path, "asset": base,
                        "net_pct": round(net, 4),
                        "legs": conv_legs,
                        "usdt_pair_qvol": round(xt["qvol"]),
                        "usdc_pair_qvol": round(xc["qvol"]),
                    })
    out.sort(key=lambda o: -o["net_pct"])
    return out


def verify_stable_cross(loops, tickers, top_n=12, notional=1000):
    sym = {(t["ex"], t["base"], t["quote"]): t["sym"] for t in tickers}

    def one(lp):
        try:
            ex, base = lp["ex"], lp["asset"]
            fee = 1 - TAKER_FEE[ex]
            xt = fetch_book(ex, sym[(ex, base, "USDT")])
            xc = fetch_book(ex, sym[(ex, base, "USDC")])
            conv = sym.get((ex, "USDC", "USDT"))
            cb = fetch_book(ex, conv) if conv else None
            if lp["path"].startswith("USDT->" + base):
                v1, _ = vwap_fill(xt["asks"], notional)
                x_amt = notional / v1
                v2, _ = vwap_fill(xc["bids"], x_amt * xc["bids"][0][0])
                usdc = x_amt * v2
                if cb:
                    v3, _ = vwap_fill(cb["bids"], usdc * cb["bids"][0][0])
                    end = usdc * v3 * fee ** 3
                else:
                    end = usdc * fee ** 2
            else:
                if cb:
                    v1, _ = vwap_fill(cb["asks"], notional)
                    usdc = notional / v1
                    fees = fee ** 3
                else:
                    usdc = notional
                    fees = fee ** 2
                v2, _ = vwap_fill(xc["asks"], usdc)
                x_amt = usdc / v2
                v3, _ = vwap_fill(xt["bids"], x_amt * xt["bids"][0][0])
                end = x_amt * v3 * fees
            lp["verified"] = {"status": "ok", "net_pct": round((end / notional - 1) * 100, 4)}
        except Exception as e:
            lp["verified"] = {"status": f"error: {type(e).__name__}"}

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(one, loops[:top_n]))


# ---------------- inventory loops ----------------

import requests as _rq

CHAIN_ALIAS = {"ERC20": "ETH", "ETHEREUM": "ETH", "BEP20": "BSC", "BEP20(BSC)": "BSC",
               "BNB SMART CHAIN": "BSC", "TRC20": "TRX", "TRON": "TRX", "SPL": "SOL",
               "SOLANA": "SOL", "ARBITRUM ONE": "ARB", "ARBITRUMONE": "ARB",
               "MATIC": "POL", "POLYGON": "POL", "POLYGON POS": "POL"}


def _canon(name):
    n = (name or "").strip().upper()
    return CHAIN_ALIAS.get(n, n)


def fetch_chain_maps():
    """currency -> {chain: (withdraw_ok, deposit_ok)} for venues that publish it."""
    maps = {}
    try:
        g = {}
        for c in _rq.get("https://api.gateio.ws/api/v4/spot/currencies", timeout=25).json():
            for ch in c.get("chains") or []:
                g.setdefault(c["currency"], {})[_canon(ch.get("name"))] = (
                    not ch.get("withdraw_disabled", True), not ch.get("deposit_disabled", True))
        maps["gate"] = g
    except Exception:
        pass
    try:
        k = {}
        for c in _rq.get("https://api.kucoin.com/api/v3/currencies", timeout=25).json()["data"]:
            for ch in c.get("chains") or []:
                k.setdefault(c["currency"], {})[_canon(ch.get("chainName"))] = (
                    bool(ch.get("isWithdrawEnabled")), bool(ch.get("isDepositEnabled")))
        maps["kucoin"] = k
    except Exception:
        pass
    try:
        h = {}
        for c in _rq.get("https://api.huobi.pro/v2/reference/currencies", timeout=25).json()["data"]:
            for ch in c.get("chains") or []:
                h.setdefault(c["currency"].upper(), {})[_canon(ch.get("displayName") or ch.get("chain"))] = (
                    ch.get("withdrawStatus") == "allowed", ch.get("depositStatus") == "allowed")
        maps["htx"] = h
    except Exception:
        pass
    try:
        b = {}
        for c in _rq.get("https://api.bitget.com/api/v2/spot/public/coins", timeout=25).json()["data"]:
            for ch in c.get("chains") or []:
                b.setdefault(c["coin"], {})[_canon(ch.get("chain"))] = (
                    ch.get("withdrawable") == "true", ch.get("rechargeable") == "true")
        maps["bitget"] = b
    except Exception:
        pass
    return maps


def rebalance_path(chain_maps, asset, buy_ex, sell_ex):
    """Is there a chain where buy venue can WITHDRAW and sell venue can DEPOSIT?"""
    src = chain_maps.get(buy_ex, {}).get(asset)
    dst = chain_maps.get(sell_ex, {}).get(asset)
    if src is None or dst is None:
        return "unverified"
    open_chains = [ch for ch, (wd, _) in src.items() if wd and dst.get(ch, (False, False))[1]]
    return "open via " + "/".join(sorted(open_chains)) if open_chains else "NO COMMON OPEN CHAIN"


def build_inventory_loops(tickers, chain_maps):
    """Cross-venue spreads executable as simultaneous buy/sell with
    pre-positioned inventory. Rebalance needs a common chain with the
    buy side's withdrawal AND the sell side's deposit both open."""
    opps = build_spot_opportunities(tickers, min_qvol=100_000)
    verify_opportunities(opps, tickers, top_n=30, notional=2000)
    loops = []
    for o in opps[:30]:
        v = o.get("verified") or {}
        if v.get("status") != "ok" or v["net_pct"] <= 0:
            continue
        o["rebalance"] = rebalance_path(chain_maps, o["asset"], o["buy_ex"], o["sell_ex"])
        if o["rebalance"].startswith("open"):
            loops.append(o)
    return loops, opps


def main():
    t0 = time.time()
    print("[1/4] fetching fresh tickers...", flush=True)
    tickers = fetch_all_tickers()
    print(f"  {len(tickers)} tickers", flush=True)

    print("[2/4] stable-cross loops (X/USDT vs X/USDC, same venue)...", flush=True)
    sc = build_stable_cross(tickers)
    verify_stable_cross(sc, tickers)

    print("[3/4] BTC/ETH triangles...", flush=True)
    tris = build_triangles(tickers)
    verify_triangles(tris, tickers, top_n=10)

    print("[4/4] inventory loops (common-chain rebalance check)...", flush=True)
    chain_maps = fetch_chain_maps()
    inv, all_opps = build_inventory_loops(tickers, chain_maps)

    result = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stable_cross": sc[:60],
        "triangles": tris[:30],
        "inventory_loops": inv,
        "top_spreads_all": [
            {k: o[k] for k in ("asset", "quote", "buy_ex", "sell_ex", "net_pct",
                               "verified", "transfer_notes", "rebalance") if k in o}
            for o in all_opps[:30]],
    }
    with open(os.path.join(D, "instant_loops.json"), "w") as f:
        json.dump(result, f, indent=1)

    print(f"\nDone in {time.time()-t0:.0f}s\n")
    print("=== STABLE-CROSS LOOPS (same venue, seconds per cycle) ===")
    for lp in sc[:15]:
        v = lp.get("verified") or {}
        vt = f"verified {v['net_pct']:+.3f}%" if v.get("status") == "ok" else v.get("status", "")
        print(f"  [{lp['ex']:9s}] {lp['path']:32s} ticker {lp['net_pct']:+.3f}% | {vt} "
              f"(vols ${lp['usdt_pair_qvol']:,}/${lp['usdc_pair_qvol']:,})")
    print("\n=== TRIANGLES (top) ===")
    for tr in tris[:6]:
        v = tr.get("verified") or {}
        vt = f"verified {v['net_pct']:+.3f}%" if v.get("status") == "ok" else v.get("status", "")
        print(f"  [{tr['ex']:9s}] {tr['path']:32s} ticker {tr['net_pct']:+.3f}% | {vt}")
    print("\n=== INVENTORY LOOPS (simultaneous 2-venue, rebalance open) ===")
    for o in inv:
        v = o["verified"]
        print(f"  {o['asset']}/{o['quote']} buy {o['buy_ex']} sell {o['sell_ex']}: "
              f"verified {v['net_pct']:+.2f}% (${v['fill_usd']} per cycle) rebalance={o['rebalance']}")
    if not inv:
        print("  (none pass all gates right now)")


if __name__ == "__main__":
    main()
