#!/usr/bin/env python3
"""Second pass over Unknown results: retry with URL variants + alternate
headers to recover sites that bot-blocked (403/429) or 404'd on the exact
URL listed in the spreadsheet.

Appends recovered results to data/results.jsonl (later lines win in the
builder), so a recovered site simply overwrites its earlier Unknown.
"""

import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import detect

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

ALT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                   "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "close",
}


def variants(url):
    """Ordered URL variants to try for a stubborn site."""
    p = urlparse(url if url.startswith(("http://", "https://")) else "https://" + url)
    host = p.netloc
    out = []
    bare = host[4:] if host.startswith("www.") else host
    wwwd = host if host.startswith("www.") else "www." + host
    path = p.path if p.path not in ("", "/") else ""
    # root of the listed host first (drops any deep path that 404'd)
    for h in (host, wwwd, bare):
        for scheme in ("https", "http"):
            out.append(f"{scheme}://{h}")
    # registrable domain (drop one subdomain level) as a last resort
    parts = bare.split(".")
    if len(parts) > 2:
        out.append("https://" + ".".join(parts[-2:]))
    if path:
        out.insert(1, f"https://{host}{path}")
    seen, res = set(), []
    for u in out:
        k = u.rstrip("/")
        if k not in seen:
            seen.add(k)
            res.append(u)
    return res[:5]


def retry_one(url):
    best = None
    for i, v in enumerate(variants(url)):
        # alternate header profile on odd attempts
        if i % 2 == 1:
            detect._local.s = None
            detect.HEADERS.clear()
            detect.HEADERS.update(ALT_HEADERS)
        else:
            detect._local.s = None
            detect.HEADERS.clear()
            detect.HEADERS.update({
                "User-Agent": detect.UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "close",
            })
        r = detect.check_site(v)
        r["url"] = url               # keep the spreadsheet's key
        r["retry_variant"] = v
        if r["verdict"] in ("Yes", "Likely"):
            return r
        if r["verdict"] == "No":
            best = best or r
        elif best is None:
            best = r
    return best


def main():
    urls = [l.strip() for l in open(sys.argv[1]) if l.strip()]
    out = os.path.join(D, "results.jsonl")
    lock = threading.Lock()
    n, t0 = [0], time.time()
    rec = {"Yes": 0, "Likely": 0, "No": 0, "Unknown": 0}
    with open(out, "a") as fh:
        def one(u):
            try:
                r = retry_one(u)
            except Exception as e:
                r = {"url": u, "verdict": "Unknown", "status": f"retry_err_{type(e).__name__}"}
            with lock:
                fh.write(json.dumps(r) + "\n")
                rec[r["verdict"]] = rec.get(r["verdict"], 0) + 1
                n[0] += 1
                if n[0] % 100 == 0:
                    el = time.time() - t0
                    print(f"  {n[0]}/{len(urls)} {n[0]/el:.1f}/s recovered={rec}", flush=True)
                    fh.flush()
        with ThreadPoolExecutor(max_workers=40) as pool:
            list(pool.map(one, urls))
    print(f"retry done {n[0]} in {(time.time()-t0)/60:.1f}m -> {rec}", flush=True)


if __name__ == "__main__":
    main()
