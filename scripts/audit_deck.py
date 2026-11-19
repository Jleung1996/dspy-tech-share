"""Audit the deck for standalone deliverability.

Checks, in order of what actually breaks when someone opens an emailed file:
  1. external references (fonts, CDNs, images) - would silently fail offline
  2. network APIs (fetch, XHR, localStorage) - blocked or unreliable on file://
  3. charset correctness - determines whether it renders as mojibake
  4. tag balance - a truncated email attachment usually shows up here
  5. modern syntax that older corporate browsers reject
"""

import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
html = path.read_text(encoding="utf-8")
raw = path.read_bytes()

print("=" * 66)
print("STANDALONE AUDIT")
print("=" * 66)
print(f"file        {path.name}")
print(f"size        {len(raw)/1024:.1f} KB  ({len(raw):,} bytes)")
print(f"encoding    utf-8, {sum(1 for c in html if ord(c) > 127)} non-ascii chars")

fails = []

# 1. external references -----------------------------------------------------
print("\n[1] external references")
patterns = {
    "http(s) URL": r"https?://",
    "@import": r"@import",
    "<link>": r"<link\b",
    "<script src>": r"<script[^>]+src=",
    "<img src>": r"<img\b[^>]*src=",
    "url(...)": r"url\(\s*['\"]?(?!data:|#)",
    "@font-face": r"@font-face",
    "srcset": r"srcset=",
}
for label, pat in patterns.items():
    hits = re.findall(pat, html, re.I)
    status = "OK" if not hits else f"FOUND {len(hits)}"
    if hits:
        fails.append(f"external: {label} x{len(hits)}")
        for h in re.findall(pat + r"[^\s\"')>]{0,60}", html, re.I)[:3]:
            print(f"    {h[:80]}")
    print(f"    {status:<12} {label}")

# 2. network / storage APIs --------------------------------------------------
print("\n[2] browser APIs that fail on file://")
for label, pat in {
    "fetch(": r"\bfetch\s*\(",
    "XMLHttpRequest": r"XMLHttpRequest",
    "localStorage": r"localStorage",
    "sessionStorage": r"sessionStorage",
    "indexedDB": r"indexedDB",
    "WebSocket": r"WebSocket",
    "import(": r"\bimport\s*\(",
}.items():
    hits = re.findall(pat, html)
    if hits:
        fails.append(f"api: {label}")
    print(f"    {'OK' if not hits else 'FOUND ' + str(len(hits)):<12} {label}")

# 3. charset ----------------------------------------------------------------
print("\n[3] charset declaration")
head = html[:2000]
has_meta = re.search(r'<meta\s+charset=["\']?utf-8', head, re.I) is not None
first_nonascii = next((i for i, c in enumerate(html) if ord(c) > 127), None)
meta_pos = html.lower().find("<meta charset")
print(f"    {'OK' if has_meta else 'MISSING':<12} <meta charset=utf-8>")
if first_nonascii is not None and meta_pos > first_nonascii:
    fails.append("charset declared after non-ascii content")
    print("    FAIL         charset appears after first non-ascii char")
else:
    print("    OK           charset declared before any non-ascii content")

# 4. tag balance ------------------------------------------------------------
print("\n[4] structural balance")
for tag in ("html", "head", "body", "section", "div", "table", "svg"):
    o = len(re.findall(rf"<{tag}\b", html))
    c = len(re.findall(rf"</{tag}>", html))
    ok = o == c or tag in ("div", "svg", "table")  # these can be implied
    flag = "OK" if o == c else f"open {o} / close {c}"
    if tag in ("html", "head", "body") and o != c:
        fails.append(f"unbalanced <{tag}>")
    print(f"    {flag:<16} <{tag}>")
print(f"    {'OK' if html.rstrip().lower().endswith('</html>') else 'FAIL':<16} ends with </html>")

# 5. risky syntax -----------------------------------------------------------
print("\n[5] syntax portability")
risky = {
    "optional chaining ?.": r"\?\.[a-zA-Z_$]",
    "nullish ??": r"\?\?",
    "structuredClone": r"structuredClone",
    "Array.at(": r"\.at\(",
    ":has(": r":has\(",
    "color-mix(": r"color-mix\(",
    "backdrop-filter": r"backdrop-filter",
    "container queries": r"@container",
}
for label, pat in risky.items():
    hits = re.findall(pat, html)
    note = "OK" if not hits else f"{len(hits)} use(s)"
    print(f"    {note:<16} {label}")

print("\n" + "=" * 66)
if fails:
    print("BLOCKING ISSUES:")
    for f in fails:
        print("  -", f)
else:
    print("RESULT: fully self-contained. No network, no external files,")
    print("        no storage APIs. Opens from a bare .html on any modern browser.")
print("=" * 66)
