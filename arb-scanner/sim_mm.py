#!/usr/bin/env python3
"""Live paper-trading simulator for maker spread-capture.

Posts simulated $NOTIONAL bid+ask at the touch on real books, observes the
real trade tape, and fills quotes only when actual prints cross them:
  - conservative rule: price trades STRICTLY THROUGH our level
  - optimistic rule: printed volume AT our level exceeds the queue that was
    ahead of us when we posted
After a fill that side requotes at the current touch. Inventory is marked
to mid at the end. No orders are ever sent anywhere - observation only.

Usage: python3 sim_mm.py <minutes>
Writes data/sim_mm_result.json.
"""

import json
import os
import sys
import time
import traceback

import requests

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
S = requests.Session()
S.headers.update({"User-Agent": "arb-research/1.0"})
NOTIONAL = 100.0   # USD per quote side


def kucoin_book(sym):
    d = S.get(f"https://api.kucoin.com/api/v1/market/orderbook/level2_20?symbol={sym}", timeout=15).json()["data"]
    return (float(d["bids"][0][0]), float(d["bids"][0][1]),
            float(d["asks"][0][0]), float(d["asks"][0][1]))


def kucoin_trades(sym):
    d = S.get(f"https://api.kucoin.com/api/v1/market/histories?symbol={sym}", timeout=15).json()["data"]
    return [(int(t["time"]), float(t["price"]), float(t["size"])) for t in d]


def mexc_book(sym):
    d = S.get(f"https://api.mexc.com/api/v3/depth?symbol={sym}&limit=5", timeout=15).json()
    return (float(d["bids"][0][0]), float(d["bids"][0][1]),
            float(d["asks"][0][0]), float(d["asks"][0][1]))


def mexc_trades(sym):
    d = S.get(f"https://api.mexc.com/api/v3/trades?symbol={sym}&limit=100", timeout=15).json()
    return [(int(t["time"]) * 10**6, float(t["price"]), float(t["qty"])) for t in d]


BOOKS = {
    ("kucoin", "ACT-USDT"): (kucoin_book, kucoin_trades, 0.001),   # maker fee/side
    ("mexc", "ZAYUSDT"): (mexc_book, mexc_trades, 0.0),
    ("mexc", "XPLKUSDT"): (mexc_book, mexc_trades, 0.0),
}


class SimBook:
    def __init__(self, venue, sym, book_fn, trades_fn, maker_fee):
        self.venue, self.sym = venue, sym
        self.book_fn, self.trades_fn, self.fee = book_fn, trades_fn, maker_fee
        self.seen = set()
        self.quotes = {}          # side -> dict(px, qty, queue_ahead, at_level_vol)
        self.pos = {"cons": 0.0, "opt": 0.0}      # base inventory per rule
        self.cash = {"cons": 0.0, "opt": 0.0}
        self.fills = {"cons": [], "opt": []}
        self.mid = None
        self.polls = self.errors = 0

    def requote(self, bb, bq, ba, aq):
        base_qty = NOTIONAL / ((bb + ba) / 2)
        for side, px, queue in (("bid", bb, bq), ("ask", ba, aq)):
            q = self.quotes.get(side)
            if q is None or q["done_cons"] and q["done_opt"]:
                self.quotes[side] = {"px": px, "qty": base_qty, "queue": queue * px,
                                     "at_level": 0.0, "done_cons": False, "done_opt": False}

    def fill(self, rule, side, px, qty):
        sign = 1 if side == "bid" else -1
        self.pos[rule] += sign * qty
        self.cash[rule] -= sign * qty * px
        self.cash[rule] -= qty * px * self.fee
        self.fills[rule].append({"t": time.time(), "side": side, "px": px})

    def step(self):
        try:
            bb, bq, ba, aq = self.book_fn(self.sym)
            self.mid = (bb + ba) / 2
            trades = self.trades_fn(self.sym)
            self.polls += 1
        except Exception:
            self.errors += 1
            return
        new = [t for t in trades if t not in self.seen]
        self.seen.update(trades)
        if len(self.seen) > 20000:
            self.seen = set(trades)
        for _, px, sz in sorted(new):
            for side, cmp_through, cmp_at in (("bid", lambda p, q: p < q, lambda p, q: p == q),
                                              ("ask", lambda p, q: p > q, lambda p, q: p == q)):
                q = self.quotes.get(side)
                if not q:
                    continue
                if not q["done_cons"] and cmp_through(px, q["px"]):
                    self.fill("cons", side, q["px"], q["qty"]); q["done_cons"] = True
                if not q["done_opt"]:
                    if cmp_through(px, q["px"]):
                        self.fill("opt", side, q["px"], q["qty"]); q["done_opt"] = True
                    elif cmp_at(px, q["px"]):
                        q["at_level"] += sz * px
                        if q["at_level"] > q["queue"]:
                            self.fill("opt", side, q["px"], q["qty"]); q["done_opt"] = True
        self.requote(bb, bq, ba, aq)

    def result(self, minutes):
        out = {"venue": self.venue, "symbol": self.sym, "minutes": minutes,
               "polls": self.polls, "errors": self.errors, "mid_final": self.mid}
        for rule in ("cons", "opt"):
            mtm = self.cash[rule] + self.pos[rule] * (self.mid or 0)
            buys = sum(1 for f in self.fills[rule] if f["side"] == "bid")
            sells = len(self.fills[rule]) - buys
            out[rule] = {"fills": len(self.fills[rule]), "buys": buys, "sells": sells,
                         "round_trips": min(buys, sells),
                         "inventory_base": round(self.pos[rule], 6),
                         "inventory_usd": round(self.pos[rule] * (self.mid or 0), 2),
                         "pnl_usd_marked": round(mtm, 4),
                         "pnl_per_hour": round(mtm / minutes * 60, 4)}
        return out


def main():
    minutes = float(sys.argv[1]) if len(sys.argv) > 1 else 10
    sims = [SimBook(v, s, *fns) for (v, s), fns in BOOKS.items()]
    t_end = time.time() + minutes * 60
    # prime the tape so pre-existing trades don't count
    for sb in sims:
        try:
            sb.seen.update(sb.trades_fn(sb.sym))
            bb, bq, ba, aq = sb.book_fn(sb.sym)
            sb.mid = (bb + ba) / 2
            sb.requote(bb, bq, ba, aq)
        except Exception:
            traceback.print_exc()
    while time.time() < t_end:
        for sb in sims:
            sb.step()
        time.sleep(5)
    results = [sb.result(minutes) for sb in sims]
    with open(os.path.join(D, "sim_mm_result.json"), "w") as f:
        json.dump({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "notional_per_side_usd": NOTIONAL, "results": results}, f, indent=1)
    for r in results:
        print(f"{r['venue']} {r['symbol']}: polls {r['polls']} (errors {r['errors']})")
        for rule in ("cons", "opt"):
            x = r[rule]
            print(f"  [{rule:4s}] fills {x['fills']} (rt {x['round_trips']}) "
                  f"inv ${x['inventory_usd']} pnl ${x['pnl_usd_marked']} (${x['pnl_per_hour']}/h)")


if __name__ == "__main__":
    main()
