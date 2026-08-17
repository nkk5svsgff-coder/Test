#!/usr/bin/env python3
"""Detect introductory-discount pricing that auto-renews at a higher price.

TARGET pattern (what the user wants flagged "Yes"):
    "$5 for the first month, then $29/month"
    "1 week for EUR 1.99, then EUR 9.99/week"
    "50% off your first year - renews at $99/yr"
    i.e. a PAID discounted first payment that automatically rebills higher.

NOT the target:
    free trials ("free for 30 days, then $12") -> tracked separately as
    "free trial" and NOT counted as Yes,
    plain one-off discounts with no renewal ("20% off today"),
    lifetime deals.

Crawls homepage + up to 4 pricing/checkout pages, extracts the text around
every price token, and matches tiered patterns. Caches the price context
per site (gzipped) so the corpus can be re-analysed without re-crawling.
"""

import gzip
import html as htmllib
import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

import detect

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(D, exist_ok=True)

# ---------------- price + phrase vocabulary ----------------
CUR = r"(?:[$€£₹¥]|USD|EUR|GBP|BRL|R\$|PLN|zł|CHF|SEK|NOK|DKK|CZK|Kč|HUF|Ft|RON|lei|TRY|₺|INR|MXN|COP|ARS)"
AMT = r"\d{1,4}(?:[.,]\d{1,2})?"
PRICE = rf"(?:{CUR}\s?{AMT}|{AMT}\s?{CUR})"

PERIOD = r"(?:month|months|mo\b|week|weeks|wk\b|year|years|yr\b|day|days|quarter)"
# multilingual "then / afterwards"
THEN = (r"(?:then|thereafter|after that|afterwards?|afterward|"
        r"danach|anschlie(?:ss|ß)end|dann|"
        r"luego|despu[eé]s|posteriormente|"
        r"puis|ensuite|par la suite|"
        r"poi|successivamente|"
        r"depois|em seguida|ap[oó]s|"
        r"daarna|vervolgens|"
        r"sedan|derefter|deretter|sitten|"
        r"potem|nast[eę]pnie|pot[ée]|"
        r"sonra|затем|потом)")
FIRST = (r"(?:first|1st|initial|introductory|intro|starter|welcome|launch|"
         r"erste[nrs]?|primer[oa]?|premier|prim[oa]|primeiro|eerste|f[oö]rsta|"
         r"pierwszy|ilk|первый)")
RENEW = (r"(?:renew(?:s|al|ing)?|auto[- ]?renew\w*|rebill\w*|recurring|"
         r"verl[aä]ngert|se renueva|renouvelle|si rinnova|renova|verlengt|"
         r"yenilenir|abonelik)")
FREEWORD = r"(?:free|gratis|kostenlos|gratuit|gr[aá]tis|бесплатн|ilmainen|gratuito|0[.,]00)"
# gap that does not cross a sentence end, but DOES tolerate decimal points ("$9.99")
G = r"(?:[^.!?<>]|\.(?=\d))"

# ---- Tier A: conclusive intro-then-higher-price ----
A_PATTERNS = [
    # "$5 for the first month, then $29"
    (re.compile(rf"{PRICE}{G}{{0,70}}?\b{FIRST}\b{G}{{0,50}}?\b{THEN}\b{G}{{0,40}}?{PRICE}", re.I),
     "intro price + first period + then + higher price"),
    # "first month $5, then $29/mo"
    (re.compile(rf"\b{FIRST}\b{G}{{0,40}}?{PRICE}{G}{{0,60}}?\b{THEN}\b{G}{{0,40}}?{PRICE}", re.I),
     "first-period price + then + higher price"),
    # "then $29/month" preceded by a price within the same block
    (re.compile(rf"{PRICE}{G}{{0,90}}?\b{THEN}\b\s*(?:only\s+|just\s+)?{PRICE}\s*(?:/|per\s|a\s|ein\s|por\s)?\s*{PERIOD}", re.I),
     "price ... then <price> per period"),
    # "renews at $99" / "auto-renews at 49.99/yr"
    (re.compile(rf"{RENEW}{G}{{0,30}}?(?:at|for|to|a|em|à)\s*{PRICE}", re.I),
     "renews at <price>"),
    # "$1 for 7 days, then $39.99 every month"
    (re.compile(rf"{PRICE}{G}{{0,40}}?\bfor\b{G}{{0,20}}?\d{{1,3}}\s*{PERIOD}{G}{{0,40}}?\b{THEN}\b{G}{{0,40}}?{PRICE}", re.I),
     "price for N periods, then <price>"),
    # "% off first month ... then/renews <price>"
    (re.compile(rf"\d{{1,3}}\s?%\s*(?:off|de descuento|rabatt|r[ée]duction|desconto){G}{{0,50}}?\b{FIRST}\b{G}{{0,60}}?(?:{THEN}|{RENEW}){G}{{0,40}}?{PRICE}", re.I),
     "% off first period, then <price>"),
    # "introductory price ... regular price $X"
    (re.compile(rf"(?:introductory|intro|promotional|promo|launch)\s+(?:price|rate|offer){G}{{0,80}}?(?:regular|normal|standard|full|list)\s+price{G}{{0,25}}?{PRICE}", re.I),
     "introductory price vs regular price"),
]

