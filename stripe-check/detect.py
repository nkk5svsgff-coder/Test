#!/usr/bin/env python3
"""Stripe-presence detector for a list of websites.

Method (client-side, evidence-based):
  1. GET the homepage (https, fall back to http), following redirects.
  2. Scan response headers (CSP) + HTML for hard Stripe markers:
     js.stripe.com, checkout/buy/billing.stripe.com, api.stripe.com,
     m.stripe.network, pk_live_/pk_test_ keys, <stripe-pricing-table>, etc.
  3. If nothing found, follow up to 2 same-site commerce pages discovered in
     the homepage HTML (pricing / plans / checkout / subscribe / billing /
     upgrade / buy / signup) and scan those too.
  4. Record which marker matched and on which URL, plus any OTHER payment
     processors seen (Paddle, Lemon Squeezy, Chargebee, PayPal, Shopify,
     Apple/Google IAP, ...) for context.

Deliberately does NOT match the bare word "stripe" (avoids false positives
from "integrates with Stripe", CSS classes like .striped, blog copy).

Writes newline-delimited JSON to data/results.jsonl (resumable).
"""

import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(D, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close",
}
CONNECT_TO, READ_TO = 6, 9
MAX_BYTES = 900_000
JS_MAX_BYTES = 1_100_000
SITE_DEADLINE = 30  # hard wall-clock cap per website

# ---- hard Stripe markers: (regex, label) -------------------------------
STRIPE_MARKERS = [
    (re.compile(r"js\.stripe\.com", re.I), "js.stripe.com"),
    (re.compile(r"checkout\.stripe\.com", re.I), "checkout.stripe.com"),
    (re.compile(r"buy\.stripe\.com", re.I), "buy.stripe.com (payment link)"),
    (re.compile(r"billing\.stripe\.com", re.I), "billing.stripe.com (portal)"),
    (re.compile(r"pay\.stripe\.com", re.I), "pay.stripe.com"),
    (re.compile(r"link\.stripe\.com", re.I), "link.stripe.com"),
    (re.compile(r"api\.stripe\.com", re.I), "api.stripe.com"),
    (re.compile(r"m\.stripe\.(network|com)", re.I), "m.stripe.network (fraud beacon)"),
    (re.compile(r"[qb]\.stripe\.com", re.I), "q.stripe.com"),
    (re.compile(r"stripecdn\.com", re.I), "stripecdn.com"),
    (re.compile(r"files\.stripe\.com", re.I), "files.stripe.com"),
    (re.compile(r"hooks\.stripe\.com", re.I), "hooks.stripe.com"),
    (re.compile(r"dashboard\.stripe\.com", re.I), "dashboard.stripe.com"),
    (re.compile(r"connect\.stripe\.com", re.I), "connect.stripe.com"),
    (re.compile(r"\bpk_live_[0-9a-zA-Z]{10,}", re.I), "pk_live_ publishable key"),
    (re.compile(r"\bpk_test_[0-9a-zA-Z]{10,}", re.I), "pk_test_ publishable key"),
    (re.compile(r"stripe-pricing-table", re.I), "<stripe-pricing-table>"),
    (re.compile(r"stripe-buy-button", re.I), "<stripe-buy-button>"),
    (re.compile(r"data-stripe[-a-z]*=", re.I), "data-stripe attribute"),
    (re.compile(r"Stripe\s*\(\s*['\"]pk_", re.I), "Stripe(pk_...) init"),
    (re.compile(r"stripe(?:_|-)?(?:publishable|public)(?:_|-)?key", re.I), "stripe publishable key var"),
    (re.compile(r"@stripe/(?:stripe-js|react-stripe-js)", re.I), "@stripe/stripe-js package"),
    (re.compile(r"wc-stripe|woocommerce_stripe|wc_stripe", re.I), "WooCommerce Stripe plugin"),
    (re.compile(r"stripe_checkout|stripeCheckout", re.I), "stripeCheckout"),
    (re.compile(r"stripe\.handleCardPayment|confirmCardPayment|stripe\.elements\(", re.I), "Stripe.js API call"),
]

