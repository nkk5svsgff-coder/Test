#!/usr/bin/env python3
"""Instantly-repeatable neg-risk conversion arbs on Polymarket.

Mechanism: in a neg-risk (mutually exclusive) event with n outcomes, a
complete set of NO tokens (one per outcome) is convertible to $(n-1) USDC
immediately via the NegRiskAdapter - no waiting for resolution. On the
CLOB, NO_ask(i) = 1 - YES_bid(i) exactly (complementary shared book), so:

    cost of NO set  = n - sum(YES bids)
    instant payout  = n - 1
    profit per set  = sum(YES bids) - 1     when sum > $1

Cycle: hit the asks (operator-relayed, no gas), convert (one Polygon tx,
cents), collect USDC, repeat while makers keep the bids there.

Verifies candidates against live CLOB depth. Writes data/negrisk_instant.json.
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
S = requests.Session()
S.headers.update({"User-Agent": "arb-research/1.0"})


def get_json(url, **kw):
    kw.setdefault("timeout", 25)
    r = S.get(url, **kw)
    r.raise_for_status()
    return r.json()


def fetch_candidates(min_sum=1.004):
    events = []
    for off in range(0, 2000, 100):
        batch = get_json("https://gamma-api.polymarket.com/events",
                         params={"closed": "false", "limit": 100, "offset": off,
                                 "order": "volume24hr", "ascending": "false"})
        if not batch:
            break
        events.extend(batch)
        if len(batch) < 100:
            break
    out = []
    for ev in events:
        if not ev.get("negRisk"):
            continue
        ms = [m for m in (ev.get("markets") or []) if not m.get("closed")]
        if len(ms) < 2:
            continue
        bids, tokens, ok = [], [], True
        for m in ms:
            try:
                bids.append(float(m["bestBid"]))
                tokens.append(json.loads(m["clobTokenIds"])[0])   # YES token id
            except (KeyError, TypeError, ValueError, IndexError):
                ok = False
                break
        if not ok or sum(bids) < min_sum:
            continue
        out.append({"title": ev.get("title"), "slug": ev.get("slug"),
                    "n": len(ms), "sum_bid_gamma": round(sum(bids), 4),
                    "questions": [m.get("question") for m in ms],
                    "yes_tokens": tokens,
                    "vol24h": ev.get("volume24hr")})
    out.sort(key=lambda e: (e["sum_bid_gamma"] - 1) / (e["n"] - e["sum_bid_gamma"]), reverse=True)
    return out


def verify_event(ev):
    """Live CLOB books for every outcome's YES token: best bid + size."""
    def one(tid):
        try:
            book = get_json("https://clob.polymarket.com/book", params={"token_id": tid})
            bids = sorted(book.get("bids", []), key=lambda x: -float(x["price"]))
            if not bids:
                return None
            return float(bids[0]["price"]), float(bids[0]["size"])
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        tops = list(pool.map(one, ev["yes_tokens"]))
    if any(t is None for t in tops):
        ev["live"] = {"status": "book_unavailable"}
        return ev
    s = sum(p for p, _ in tops)
    sets_at_top = min(sz for _, sz in tops)
    edge = s - 1.0
    capital = ev["n"] - s
    ev["live"] = {
        "status": "ok",
        "sum_bid_live": round(s, 4),
        "edge_per_set": round(edge, 4),
        "capital_per_set": round(capital, 4),
        "ret_pct": round(edge / capital * 100, 3),
        "sets_at_best_bid": round(sets_at_top, 1),
        "profit_at_best_depth": round(edge * sets_at_top, 2),
        "weakest_bid": min(tops)[0],
    }
    return ev


def main():
    t0 = time.time()
    print("[1/2] gamma sweep for neg-risk sum(YES bids) > $1...", flush=True)
    cands = fetch_candidates()
    print(f"  {len(cands)} candidates", flush=True)
    print("[2/2] verifying live CLOB books (every outcome, real depth)...", flush=True)
    verified = [verify_event(e) for e in cands[:14]]

    result = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "candidates": len(cands), "verified": verified}
    with open(os.path.join(D, "negrisk_instant.json"), "w") as f:
        json.dump(result, f, indent=1)

    print(f"\nDone in {time.time()-t0:.0f}s - live instantly-repeatable conversion arbs:\n")
    for e in verified:
        lv = e["live"]
        if lv.get("status") != "ok" or lv["edge_per_set"] <= 0.002:
            tag = lv.get("status") if lv.get("status") != "ok" else f"gone live (sum {lv['sum_bid_live']})"
            print(f"  [dead] {e['title'][:58]:58s} {tag}")
            continue
        print(f"  [LIVE] {e['title'][:58]:58s} n={e['n']:2d} sum_bid={lv['sum_bid_live']:.3f} "
              f"edge ${lv['edge_per_set']:.3f}/set ({lv['ret_pct']:.2f}%) "
              f"x {lv['sets_at_best_bid']:.0f} sets at top = ${lv['profit_at_best_depth']:.2f}/cycle")


if __name__ == "__main__":
    main()