# ---- Tier B: strong hints, not conclusive ----
B_PATTERNS = [
    (re.compile(rf"\b{FIRST}\s+{PERIOD}\b{G}{{0,40}}?{PRICE}", re.I), "first-period price stated"),
    (re.compile(rf"(?:introductory|intro|promotional|promo|welcome|launch)\s+(?:price|rate|offer|pricing)", re.I), "introductory/promo price wording"),
    (re.compile(rf"{RENEW}{G}{{0,60}}?(?:regular|normal|standard|full|list)\s+price", re.I), "renews at regular price"),
    (re.compile(rf"(?:regular|normal|standard|full|list)\s+price{G}{{0,25}}?{PRICE}{G}{{0,60}}?{RENEW}", re.I), "regular price + renewal"),
    (re.compile(rf"\bprice\s+(?:will\s+)?(?:increase|go(?:es)? up|rise){G}{{0,40}}?{PRICE}", re.I), "price increases to <price>"),
    (re.compile(rf"\b{THEN}\b\s*(?:only\s+|just\s+)?{PRICE}\s*(?:/|per\s|a\s)?\s*{PERIOD}", re.I), "then <price> per period"),
    (re.compile(rf"(?:billed|charged)\s+{PRICE}\s+(?:after|from)\s+(?:the\s+)?(?:first|1st|second|2nd|next)", re.I), "billed <price> after first term"),
]

# free-trial patterns (explicitly NOT the target, tracked for contrast)
TRIAL_PATTERNS = [
    re.compile(rf"{FREEWORD}{G}{{0,40}}?\b(?:trial|test|prueba|essai|prova|proefperiode|deneme)\b", re.I),
    re.compile(rf"\b(?:trial|prueba|essai|prova)\b{G}{{0,30}}?{FREEWORD}", re.I),
    re.compile(rf"{FREEWORD}\s+(?:for\s+)?\d{{1,2}}\s*{PERIOD}{G}{{0,40}}?\b{THEN}\b", re.I),
]

PRICING_PATHS = ["/pricing", "/plans", "/subscribe", "/checkout", "/premium",
                 "/upgrade", "/membership", "/join", "/preise", "/precios", "/tarifs"]
PRICE_RX = re.compile(PRICE, re.I)
TAG_RX = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.I | re.S)


SCRIPT_RX = re.compile(r"<script[^>]*>(.*?)</script>", re.I | re.S)


def script_text(html):
    """Offer copy is often inside JSON in <script> blocks (Next.js, Nuxt).
    Pull it out and decode escapes, without dragging in CSS noise."""
    parts = []
    for m in SCRIPT_RX.finditer(html):
        s = m.group(1)
        if not s or len(s) < 40:
            continue
        s = s[:250000]
        s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda mm: chr(int(mm.group(1), 16)), s)
        s = s.replace("\\/", "/").replace('\\"', '"').replace("\\n", " ")
        parts.append(s)
        if sum(len(p) for p in parts) > 300000:
            break
    return " ".join(parts)


def visible_text(html):
    t = TAG_RX.sub(" ", html)
    t = re.sub(r"<[^>]+>", " ", t)
    t = htmllib.unescape(t)
    return re.sub(r"[ \t\r\n ]+", " ", t)


def price_windows(text, radius=230, cap=90):
    """Text windows around each price token (where offers live)."""
    out, last = [], -10**9
    for m in PRICE_RX.finditer(text):
        s = max(0, m.start() - radius)
        if s < last:            # merge overlapping windows
            out[-1] = out[-1] + text[max(last, s):m.end() + radius]
        else:
            out.append(text[s:m.end() + radius])
        last = m.end() + radius
        if len(out) >= cap:
            break
    return out


PAID_BEFORE_THEN = re.compile(rf"{PRICE}[^<>]{{0,80}}?\b{THEN}\b", re.I)


def _is_free_trial_snippet(snip):
    """True when the match is really 'free trial then $X' (not a paid intro price)."""
    freeish = re.search(rf"{FREEWORD}", snip, re.I)
    if not freeish:
        return False
    # a paid amount appearing before the 'then' rescues it (e.g. "$1 ... then $9")
    m = PAID_BEFORE_THEN.search(snip)
    if m and not re.match(rf"\s*{FREEWORD}", m.group(0), re.I):
        return False
    return True