# ---- weak signals: real but not conclusive -> verdict "Likely" ---------
WEAK_MARKERS = [
    (re.compile(r"powered\s+by\s+stripe", re.I), "text: 'Powered by Stripe'"),
    (re.compile(r"(?:pay|payments?|checkout|billing|subscribe|purchase|card)[^.<>{}]{0,40}?\b(?:via|with|by|through|using|processed by)\s+stripe\b", re.I),
     "text: pay/checkout via Stripe"),
    (re.compile(r"\bstripe\b[^.<>{}]{0,25}?(?:secure(?:ly)?\s+(?:payment|checkout)|payment\s+gateway|handles?\s+(?:our|all)\s+payment)", re.I),
     "text: Stripe payment gateway"),
    (re.compile(r"\.data\(\s*['\"]stripe['\"]\s*\)|dataset\.stripe\b", re.I), "JS reads data-stripe attribute"),
    (re.compile(r"\bstripe(?:Response|Rsponse|Session|Customer|Subscription|Payment|Intent)\b", re.I), "JS Stripe object/var"),
    (re.compile(r"/(?:api|wp-json)[^\"'<>\s]*stripe", re.I), "server endpoint named stripe"),
    (re.compile(r"stripe[_-]?(?:webhook|connect|account_id)", re.I), "stripe webhook/connect ref"),
]

# ---- other processors (context only) ----------------------------------
OTHER_MARKERS = [
    (re.compile(r"(cdn|buy|checkout|www)\.paddle\.com|paddle_button|paddlejs|paddle\.Setup", re.I), "Paddle"),
    (re.compile(r"lemonsqueezy\.com|lmsqueezy", re.I), "Lemon Squeezy"),
    (re.compile(r"chargebee\.com|chargebee\.js", re.I), "Chargebee"),
    (re.compile(r"recurly\.com|recurly\.js", re.I), "Recurly"),
    (re.compile(r"braintreegateway\.com|braintree-api\.com|braintree\.js", re.I), "Braintree"),
    (re.compile(r"paypalobjects\.com|paypal\.com/sdk|paypal\.com/cgi-bin|paypal-button", re.I), "PayPal"),
    (re.compile(r"cdn\.shopify\.com|shopify\.com/s/files|myshopify\.com|shopifycdn", re.I), "Shopify"),
    (re.compile(r"gumroad\.com", re.I), "Gumroad"),
    (re.compile(r"fastspring\.com|onfastspring\.com", re.I), "FastSpring"),
    (re.compile(r"2checkout\.com|avangate\.com|verifone\.cloud", re.I), "2Checkout/Verifone"),
    (re.compile(r"checkout\.razorpay\.com|razorpay\.com/v1", re.I), "Razorpay"),
    (re.compile(r"mollie\.com", re.I), "Mollie"),
    (re.compile(r"adyen\.com|adyen\.js|checkoutshopper", re.I), "Adyen"),
    (re.compile(r"klarna\.com|klarnacdn", re.I), "Klarna"),
    (re.compile(r"squareup\.com|squarecdn\.com|web\.squarecdn", re.I), "Square"),
    (re.compile(r"revenuecat\.com|purchases-js", re.I), "RevenueCat"),
    (re.compile(r"apps\.apple\.com|itunes\.apple\.com", re.I), "App Store link"),
    (re.compile(r"play\.google\.com/store/apps", re.I), "Google Play link"),
    (re.compile(r"lemonsqueezy|polar\.sh", re.I), "Polar/LS"),
    (re.compile(r"paypro(global)?\.com", re.I), "PayProGlobal"),
    (re.compile(r"cleverbridge\.com", re.I), "Cleverbridge"),
    (re.compile(r"maxmind|sift\.com", re.I), None),  # ignore
    (re.compile(r"gocardless\.com", re.I), "GoCardless"),
    (re.compile(r"xsolla\.com", re.I), "Xsolla"),
    (re.compile(r"iyzipay|iyzico", re.I), "iyzico"),
    (re.compile(r"stripe\.com/(?:docs|partners)", re.I), None),  # ignore doc links
]

# candidate commerce paths, ranked
LINK_PRIORITY = [
    (re.compile(r"/(pricing|plans?|price|subscri\w*|checkout|billing|upgrade|buy|order|purchase|membership|paywall)\b", re.I), 0),
    (re.compile(r"(pricing|plans|checkout|subscribe|billing|upgrade|buy now|get started|start free|sign up|join now|donate)", re.I), 1),
]
FALLBACK_PATHS = ["/pricing", "/plans", "/checkout", "/subscribe", "/signup", "/#pricing"]

