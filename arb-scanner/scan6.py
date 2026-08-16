#!/usr/bin/env python3
"""Out-of-the-box sector scanner - markets entirely outside crypto exchange
spot/derivatives and prediction markets:

  1. P2P fiat corridors: USDT price in emerging-market currencies (OKX P2P
     books) vs official FX - capital-controls premiums/discounts.
  2. DeFi lending-rate arbitrage: borrow asset X cheaply on protocol A,
     lend the same asset on protocol B at a higher rate. Instant, on-chain,
     continuously repeatable carry.
  3. CS2 skins price surface: Skinport market prices vs suggested (Steam)
     prices - measures the gaming-items liquidation discount structure.
  4. NFT floor-vs-offer probe (Magic Eden public stats).

Writes data/new_sectors.json.
"""

import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import requests

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) arb-research/1.0"})


def get_json(url, **kw):
    kw.setdefault("timeout", 30)
    r = S.get(url, **kw)
    r.raise_for_status()
    return r.json()


# ---------------- 1. P2P fiat corridors ----------------

P2P_CCYS = ["ngn", "ars", "ves", "try", "egp", "pkr", "kes", "ghs", "php",
            "vnd", "brl", "cop", "uah", "mad", "bdt", "lkr", "inr", "idr"]


def okx_p2p_book(quote, side):
    """side='sell': merchants selling USDT (your buy price).
    side='buy': merchants buying USDT (your sell price)."""
    d = get_json("https://www.okx.com/v3/c2c/tradingOrders/books",
                 params={"quoteCurrency": quote, "baseCurrency": "usdt",
                         "side": side, "paymentMethod": "all", "userType": "all",
                         "showTrade": "false", "showFollow": "false",
                         "showAlreadyTraded": "false", "isAbleFilter": "false",
                         "t": str(int(time.time() * 1000))})
    offers = (d.get("data") or {}).get(side) or []
    prices = []
    for o in offers[:10]:
        try:
            prices.append(float(o["price"]))
        except (KeyError, ValueError):
            pass
    if not prices:
        return None, 0
    prices.sort()
    return prices[len(prices) // 2], len(offers)   # median of top-of-book


def scan_p2p():
    fx = get_json("https://open.er-api.com/v6/latest/USD")["rates"]
    rows = []
    for ccy in P2P_CCYS:
        official = fx.get(ccy.upper())
        if not official:
            continue
        try:
            buy_px, n_sell = okx_p2p_book(ccy, "sell")   # you buy USDT at this
            time.sleep(0.4)
            sell_px, n_buy = okx_p2p_book(ccy, "buy")    # you sell USDT at this
            time.sleep(0.4)
        except Exception:
            continue
        if not buy_px or not sell_px:
            continue
        rows.append({
            "currency": ccy.upper(), "official_fx": official,
            "p2p_buy_usdt": buy_px, "p2p_sell_usdt": sell_px,
            "buy_premium_pct": round((buy_px / official - 1) * 100, 2),
            "sell_premium_pct": round((sell_px / official - 1) * 100, 2),
            "onramp_offramp_spread_pct": round((sell_px / buy_px - 1) * 100, 2),
            "offers": n_sell + n_buy,
        })
    rows.sort(key=lambda r: -abs(r["sell_premium_pct"]))
    return rows


# ---------------- 2. DeFi lending-rate arbitrage ----------------

def scan_defi_lending(min_supply_tvl=3_000_000, min_borrow_avail=1_000_000):
    pools = get_json("https://yields.llama.fi/pools")["data"]
    borrow = get_json("https://yields.llama.fi/lendBorrow")
    binfo = {b["pool"]: b for b in borrow}

    supply_side, borrow_side = {}, {}
    for p in pools:
        sym, chain = (p.get("symbol") or "").upper(), p.get("chain")
        if not sym or "-" in sym:           # skip LP tokens
            continue
        key = (chain, sym)
        apy = p.get("apy") or 0
        if (p.get("tvlUsd") or 0) >= min_supply_tvl and apy > 0:
            cur = supply_side.get(key)
            if not cur or apy > cur["apy"]:
                supply_side[key] = {"apy": apy, "project": p["project"],
                                    "tvl": p["tvlUsd"], "pool": p["pool"]}
        b = binfo.get(p.get("pool"))
        if b and b.get("borrowable"):
            net_borrow = (b.get("apyBaseBorrow") or 0) - (b.get("apyRewardBorrow") or 0)
            avail = (b.get("totalSupplyUsd") or 0) - (b.get("totalBorrowUsd") or 0)
            if avail >= min_borrow_avail:
                cur = borrow_side.get(key)
                if not cur or net_borrow < cur["apy"]:
                    borrow_side[key] = {"apy": net_borrow, "project": p["project"],
                                        "avail": avail, "ltv": b.get("ltv")}
    rows = []
    for key in supply_side.keys() & borrow_side.keys():
        s, b = supply_side[key], borrow_side[key]
        if s["project"] == b["project"]:
            continue
        spread = s["apy"] - b["apy"]
        if spread <= 0.5:
            continue
        rows.append({
            "chain": key[0], "asset": key[1],
            "borrow_on": b["project"], "borrow_apy_pct": round(b["apy"], 2),
            "borrow_avail_usd": round(b["avail"]),
            "lend_on": s["project"], "supply_apy_pct": round(s["apy"], 2),
            "supply_tvl_usd": round(s["tvl"]),
            "spread_pct_yr": round(spread, 2),
            "max_ltv": b.get("ltv"),
        })
    rows.sort(key=lambda r: -r["spread_pct_yr"])
    return rows


# ---------------- 3. CS2 skins surface ----------------

def scan_skins():
    r = S.get("https://api.skinport.com/v1/items",
              params={"app_id": 730, "currency": "USD"},
              headers={"Accept-Encoding": "br"}, timeout=40)
    r.raise_for_status()
    items = r.json()
    rows = []
    for it in items:
        mn, sug, qty = it.get("min_price"), it.get("suggested_price"), it.get("quantity") or 0
        if not mn or not sug or qty < 20 or mn < 5:
            continue
        disc = (1 - mn / sug) * 100
        if disc > 15:
            rows.append({
                "item": it["market_hash_name"], "skinport_min": mn,
                "steam_suggested": sug, "discount_pct": round(disc, 1),
                "listings": qty,
            })
    rows.sort(key=lambda r: -r["discount_pct"])
    return rows[:25], len(items)


# ---------------- 4. NFT probe ----------------

def scan_nft():
    out = []
    for sym in ["mad_lads", "okay_bears", "tensorians", "claynosaurz", "froganas"]:
        try:
            st = get_json(f"https://api-mainnet.magiceden.dev/v2/collections/{sym}/stats")
            out.append({"collection": sym,
                        "floor_sol": (st.get("floorPrice") or 0) / 1e9,
                        "listed": st.get("listedCount"),
                        "vol24h_sol": (st.get("volume24hr") or 0) / 1e9})
            time.sleep(0.3)
        except Exception:
            pass
    return out


def main():
    t0 = time.time()
    res = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    print("[1/4] P2P fiat corridors (OKX P2P vs official FX)...", flush=True)
    try:
        res["p2p_corridors"] = scan_p2p()
    except Exception:
        traceback.print_exc(); res["p2p_corridors"] = []

    print("[2/4] DeFi lending-rate spreads (DefiLlama)...", flush=True)
    try:
        res["defi_lending"] = scan_defi_lending()
    except Exception:
        traceback.print_exc(); res["defi_lending"] = []

    print("[3/4] CS2 skins surface (Skinport)...", flush=True)
    try:
        res["skins"], res["skins_universe"] = scan_skins()
    except Exception:
        traceback.print_exc(); res["skins"] = []

    print("[4/4] NFT floors (Magic Eden)...", flush=True)
    res["nft"] = scan_nft()

    with open(os.path.join(D, "new_sectors.json"), "w") as f:
        json.dump(res, f, indent=1)

    print(f"\nDone in {time.time()-t0:.0f}s\n")
    print("=== P2P CORRIDORS (USDT vs official FX) ===")
    for r in res["p2p_corridors"]:
        print(f"  {r['currency']}: official {r['official_fx']:.2f} | buy USDT {r['buy_premium_pct']:+.1f}% "
              f"| sell USDT {r['sell_premium_pct']:+.1f}% | in-country roundtrip {r['onramp_offramp_spread_pct']:+.2f}% ({r['offers']} offers)")
    print("\n=== DEFI LENDING SPREADS (borrow low / lend high, same asset+chain) ===")
    for r in res["defi_lending"][:15]:
        print(f"  [{r['chain']:10s}] {r['asset']:8s} borrow {r['borrow_on']:18s} {r['borrow_apy_pct']:5.2f}% -> "
              f"lend {r['lend_on']:18s} {r['supply_apy_pct']:5.2f}%  spread {r['spread_pct_yr']:+.2f}%/yr "
              f"(avail ${r['borrow_avail_usd']:,}, tvl ${r['supply_tvl_usd']:,})")
    print("\n=== SKINS: deepest Skinport discounts vs Steam suggested ===")
    for r in res["skins"][:8]:
        print(f"  {r['discount_pct']:5.1f}% off  ${r['skinport_min']:8.2f} vs ${r['steam_suggested']:8.2f}  x{r['listings']}  {r['item'][:50]}")


if __name__ == "__main__":
    main()