def analyse(chunks):
    """chunks: list of (url, text). Returns verdict dict."""
    a_hits, b_hits, trial = [], [], False
    for url, text in chunks:
        wins = price_windows(text)
        blob = " || ".join(wins) if wins else text[:4000]
        for rx in TRIAL_PATTERNS:
            if rx.search(blob):
                trial = True
                break
        for rx, label in A_PATTERNS:
            m = rx.search(blob)
            if m:
                snip = re.sub(r"\s+", " ", m.group(0))[:190]
                ctx = blob[max(0, m.start() - 140):m.end()]
                if not _is_free_trial_snippet(ctx):
                    a_hits.append((label, snip, url))
        if not a_hits:
            for rx, label in B_PATTERNS:
                m = rx.search(blob)
                if m:
                    snip = re.sub(r"\s+", " ", m.group(0))[:190]
                    ctx = blob[max(0, m.start() - 140):m.end()]
                    if not _is_free_trial_snippet(ctx):
                        b_hits.append((label, snip, url))
    return a_hits, b_hits, trial


def check_site(url_raw):
    t0 = time.time()
    raw = (url_raw or "").strip()
    if not raw:
        return {"url": url_raw, "verdict": "Unknown", "status": "no_url"}
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw.lstrip("/")

    final, code, html, hdr = detect.fetch(raw)
    if final is None and raw.startswith("https://"):
        final, code, html, hdr = detect.fetch("http://" + raw[len("https://"):])
    if final is None:
        return {"url": url_raw, "verdict": "Unknown", "status": str(code),
                "secs": round(time.time() - t0, 1)}

    chunks = [(final, visible_text(html) + "  ||  " + script_text(html))]
    links = detect.candidate_links(html, final) if html else []
    forced = [urljoin(final, p) for p in PRICING_PATHS[:4]]
    seen = {final.rstrip("/")}
    todo = []
    for u in links[:3] + forced:
        k = u.rstrip("/")
        if k not in seen:
            seen.add(k)
            todo.append(u)
    for u in todo[:4]:
        if time.time() - t0 > 34:
            break
        f2, c2, h2, hd2 = detect.fetch(u)
        if f2 is None or not h2:
            continue
        chunks.append((f2, visible_text(h2) + "  ||  " + script_text(h2)))

    a, b, trial = analyse(chunks)
    if a:
        v, ev = "Yes", a
    elif b:
        v, ev = "Likely", b
    else:
        v, ev = "No", []
    blocked = isinstance(code, int) and code in (401, 403, 429, 451, 503)
    if v == "No" and blocked:
        v = "Unknown"
    return {
        "url": url_raw, "verdict": v,
        "status": f"blocked_{code}" if blocked else f"http_{code}",
        "evidence": " | ".join(f"{lab}: \"{sn}\"" for lab, sn, _ in ev[:2]),
        "found_on": ev[0][2] if ev else final,
        "free_trial": trial, "pages": len(chunks),
        "secs": round(time.time() - t0, 1),
        "ctx": [c[:1] for c in []],   # placeholder, corpus saved separately
    }, chunks


def run(urls, out_path, corpus_path, workers=40):
    done = set()
    if os.path.exists(out_path):
        with open(out_path) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["url"])
                except Exception:
                    pass
    todo = [u for u in urls if u not in done]
    print(f"total {len(urls)}, done {len(done)}, to check {len(todo)}", flush=True)
    lock = threading.Lock()
    n, t0 = [0], time.time()
    fh = open(out_path, "a")
    cf = gzip.open(corpus_path, "at")

    def one(u):
        try:
            r, chunks = check_site(u)
        except Exception as e:
            r, chunks = {"url": u, "verdict": "Unknown", "status": f"err_{type(e).__name__}"}, []
        r.pop("ctx", None)
        wins = []
        for cu, txt in chunks:
            for w in price_windows(txt, radius=200, cap=25):
                wins.append(w[:600])
        with lock:
            fh.write(json.dumps(r) + "\n")
            cf.write(json.dumps({"url": u, "w": wins[:40]}) + "\n")
            n[0] += 1
            if n[0] % 200 == 0:
                el = time.time() - t0
                print(f"  {n[0]}/{len(todo)} {n[0]/el:.1f}/s eta {(len(todo)-n[0])/max(n[0]/el,0.01)/60:.0f}m", flush=True)
                fh.flush()
                cf.flush()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, todo))
    fh.close()
    cf.close()
    print(f"done {n[0]} in {(time.time()-t0)/60:.1f}m", flush=True)


if __name__ == "__main__":
    urls = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    run(urls, sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 40)