SKIP_EXT = re.compile(r"\.(pdf|zip|dmg|exe|png|jpe?g|gif|svg|mp4|mp3|ico|css|woff2?|ttf)(\?|$)", re.I)

BUNDLE_HINT = re.compile(r"(main|app|index|vendor|chunk|bundle|runtime|client|entry|payment|billing|checkout)", re.I)


def candidate_scripts(html, base):
    """Same-origin JS bundles from the homepage, most promising first."""
    host = urlparse(base).netloc.lower().lstrip("www.")
    out = []
    for m in re.finditer(r"<script\b[^>]*src=[\"']([^\"'>]{1,400})[\"']", html, re.I):
        src_u = m.group(1)
        absu = urljoin(base, src_u)
        p = urlparse(absu)
        if p.scheme not in ("http", "https") or not p.path.lower().endswith((".js", ".mjs")):
            continue
        h = p.netloc.lower().lstrip("www.")
        if h != host and not h.endswith("." + host):
            continue
        rank = 0 if BUNDLE_HINT.search(p.path) else 1
        out.append((rank, absu))
    seen, res = set(), []
    for rank, u in sorted(out, key=lambda x: x[0]):
        if u not in seen:
            seen.add(u)
            res.append(u)
    return res

_local = threading.local()


def session():
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update(HEADERS)
        ad = HTTPAdapter(max_retries=Retry(total=0, backoff_factor=0),
                         pool_connections=4, pool_maxsize=4)
        s.mount("https://", ad)
        s.mount("http://", ad)
        _local.s = s
    return s


def fetch(url, cap=None):
    """Return (final_url, status, text, header_blob) or (None, err, '', '')."""
    cap = cap or MAX_BYTES
    try:
        r = session().get(url, timeout=(CONNECT_TO, READ_TO), allow_redirects=True,
                          stream=True, verify=True)
        ctype = (r.headers.get("Content-Type") or "").lower()
        body = b""
        if "html" in ctype or "javascript" in ctype or "json" in ctype or not ctype:
            for chunk in r.iter_content(64 * 1024):
                body += chunk
                if len(body) >= cap:
                    break
        r.close()
        hdr = " ".join(f"{k}: {v}" for k, v in r.headers.items()
                       if k.lower() in ("content-security-policy",
                                        "content-security-policy-report-only",
                                        "x-powered-by", "server", "link",
                                        "report-to", "reporting-endpoints"))
        return r.url, r.status_code, body.decode("utf-8", "ignore"), hdr
    except requests.exceptions.SSLError:
        return None, "ssl_error", "", ""
    except requests.exceptions.ConnectTimeout:
        return None, "connect_timeout", "", ""
    except requests.exceptions.ReadTimeout:
        return None, "read_timeout", "", ""
    except requests.exceptions.TooManyRedirects:
        return None, "too_many_redirects", "", ""
    except requests.exceptions.ConnectionError as e:
        msg = str(e).lower()
        if "name or service not known" in msg or "nodename nor servname" in msg or "getaddrinfo" in msg:
            return None, "dns_fail", "", ""
        return None, "conn_error", "", ""
    except Exception as e:
        return None, f"err_{type(e).__name__}", "", ""


def scan(text, hdr):
    """Return (hard_evidence, other_processors, weak_evidence)."""
    blob = text + "\n" + hdr
    ev = [label for rx, label in STRIPE_MARKERS if rx.search(blob)]
    others = []
    for rx, label in OTHER_MARKERS:
        if label and rx.search(blob) and label not in others:
            others.append(label)
    weak = [label for rx, label in WEAK_MARKERS if rx.search(blob)]
    return ev, others, weak


def candidate_links(html, base):
    """Same-site commerce-ish links from the homepage, best first."""
    host = urlparse(base).netloc.lower().lstrip("www.")
    found = {}
    for m in re.finditer(r"<a\b[^>]*href=[\"']([^\"'#>]{1,300})[\"'][^>]*>(.{0,120}?)</a>",
                         html, re.I | re.S):
        href, text = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
        if href.startswith(("mailto:", "tel:", "javascript:")) or SKIP_EXT.search(href):
            continue
        absu = urljoin(base, href)
        p = urlparse(absu)
        if p.scheme not in ("http", "https"):
            continue
        h = p.netloc.lower().lstrip("www.")
        if h != host and not h.endswith("." + host):
            continue
        for rx, rank in LINK_PRIORITY:
            if rx.search(p.path + " " + text):
                if absu not in found or rank < found[absu]:
                    found[absu] = rank
                break
    return [u for u, _ in sorted(found.items(), key=lambda kv: kv[1])]


