# Digital Arbitrage Scanner

Live scanner for purely digital, instant-execution arbitrage opportunities.
No API keys needed — public endpoints only.

## What it scans

| Class | Sources | Method |
|---|---|---|
| Cross-exchange spot spreads | Kraken, Coinbase, KuCoin, OKX, Gate, MEXC, HTX, Bitfinex, Bitstamp, Bitget, Crypto.com (~9,500 pairs) | Executable spread: buy at venue A's ask, sell at venue B's bid, net of base-tier taker fees; ≥$150k 24h volume both sides |
| Order-book verification | Depth-20 books on all 11 venues | Re-checks top spreads minutes later with VWAP fills for $2k/leg — kills stale-ticker mirages |
| Transfer status | Gate, KuCoin, HTX, Bitget public currency endpoints | Flags spreads that persist only because a deposit/withdrawal leg is suspended |
| Triangular cycles | Same 11 venues, BTC/ETH cross pairs | stable→X→BTC/ETH→stable both directions, 3 taker fees, depth-verified |
| Perp funding carry | Gate + Bitget (all USDT perps), OKX (majors) | Annualized funding; delta-neutral carry direction per sign |
| Prediction markets | Polymarket (neg-risk events), Kalshi (mutually-exclusive events) | Robust arb: sum of YES bids > $1 (buy NO on all outcomes); conditional: sum of YES asks < $1 |

## Run

```
python3 scan.py     # ~40s: writes data/merged_tickers.json + data/opportunities.json
python3 report.py   # builds data/report.md + data/opportunities.csv (top 100)
```

Run `scan.py` twice (keeping a copy of the first `opportunities.json` as
`opportunities_run1.json`) to get persistence tags in the report.

## Honest caveats baked into the output

- Ticker-level spreads are usually mirages: stale bulk-ticker data (HTX especially)
  showed +6.9% "spreads" that verified to −28% against live books.
- Big verified spreads persist for a reason — every >1% verified spread found had a
  suspended deposit/withdrawal leg (e.g. ZEC on HTX: withdrawals off, price trapped ~4% low).
- Same ticker ≠ same token across exchanges; verify contract addresses before wiring funds.
- Binance and Bybit are geo-blocked from this runner's location and are not covered.
- Fees assume base-tier taker; withdrawal fees and transfer latency are not netted out
  of cross-exchange rows.
