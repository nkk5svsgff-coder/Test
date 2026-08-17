#!/usr/bin/env python3
"""Re-analyse the cached pricing corpus with numeric validation.

Stricter than the first pass: to call a site "Yes" we now require evidence
that the SECOND price is actually HIGHER than the first (a real step-up),
that the first payment is not zero/free, and that free-trial wording is not
sitting between the two prices.

Reads data/pricing_corpus.jsonl.gz (no re-crawling) and writes
data/pricing_final.jsonl.
"""

import gzip
import json
import os
import re

import scan_pricing as sp

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

PRICE_RX = re.compile(sp.PRICE, re.I)
NUM_RX = re.compile(r"\d[\d.,]*")
FREE_NEAR = re.compile(
    rf"(?:{sp.FREEWORD})\s*(?:for\s+)?(?:\d{{1,2}}\s*)?(?:{sp.PERIOD}|trial|prueba|essai|prova|test|deneme)"
    rf"|\d{{1,2}}[\s-]*{sp.PERIOD}s?\s*(?:for\s+)?(?:{sp.FREEWORD})"      # "3 days free"
    rf"|\b(?:try|start|get|enjoy|test)\b[^.<>]{{0,24}}?(?:{sp.FREEWORD})"  # "Try ... free"
    rf"|(?:{sp.FREEWORD})\s*(?:,|\.|-|—)?\s*(?:then|danach|luego|puis|depois|daarna)", re.I)
TRIAL_WORD = re.compile(r"\b(?:free trial|trial|gratis|kostenlos|gratuit|gr[aá]tis)\b", re.I)
DATE_RX = re.compile(r"\d{1,2}[/.]\d{1,2}[/.]\d{2,4}")
PCT_OFF = re.compile(r"\d{1,3}\s?%\s*(?:off|de descuento|rabatt|r[ée]duction|desconto|di sconto|korting)", re.I)


def amount(tok):
    """Parse '€1.234,56' / '$1,234.56' / '9.99' -> float."""
    m = NUM_RX.search(tok)
    if not m:
        return None
    s = m.group(0)
    if "." in s and "," in s:
        s = s.replace("." if s.rfind(",") > s.rfind(".") else ",", "")
        s = s.replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".") if re.search(r",\d{1,2}$", s) else s.replace(",", "")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def judge_window(w):
    """Return (tier, label, snippet) for one price-context window."""
    best = None
    for rx, label in sp.A_PATTERNS:
        for m in rx.finditer(w):
            seg = m.group(0)
            pre = w[max(0, m.start() - 130):m.start()]
            snip = re.sub(r"\s+", " ", seg)[:190]
            if DATE_RX.search(seg):        # narrative text with dates, not an offer
                continue
            toks = PRICE_RX.findall(seg) or []
            vals = [v for v in (amount(t) for t in toks) if v is not None]

            # free-trial guard: 'free ... trial/period' inside the match or right before it
            if FREE_NEAR.search(seg) or FREE_NEAR.search(pre[-70:]):
                if not (len(vals) >= 2 and vals[0] > 0 and vals[-1] > vals[0] * 1.05):
                    continue

            if label == "renews at <price>":
                # needs a cheaper price nearby to prove the first term was discounted
                pre_vals = [v for v in (amount(t) for t in PRICE_RX.findall(pre)) if v]
                if vals and pre_vals and min(pre_vals) < vals[-1] * 0.95 and min(pre_vals) > 0:
                    return "Yes", label + " (after a lower intro price)", snip
                best = best or ("Likely", label + " (auto-renewal price stated)", snip)
                continue

            if label == "% off first period, then <price>" or PCT_OFF.search(seg):
                return "Yes", label, snip

            if len(vals) >= 2:
                first, last = vals[0], vals[-1]
                if first > 0 and 1.05 < last / first <= 60:
                    return "Yes", label + f" ({first:g} -> {last:g})", snip
                if first > 0 and abs(last - first) < 0.01:
                    continue          # same price restated: not a step-up
                best = best or ("Likely", label + " (prices not clearly stepping up)", snip)
            elif vals:
                best = best or ("Likely", label, snip)

    if best:
        return best
    for rx, label in sp.B_PATTERNS:
        m = rx.search(w)
        if m:
            seg = m.group(0)
            pre = w[max(0, m.start() - 130):m.start()]
            if FREE_NEAR.search(seg) or FREE_NEAR.search(pre[-70:]):
                continue
            return "Likely", label, re.sub(r"\s+", " ", seg)[:190]
    return None, None, None


def main():
    live = {}
    with open(os.path.join(D, "pricing.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            live[r["url"]] = r

    out, counts = [], {"Yes": 0, "Likely": 0, "No": 0, "Unknown": 0}
    with gzip.open(os.path.join(D, "pricing_corpus.jsonl.gz"), "rt") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            url = rec["url"]
            base = live.get(url, {})
            tier, label, snip, where = None, None, None, base.get("found_on", "")
            for w in rec.get("w", []):
                t, lab, sn = judge_window(w)
                if t == "Yes":
                    tier, label, snip = t, lab, sn
                    break
                if t == "Likely" and tier is None:
                    tier, label, snip = t, lab, sn
            if tier is None:
                v = base.get("verdict", "No")
                tier = "Unknown" if v == "Unknown" else "No"
                label = snip = ""
            counts[tier] = counts.get(tier, 0) + 1
            out.append({"url": url, "verdict": tier,
                        "evidence": (f'{label}: "{snip}"' if snip else ""),
                        "free_trial": base.get("free_trial", False),
                        "status": base.get("status", ""), "found_on": where})

    with open(os.path.join(D, "pricing_final.jsonl"), "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    print("counts:", counts, "of", len(out))


if __name__ == "__main__":
    main()