def check_site(url_raw):
    """Full check for one website. Returns a result dict."""
    t0 = time.time()
    left = lambda: SITE_DEADLINE - (time.time() - t0)
    raw = (url_raw or "").strip()
    if not raw:
        return {"url": url_raw, "verdict": "Unknown", "status": "no_url"}
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw.lstrip("/")

    others_all, statuses, weak_all, checked = [], [], [], 0

    final, code, html, hdr = fetch(raw)
    checked += 1
    if final is None and raw.startswith("https://"):
        statuses.append(str(code))
        final, code, html, hdr = fetch("http://" + raw[len("https://"):])
        checked += 1
    if final is None:
        return {"url": url_raw, "verdict": "Unknown",
                "status": statuses[0] if statuses else str(code),
                "checked": checked, "secs": round(time.time() - t0, 1)}

    def done(verdict, ev=None, where=None, st=None):
        r = {"url": url_raw, "verdict": verdict, "status": st or f"http_{code}",
             "checked": checked, "secs": round(time.time() - t0, 1),
             "others": ",".join(sorted(set(others_all)))}
        if ev:
            r["evidence"] = "; ".join(ev[:4])
            r["found_on"] = where
        elif where:
            r["found_on"] = where
        return r

    ev, others, weak = scan(html, hdr)
    others_all += others
    weak_all += [(w, final) for w in weak]
    if ev:
        return done("Yes", ev, final)

    blocked = isinstance(code, int) and code in (401, 403, 429, 451, 503)

    # ---- pages: discovered commerce links first, then /pricing, /plans ----
    links = candidate_links(html, final) if html else []
    forced = [urljoin(final, p) for p in ("/pricing", "/plans")]
    todo, seen = [], {final.rstrip("/")}
    for u in links[:2] + forced:
        k = u.rstrip("/")
        if k not in seen:
            seen.add(k)
            todo.append(u)
    for u in todo[:3]:
        if left() < 10:
            break
        f2, c2, h2, hd2 = fetch(u)
        checked += 1
        if f2 is None:
            continue
        ev2, o2, w2 = scan(h2, hd2)
        others_all += o2
        weak_all += [(w, f2) for w in w2]
        if ev2:
            return done("Yes", ev2, f2)

    # ---- first-party JS bundles (catches SPA billing code) ----
    if html and left() > 12:
        for u in candidate_scripts(html, final)[:2]:
            if left() < 8:
                break
            f3, c3, h3, hd3 = fetch(u, cap=JS_MAX_BYTES)
            checked += 1
            if f3 is None:
                continue
            ev3, o3, w3 = scan(h3, "")
            others_all += o3
            weak_all += [(w, f3) for w in w3]
            if ev3:
                return done("Yes", ev3, f3)

    if weak_all:
        labels, where = [w for w, _ in weak_all], weak_all[0][1]
        seen_l = list(dict.fromkeys(labels))
        return done("Likely", seen_l, where)
    if blocked:
        return done("Unknown", None, None, st=f"blocked_{code}")
    if isinstance(code, int) and code >= 400:
        return done("Unknown", None, None, st=f"http_{code}")
    return done("No", None, final)


def run(urls, out_path, workers=28, label=""):
    done = set()
    if os.path.exists(out_path):
        with open(out_path) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["url"])
                except Exception:
                    pass
    todo = [u for u in urls if u not in done]
    print(f"{label} total {len(urls)}, already done {len(done)}, to check {len(todo)}", flush=True)
    lock = threading.Lock()
    n = [0]
    t0 = time.time()
    with open(out_path, "a") as fh:
        def one(u):
            r = check_site(u)
            with lock:
                fh.write(json.dumps(r) + "\n")
                n[0] += 1
                if n[0] % 100 == 0:
                    el = time.time() - t0
                    rate = n[0] / el
                    print(f"  {n[0]}/{len(todo)}  {rate:.1f}/s  eta {(len(todo)-n[0])/max(rate,0.01)/60:.1f}m",
                          flush=True)
                    fh.flush()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(one, todo))
    print(f"{label} finished {n[0]} in {(time.time()-t0)/60:.1f}m", flush=True)


if __name__ == "__main__":
    urls = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    out = sys.argv[2]
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 28
    run(urls, out, workers)
