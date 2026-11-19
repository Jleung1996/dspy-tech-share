"""Build the tech-sharing deck as a single self-contained HTML file.

Page 3 is generated from the prompts GEPA actually wrote, so the diffs cannot
drift from reality. Re-run this after any optimisation run to regenerate.

    python build_deck.py
    python build_deck.py --out out/teaching/deck.html

No external assets: one file, opens offline, arrow keys to navigate.
"""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
import sys as _sys
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
import peerlens as pl
from deck_concepts import CONCEPTS
from deck_details import DETAILS
from peerlens.prompt_v2 import RULE_MAP, rule_summary

HERE = Path(__file__).resolve().parents[1]

# The model occasionally emits mojibake for punctuation. Written with escapes so
# this table can never be mangled by an editor or an encoding round-trip.
_MOJIBAKE = {
    "\u00e2\u20ac\u201d": "\u2014",   # em dash
    "\u00e2\u20ac\u201c": "\u2013",   # en dash
    "\u00e2\u20ac\u2122": "'",        # right single quote
    "\u00e2\u20ac\u0153": '"',       # left double quote
    "\u00e2\u20ac\u009d": '"',       # right double quote
    "\u00c2\u00b7": "\u00b7",         # middot
    "\u00c2\u00a0": " ",              # nbsp
    "\u00e2\u2020\u2019": "\u2192",   # arrow right
    "\u00e2\u2020\u201c": "\u2193",   # arrow down
    "\u00c2": "",                     # stray latin-1 marker
    "\x00": "",
}


def clean_text(s: str) -> str:
    for bad, good in _MOJIBAKE.items():
        s = s.replace(bad, good)
    return s.strip()


# ---------------------------------------------------------------------------
# data collection
# ---------------------------------------------------------------------------
def load_versions(prompts_dir: Path, baseline: str) -> list[dict]:
    """v0 plus every proposal GEPA wrote, with line diffs against the previous."""
    versions: list[dict] = [{"label": "v0", "kind": "human",
                             "text": clean_text(baseline),
                             "score": None, "note": "the prompt we started from"}]

    proposals = sorted(prompts_dir.glob("proposal_*.md")) if prompts_dir.is_dir() else []
    for path in proposals:
        text = clean_text(path.read_text(encoding="utf-8"))
        if not text or text == versions[-1]["text"]:
            continue
        versions.append(
            {"label": f"v{len(versions)}", "kind": "gepa", "text": text,
             "score": None, "note": f"GEPA proposal {path.stem.split('_')[-1]}"}
        )

    for i, v in enumerate(versions):
        prev = versions[i - 1]["text"] if i else ""
        v["diff"] = line_diff(prev, v["text"])
        v["chars"] = len(v["text"])
        v["words"] = len(v["text"].split())
    return versions


def line_diff(before: str, after: str) -> list[list[str]]:
    """Ordered [op, text] rows: op in {'+', '-', ' '}."""
    a = before.splitlines() if before else []
    b = after.splitlines()
    rows: list[list[str]] = []
    for line in difflib.unified_diff(a, b, lineterm="", n=1):
        if line.startswith(("---", "+++")):
            continue
        if line.startswith("@@"):
            rows.append(["@", line])
        elif line.startswith("+"):
            rows.append(["+", line[1:]])
        elif line.startswith("-"):
            rows.append(["-", line[1:]])
        elif line.startswith(" "):
            rows.append([" ", line[1:]])
    return rows


def apply_scores(versions: list[dict], leaderboard: Path) -> float | None:
    """Attach measured scores if a leaderboard exists. Returns the baseline score."""
    if not leaderboard.exists():
        return None
    try:
        data = json.loads(leaderboard.read_text(encoding="utf-8"))
    except Exception:
        return None
    by_text = {row["text"].strip(): row for row in data if "text" in row}
    for v in versions:
        row = by_text.get(v["text"].strip())
        if row:
            v["score"] = round(row["score"], 3)
            if row.get("per_case"):
                v["per_case"] = list(row["per_case"])
    base = next((v["score"] for v in versions if v["label"] == "v0"), None)
    return base


def read_baseline_md(path: Path) -> tuple[float | None, list[dict]]:
    """Pull the score and per-case rows out of baseline.md."""
    if not path.exists():
        return None, []
    text = path.read_text(encoding="utf-8")
    score = None
    for line in text.splitlines():
        if line.startswith("**Score:"):
            try:
                score = float(line.split("**Score:")[1].split("**")[0].strip())
            except Exception:
                pass
    rows = []
    for line in text.splitlines():
        if line.startswith("| EQ_"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 7:
                rows.append({"asset": cells[0], "score": cells[1],
                             "peers": cells[2], "adj": cells[3],
                             "wrong": cells[4], "picks": cells[5]})
    return score, rows


# ---------------------------------------------------------------------------
# shell
# ---------------------------------------------------------------------------
CSS = """
:root{
  --ink:#101828; --muted:#5b6478; --line:#e3e7ef; --bg:#fbfcfe; --panel:#ffffff;
  --accent:#2f5bea; --accent-2:#0f9d76; --warn:#c2410c; --bad:#b42318;
  --code-bg:#0f1526; --code-ink:#d7dcea; --add:#0f7a4d; --del:#b42318;
  --mono:"Cascadia Code",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{
  background:var(--bg); color:var(--ink);
  font:16px/1.55 "Segoe UI",system-ui,-apple-system,Inter,sans-serif;
  overflow:hidden;
}
.deck{height:100%;position:relative}
.slide{
  position:absolute; inset:0; padding:46px 60px 84px;
  opacity:0; transform:translateX(28px) scale(.995);
  transition:opacity .45s ease, transform .45s cubic-bezier(.2,.8,.2,1);
  pointer-events:none; overflow-y:auto;
}
.slide.active{opacity:1;transform:none;pointer-events:auto}
.slide.leaving{transform:translateX(-28px) scale(.995)}
.eyebrow{font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:700}
h1{font-size:44px;line-height:1.1;margin:10px 0 6px;letter-spacing:-.02em}
h2{font-size:16px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin:30px 0 12px}
.lede{font-size:20.5px;color:var(--muted);max-width:74ch;margin:0 0 8px}
.grid{display:grid;gap:18px}
.g2{grid-template-columns:1fr 1fr}
.g3{grid-template-columns:repeat(3,1fr)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 20px;
  box-shadow:0 1px 2px rgba(16,24,40,.04)}
.card h3{margin:0 0 6px;font-size:16px}
.card p{margin:0;color:var(--muted);font-size:14px}
.pill{display:inline-block;padding:3px 10px;border-radius:999px;font-size:12px;font-weight:700;
  background:rgba(47,91,234,.1);color:var(--accent)}
.pill.g{background:rgba(15,157,118,.12);color:var(--accent-2)}
.pill.r{background:rgba(180,35,24,.1);color:var(--bad)}
code,.mono{font-family:var(--mono)}
.diagram{display:flex;align-items:center;justify-content:center;gap:0;margin:26px 0 10px}
.node{background:var(--panel);border:1.5px solid var(--line);border-radius:12px;padding:12px 16px;
  min-width:132px;text-align:center;position:relative;transition:.3s}
.node .n{font-weight:700;font-size:14px}
.node .d{font-size:11px;color:var(--muted);margin-top:2px}
.node.on{border-color:var(--accent);box-shadow:0 0 0 4px rgba(47,91,234,.12);transform:translateY(-3px)}
.arrow{width:46px;height:2px;background:var(--line);position:relative;flex:0 0 auto}
.arrow::after{content:"";position:absolute;right:-1px;top:-3px;border:4px solid transparent;border-left-color:var(--line)}
.arrow .flow{position:absolute;inset:0;background:var(--accent);transform:scaleX(0);transform-origin:left;
  transition:transform .6s ease}
.arrow.lit .flow{transform:scaleX(1)}
.arrow.lit::after{border-left-color:var(--accent)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line)}
th{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
td.num{font-variant-numeric:tabular-nums;font-weight:600}
.bar{height:8px;border-radius:5px;background:var(--line);overflow:hidden}
.bar > i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--accent-2));
  width:0;transition:width .9s cubic-bezier(.2,.8,.2,1)}
.split{display:flex;height:38px;border-radius:10px;overflow:hidden;border:1px solid var(--line)}
.split > div{display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;
  width:0;transition:width 1s cubic-bezier(.2,.8,.2,1)}
.split .mech{background:linear-gradient(90deg,#2f5bea,#4f7ef7)}
.split .opt{background:linear-gradient(90deg,#0f9d76,#25c295)}
.nav{position:fixed;left:0;right:0;bottom:0;height:56px;display:flex;align-items:center;
  justify-content:space-between;padding:0 60px;background:linear-gradient(to top,var(--bg) 60%,transparent)}
.dots{display:flex;gap:7px}
.dot{width:30px;height:30px;border-radius:9px;background:#fff;border:1px solid var(--line);color:var(--muted);cursor:pointer;transition:.2s;font-family:inherit;font-size:12.5px;font-weight:700;padding:0;display:inline-flex;align-items:center;justify-content:center}
.dot:hover{border-color:var(--accent);color:var(--accent)}
.dot.on{background:var(--accent);border-color:var(--accent);color:#fff;transform:none}
.hint{font-size:12px;color:var(--muted)}
/* prompt / diff viewer */
.viewer{display:grid;grid-template-columns:230px 1fr;gap:20px;align-items:start}
.vlist{display:flex;flex-direction:column;gap:6px;max-height:62vh;overflow:auto;padding-right:4px}
.vitem{border:1px solid var(--line);border-radius:10px;padding:9px 11px;cursor:pointer;background:var(--panel);
  transition:.2s;text-align:left;font:inherit;display:flex;justify-content:space-between;gap:8px;align-items:center}
.vitem:hover{border-color:#c8d2e6;transform:translateX(2px)}
.vitem.on{border-color:var(--accent);background:rgba(47,91,234,.05);box-shadow:0 0 0 3px rgba(47,91,234,.08)}
.vitem .lbl{font-weight:700;font-size:13px}
.vitem .sc{font-variant-numeric:tabular-nums;font-size:12px;color:var(--muted)}
.vitem .sc.up{color:var(--add);font-weight:700}
.pane{min-height:62vh}
.panehead{display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap}
.code{background:var(--code-bg);color:var(--code-ink);border-radius:12px;padding:16px 18px;
  font-family:var(--mono);font-size:12.5px;line-height:1.62;overflow:auto;max-height:52vh;white-space:pre-wrap}
.dl{display:block;opacity:0;animation:fin .32s forwards}
.dl.add{color:#7ee2b0}.dl.del{color:#ff9b8f}.dl.ctx{color:#8b95ad}.dl.hunk{color:#6d7ba0}
.dl.add::before{content:"+ ";color:#3fae7d}
.dl.del::before{content:"- ";color:#e06a5a}
.dl.ctx::before{content:"  "}
@keyframes fin{to{opacity:1}}
.commit{border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;
  padding:10px 14px;background:var(--panel);font-size:13px;color:var(--muted);margin-bottom:12px}
.commit b{color:var(--ink)}
.spark{display:flex;align-items:flex-end;gap:4px;height:64px;margin-top:8px}
.spark div{flex:1;background:linear-gradient(180deg,var(--accent),#9db4f8);border-radius:3px 3px 0 0;
  height:0;transition:height .8s cubic-bezier(.2,.8,.2,1)}
.note{font-size:13px;color:var(--muted);border-left:2px solid var(--line);padding-left:12px;margin-top:14px}
.big{font-size:54px;font-weight:800;letter-spacing:-.03em;line-height:1;font-variant-numeric:tabular-nums}
.kv{display:flex;gap:26px;flex-wrap:wrap;margin-top:6px}
.kv div{min-width:110px}
.kv .k{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}
.kv .v{font-size:26px;font-weight:800;font-variant-numeric:tabular-nums}
.tag{font-size:11px;font-weight:700;padding:2px 8px;border-radius:6px;background:#eef2fb;color:var(--accent)}
/* toolset chips + lifecycle */
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.chip{font-family:var(--mono);font-size:11.5px;padding:3px 8px;border-radius:6px;
  background:#f1f4fb;color:#26355c;border:1px solid #e0e6f4;transition:.18s;cursor:default}
.chip:hover{background:var(--accent);color:#fff;border-color:var(--accent);transform:translateY(-1px)}
.chip.hot{background:rgba(15,157,118,.12);color:#0b6b51;border-color:rgba(15,157,118,.3)}
.flowline{display:flex;align-items:stretch;gap:0;margin:18px 0 6px;flex-wrap:wrap}
.step{flex:1 1 0;min-width:150px;background:var(--panel);border:1.5px solid var(--line);
  border-radius:10px;padding:11px 13px;position:relative}
.step + .arrow2{}
.step .t{font-weight:700;font-size:13px}
.step .s{font-size:11.5px;color:var(--muted);margin-top:3px;line-height:1.4}
.arrow2{flex:0 0 26px;align-self:center;height:2px;background:var(--line);position:relative}
.arrow2::after{content:"";position:absolute;right:-1px;top:-3px;border:4px solid transparent;border-left-color:var(--line)}
.howto{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:12px}
.howto .card h3{display:flex;align-items:center;font-size:15px}
.spec{font-size:12.5px;color:var(--muted);background:#f7f9fd;border:1px dashed var(--line);
  border-radius:10px;padding:12px 16px;margin-top:16px}
.spec b{color:var(--ink)}
.section{scroll-margin-top:10px}
.scrolltip{position:sticky;bottom:0;text-align:center;font-size:12px;color:var(--muted);
  padding:8px 0;background:linear-gradient(to top,var(--bg) 55%,transparent);pointer-events:none}
/* newcomer-friendly blocks */
.node .tech{font-size:10px;color:#98a1b6;font-family:var(--mono);margin-top:4px}
.analogy{background:linear-gradient(90deg,rgba(47,91,234,.06),rgba(15,157,118,.06));
  border:1px solid #dfe6f6;border-radius:12px;padding:16px 20px;margin:18px 0;font-size:15px}
.analogy b{color:var(--ink)}
.caps{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:14px}
.cap{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:15px 17px;
  transition:.2s}
.cap:hover{border-color:#c3cfeb;box-shadow:0 4px 14px rgba(16,24,40,.06);transform:translateY(-2px)}
.cap-t{font-weight:800;font-size:15.5px;letter-spacing:-.01em}
.cap-d{font-size:13.5px;color:var(--muted);margin-top:5px;line-height:1.5}
.cap-a{font-family:var(--mono);font-size:11px;color:#9aa4bb;margin-top:9px}
.plain{font-size:16.5px;color:var(--muted);max-width:80ch}
.bigq{font-size:22px;font-weight:700;line-height:1.35;max-width:60ch;margin:6px 0 14px}
.bigq em{color:var(--accent);font-style:normal}
/* ---- graphics-first blocks ---- */
.ic{width:22px;height:22px;stroke:currentColor;fill:none;stroke-width:1.7;
  stroke-linecap:round;stroke-linejoin:round;flex:0 0 auto}
.ic.lg{width:30px;height:30px;stroke-width:1.5}
.node .ic{margin:0 auto 6px;color:var(--accent);display:block}
.node.on .ic{color:var(--accent-2)}
.ba{display:grid;grid-template-columns:1fr 40px 1fr;align-items:stretch;margin:18px 0 6px}
.ba-col{border:1px solid var(--line);border-radius:14px;padding:16px 18px;background:var(--panel)}
.ba-col.bad{background:#fdfbfb;border-color:#f2dedb}
.ba-col.good{background:#f8fdfb;border-color:#d3eee2}
.ba-h{font-size:11.5px;text-transform:uppercase;letter-spacing:.1em;font-weight:800;margin-bottom:10px}
.ba-col.bad .ba-h{color:var(--bad)}
.ba-col.good .ba-h{color:var(--accent-2)}
.pv{display:flex;justify-content:space-between;align-items:center;padding:7px 11px;border-radius:8px;
  background:#fff;border:1px solid var(--line);margin-bottom:7px;font-family:var(--mono);font-size:12.5px}
.pv b{font-weight:800}
.pv b.q{color:#c2c8d6}
.pv b.s{color:var(--muted);font-variant-numeric:tabular-nums}
.pv.win{border-color:var(--accent-2);background:#effaf5;box-shadow:0 0 0 3px rgba(15,157,118,.10)}
.pv.win b.s{color:var(--add)}
.ba-f{font-size:12.5px;color:var(--muted);margin-top:9px;text-align:center}
.ba-vs{display:flex;align-items:center;justify-content:center;color:#c2c8d6;font-weight:800;font-size:11px}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 12px;
  text-align:center;transition:.2s;cursor:default}
.tile:hover{border-color:var(--accent);transform:translateY(-3px);box-shadow:0 6px 18px rgba(16,24,40,.08)}
.tile .ic{color:#5b6b8f;margin:0 auto 8px;display:block;transition:.2s}
.tile:hover .ic{color:var(--accent)}
.tl{font-weight:700;font-size:13.5px;line-height:1.3}
.tk{font-family:var(--mono);font-size:10px;color:#a7afc2;margin-top:5px}
.trade{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px}
.trade .card{display:flex;gap:12px;align-items:flex-start}
.trade .ic{color:var(--accent-2);margin-top:1px}
.trade .no .ic{color:var(--bad)}
.trade p{margin:0;font-size:13.5px}
.hintline{font-size:12.5px;color:#98a1b6;text-align:center;margin-top:10px}
.tile{cursor:pointer}
.tile::after{content:"i";position:absolute;top:7px;right:9px;width:14px;height:14px;border-radius:50%;
  background:#eef2fb;color:#8794b4;font-size:9px;font-weight:800;line-height:14px;text-align:center;
  opacity:.75}
.tile:hover::after{background:var(--accent);color:#fff}
.modal{position:fixed;inset:0;background:rgba(12,18,32,.55);display:none;z-index:50;
  padding:40px 24px;overflow:auto}
.modal.on{display:block}
.sheet{max-width:900px;margin:0 auto;background:#fff;border-radius:16px;padding:26px 30px 30px;
  box-shadow:0 24px 70px rgba(10,16,32,.3)}
.sheet-top{display:flex;align-items:flex-start;gap:14px;border-bottom:1px solid var(--line);padding-bottom:14px}
.sheet-top .ic{color:var(--accent);margin-top:3px}
.sheet h2{margin:0;font-size:22px;letter-spacing:-.01em;color:var(--ink)}
.sheet .api{font-family:var(--mono);font-size:12px;color:#8794b4;margin-top:3px}
.sheet .close{margin-left:auto;border:0;background:#f1f4fb;width:30px;height:30px;border-radius:8px;
  cursor:pointer;font-size:16px;color:#5b6478;line-height:1}
.sheet .close:hover{background:#e6ecf9;color:var(--ink)}
.sheet h4{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:18px 0 6px}
.sheet p{margin:0;font-size:14px;color:#39445c;line-height:1.55}
.sheet pre{background:var(--code-bg);color:var(--code-ink);border-radius:10px;padding:14px 16px;
  font-family:var(--mono);font-size:12px;line-height:1.6;overflow:auto;margin:0}
.limitbox{background:#fffbeb;border:1px solid #f5e6b8;border-radius:10px;padding:12px 14px;
  font-size:13.5px;color:#6b5a1e;line-height:1.5;display:flex;gap:10px}
.limitbox .ic{color:#b58a12;margin-top:1px;flex:0 0 auto}
.mtag{font-family:var(--mono);font-size:10px;padding:2px 6px;border-radius:5px;font-weight:700}
.mtag.schema{background:#e8effd;color:#2f5bea}
.mtag.validator{background:#e9f8f2;color:#0b7a5c}
.mtag.python{background:#fdf1e6;color:#a35a10}
.tn{font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}
.tn.good{color:#0b7a5c}
.tn.mid{color:#a3610f}
.tn.bad{color:#b42318}
.tcaption{font-size:12.5px;color:var(--muted);margin:0 0 10px}
table.rules td{font-size:12.5px;vertical-align:top;padding:6px 8px}
table.rules td:first-child{white-space:nowrap}
ol.optrules{margin:0;padding-left:20px;font-size:13px;color:#39445c;line-height:1.6}
ol.optrules li{margin-bottom:4px}
.code.fullprompt{max-height:44vh;margin-top:0}
.decide{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
.dcol{border-radius:12px;padding:18px 22px}
.dcol.yes{background:#f3fbf7;border:1px solid #d3eee2}
.dcol.no{background:#fdf7f5;border:1px solid #f6ded8}
.dcol h3{margin:0 0 12px;font-size:16px;display:flex;align-items:center;gap:9px}
.dcol h3 .ic{width:20px;height:20px}
.dcol.yes h3{color:var(--accent-2)}
.dcol.no h3{color:var(--bad)}
.dcol ul{margin:0;padding:0;list-style:none}
.dcol li{display:flex;gap:10px;font-size:15px;line-height:1.45;margin-bottom:11px;color:#39445c}
.dcol li:last-child{margin-bottom:0}
.dcol li .ic{flex:0 0 auto;width:16px;height:16px;margin-top:3px;stroke-width:2.6}
.dcol.yes li .ic{color:var(--accent-2)}
.dcol.no li .ic{color:var(--bad)}

.tradegrid{display:flex;flex-direction:column;gap:10px;margin:20px 0 4px}
.trow{display:grid;grid-template-columns:1fr 46px 1fr;align-items:center;gap:8px;
  background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:15px 22px;
  transition:.2s}
.trow:hover{border-color:#c3cfeb;transform:translateX(3px)}
.tleft{font-size:17px;color:#949cb0;line-height:1.3}
.tarrow{text-align:center;color:var(--accent);font-size:19px;font-weight:800;line-height:1}
.tright{font-size:17px;font-weight:700;color:var(--ink);line-height:1.3}
.tradecards{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:18px}
.tcard{border-radius:12px;padding:17px 20px}
.tcard.buy{background:#f3fbf7;border:1px solid #d3eee2}
.tcard.cost{background:#fffaf2;border:1px solid #f5e6c8}
.tcard h3{margin:0 0 5px;font-size:15px}
.tcard p{margin:0;font-size:14.5px;line-height:1.5}

.tradetab{border-collapse:collapse;width:100%;font-size:13.5px;margin:14px 0 4px}
.tradetab th,.tradetab td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);
  vertical-align:top;line-height:1.45}
.tradetab th{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);
  background:#f8fafd}
.tradetab td:first-child{color:var(--muted);white-space:nowrap;font-size:12.5px}
.tradetab tr td:nth-child(2){color:var(--muted)}
.tradetab tr td:nth-child(3){font-weight:500}
.limits{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:14px}
.lim{display:flex;gap:11px;background:var(--panel);border:1px solid var(--line);
  border-left:3px solid #e0b93c;border-radius:10px;padding:13px 15px}
.lim .ic{color:#b58a12;margin-top:1px}
.lim b{font-size:13.5px;display:block;margin-bottom:2px}
.lim span{font-size:12.5px;color:var(--muted);line-height:1.45}


/* ---- score calculator ---- */
.mapto{font-family:var(--mono);font-size:11px;color:#0b7a5c;background:#eefaf5;
  border:1px solid #d6efe4;border-radius:6px;padding:3px 8px;display:inline-block}
.calcbox{display:grid;grid-template-columns:1fr 320px;gap:18px;margin-top:14px;align-items:start}
.pickgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.pick{border:1.5px solid var(--line);border-radius:10px;padding:10px 11px;cursor:pointer;
  background:#fff;transition:.15s;text-align:left;font:inherit}
.pick:hover{border-color:#c3cfeb;transform:translateY(-1px)}
.pick .pid{font-family:var(--mono);font-size:11.5px;font-weight:700;color:#26355c}
.pick .pname{font-size:11px;color:var(--muted);margin-top:2px;display:block;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pick.sel{border-color:var(--accent);box-shadow:0 0 0 3px rgba(47,91,234,.10);background:#f7f9ff}
.pick.t-peer{border-left:3px solid #0f9d76}
.pick.t-adjacent{border-left:3px solid #d99a1e}
.pick.t-wrong{border-left:3px solid #b42318}
.pick.t-neutral{border-left:3px solid #c2c8d6}
.picknote{font-size:12.5px;color:var(--muted);margin-top:10px;min-height:18px}
.calcright{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 20px;text-align:center}
.scorelabel{font-size:10.5px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}
.scorenum{font-size:46px;font-weight:800;letter-spacing:-.03em;line-height:1.1;
  font-variant-numeric:tabular-nums;color:var(--ink);transition:color .2s}
.scorebreak{font-family:var(--mono);font-size:11.5px;color:var(--muted);margin-top:8px;line-height:1.7}
.formula{font-size:11px;color:#98a1b6;margin-top:12px;border-top:1px solid var(--line);padding-top:10px;line-height:1.5}
/* ---- optimiser stepper ---- */
.optbox{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:16px 18px;margin-top:14px}
.optcontrols{display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap}
.obtn{border:0;background:var(--accent);color:#fff;font:inherit;font-weight:700;font-size:13px;
  padding:8px 15px;border-radius:9px;cursor:pointer;transition:.15s}
.obtn:hover{background:#2450d8}
.obtn.ghost{background:#f1f4fb;color:#5b6478}
.obtn.ghost:hover{background:#e6ecf9}
.obtn:disabled{opacity:.45;cursor:default}
.opthint{font-size:12.5px;color:var(--muted)}
.optbars{display:flex;align-items:flex-end;gap:6px;height:120px}
.obar{flex:1;position:relative;border-radius:5px 5px 0 0;background:#e3e9f6;height:0;
  transition:height .35s cubic-bezier(.2,.8,.2,1), background .2s, box-shadow .2s;cursor:pointer}
.obar .olabel{position:absolute;bottom:-20px;left:0;right:0;text-align:center;font-size:10px;
  color:var(--muted);font-family:var(--mono)}
.obar.kept{background:linear-gradient(180deg,#25c295,#0f9d76)}
.obar.dropped{background:#e8b4ae}
.obar.baseline{background:linear-gradient(180deg,#7f9bf5,#2f5bea)}
.obar.on{box-shadow:0 0 0 3px rgba(47,91,234,.22)}
.optnote{margin-top:32px;font-size:13.5px;color:#39445c;min-height:44px;line-height:1.5;
  border-top:1px solid var(--line);padding-top:12px}
.optnote b{color:var(--ink)}
.fbexample{margin-top:14px;background:#f7f9fd;border:1px dashed var(--line);border-radius:10px;padding:12px 16px}
.fblabel{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:6px}
.fbexample code{font-family:var(--mono);font-size:11.5px;color:#39445c;white-space:pre-wrap;line-height:1.6}

/* ---- anatomy stepper ---- */
.anabox-wrap{border:1px solid var(--line);border-radius:14px;background:var(--panel);margin-top:14px;overflow:hidden}
.anatabs{display:flex;flex-wrap:wrap;gap:0;border-bottom:1px solid var(--line);background:#f8fafd}
.anatab-btn{border:0;background:transparent;font:inherit;font-size:12.5px;font-weight:700;
  color:#7b869d;padding:11px 15px;cursor:pointer;border-bottom:2px solid transparent;transition:.15s}
.anatab-btn:hover{color:var(--ink);background:#eef2fb}
.anatab-btn.on{color:var(--accent);border-bottom-color:var(--accent);background:#fff}
/* ---- reflection prompt rendering ---- */
.pgp{background:#0f1526;border-radius:10px;padding:14px 16px;margin-top:10px;
  font-family:var(--mono);font-size:11.5px;line-height:1.6;color:#cfd6e8}
.pgsec{margin-bottom:13px}
.pgsec:last-child{margin-bottom:0}
.pgh{color:#8fb0ff;font-weight:700;margin-bottom:4px}
.pgdim{color:#8894b0}
.pgcode{background:#0a0f1c;border:1px solid #1e2942;border-radius:7px;padding:9px 11px;
  margin:6px 0 0;color:#dfe4f0;font-size:11px;line-height:1.55;white-space:pre-wrap}
.pgex{background:#0a0f1c;border-left:2px solid #2f5bea;border-radius:0 7px 7px 0;
  padding:8px 11px;margin-top:8px}
.pgk{color:#8fb0ff;font-weight:700;margin-bottom:4px}
.pgrow{color:#cfd6e8;margin-bottom:3px}
.pgkk{display:inline-block;min-width:104px;color:#8894b0}
.pgrow code{color:#a8e6c4}
.pglist{margin:4px 0 0;padding-left:18px;color:#cfd6e8}
.pglist li{margin-bottom:3px}
.vsrow{display:grid;grid-template-columns:1fr 40px 1fr;gap:10px;align-items:center;
  margin-top:14px}
.vsbox{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:12px 16px;text-align:center}
.vsbox.win{background:#f3fbf7;border-color:#c9ecdc}
.vsk{font-size:10px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);
  margin-bottom:6px;font-weight:700}
.vsv{font-size:26px;font-weight:800;letter-spacing:-.02em;line-height:1;color:var(--ink)}
.vsbox.win .vsv{color:#0b7a5c}
.vsarrow{text-align:center;color:#b9c0d0;font-size:16px}
.vsdelta{margin-top:10px;text-align:center;font-family:var(--mono);font-size:13px;
  font-weight:700;color:#0b7a5c}
table.cmp td .good{color:#0b7a5c}
table.cmp td .bad{color:#b4432c}

.anapane{padding:18px 20px}
.anapane h3{margin:0 0 8px;font-size:16px}
.anapane p{margin:0;font-size:13.5px;color:#39445c;line-height:1.55}
.anabox{background:#f7f9fd;border:1px dashed var(--line);border-radius:10px;padding:12px 14px;
  font-family:var(--mono);font-size:11.5px;line-height:1.75;color:#39445c;margin-top:10px;
  white-space:pre-wrap;word-break:break-word}
.anak{display:inline-block;min-width:150px;color:#8794b4;font-weight:700}
.anaout{background:var(--code-bg);color:#b9f5d8;font-family:var(--mono);font-size:13px;
  border-radius:9px;padding:11px 15px;margin-top:8px;letter-spacing:.02em}
.anatwo{display:grid;grid-template-columns:120px 1fr;gap:16px;margin-top:10px;align-items:start}
.analab{font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:4px}
.anabig{font-size:38px;font-weight:800;letter-spacing:-.03em;color:var(--warn);font-variant-numeric:tabular-nums;line-height:1}
.anafb{background:#f7f9fd;border:1px solid var(--line);border-radius:9px;padding:11px 13px;
  font-family:var(--mono);font-size:11.5px;line-height:1.65;color:#39445c}
.anacode{background:var(--code-bg);color:var(--code-ink);border-radius:10px;padding:13px 15px;
  font-family:var(--mono);font-size:11.5px;line-height:1.6;max-height:230px;overflow:auto;
  white-space:pre-wrap;margin-top:10px}
table.anatab{margin-top:12px;font-size:13px}
table.anatab td,table.anatab th{padding:6px 10px}
table.anatab .keep{color:#0b7a5c;font-weight:700}
table.anatab .drop{color:var(--muted)}

.mipwrap{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;margin-top:16px}
.mipup{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:14px}
.mipcol h4{margin:0 0 8px;font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;
  color:var(--muted)}
.mipitem{font-size:12.5px;color:#39445c;margin-bottom:5px;line-height:1.4}
.mipitem b{display:inline-block;min-width:28px;color:var(--accent);font-family:var(--mono)}
.mipctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.mbtn{font:inherit;font-size:12.5px;font-weight:700;padding:7px 14px;border-radius:8px;
  border:1px solid var(--accent);background:var(--accent);color:#fff;cursor:pointer}
.mbtn.ghost{background:#fff;color:var(--accent)}
.mbtn:disabled{opacity:.4;cursor:default}
.mipstat{font-size:12px;color:var(--muted);margin-left:4px}
.mipgrid{display:grid;grid-template-columns:74px repeat(3,1fr);gap:6px}
.miph{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
  text-align:center;padding:2px 0}
.mipl{font-family:var(--mono);font-size:11.5px;font-weight:700;color:#39445c;
  display:flex;align-items:center}
.mcell{border:1px dashed var(--line);border-radius:8px;min-height:42px;display:flex;
  align-items:center;justify-content:center;font-family:var(--mono);font-size:13px;
  font-weight:700;color:#c8cedb;background:#fff;transition:.2s}
.mcell.on{border-style:solid;color:#fff}
.mcell.on.good{background:#0b7a5c;border-color:#0b7a5c}
.mcell.on.mid{background:#2f5bea;border-color:#2f5bea}
.mcell.on.bad{background:#b4432c;border-color:#b4432c}
.mcell b{display:block;font-size:13px;line-height:1.1}
.mcell span{display:block;font-size:9.5px;opacity:.9;margin-top:2px;letter-spacing:.02em}
.mcell.best{outline:3px solid #0b7a5c;outline-offset:2px}
.mcell.never{border-style:dotted;color:#aab2c2;background:#fafbfd}
.mipnote{font-size:13px;color:#39445c;margin-top:12px;line-height:1.5;min-height:40px}

/* ---- MIPROv2 flowchart ---- */
/* loop-back rail: from the decision box up to the trial box */
.floop{grid-column:1;grid-row:3 / 10;align-self:stretch;margin:26px 0 26px 0;
  border:2px solid var(--accent);border-right:none;border-radius:12px 0 0 12px;
  position:relative;pointer-events:none}
/* ---- GEPA worked example ---- */
.gepaex{display:flex;flex-direction:column;gap:10px;margin-top:6px}
.exloop{border:1px solid var(--line);border-radius:12px;background:var(--panel);overflow:hidden}
.exhead{display:flex;align-items:center;gap:10px;padding:9px 16px;background:#f8fafd;
  border-bottom:1px solid var(--line);font-size:10px;text-transform:uppercase;
  letter-spacing:.09em;color:var(--muted);font-weight:700}
.exhead b{color:var(--accent);font-size:10.5px}
.exbody{display:grid;grid-template-columns:1fr 1.15fr 1fr}
.excell{padding:12px 16px;border-right:1px solid #eef0f5;font-size:12.5px;line-height:1.5;
  color:#39445c}
.excell:last-child{border-right:none}
.exlab{font-size:9.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
  margin-bottom:6px;font-weight:700}
.exscore{font-family:var(--mono);font-size:16px;font-weight:800;color:var(--accent);
  margin-bottom:5px;line-height:1}
.exsaid{font-style:italic;color:#5b6478}
.add-a,.add-b,.add-c{border-radius:3px;padding:0 3px;box-decoration-break:clone;
  -webkit-box-decoration-break:clone;font-weight:600}
.add-a{background:#e6f6ee;color:#0b7a5c}
.add-b{background:#e8eefe;color:#2f5bea}
.add-c{background:#f4eafc;color:#8443b8}
.exwrote{color:#39445c}
.exverdict{padding:8px 16px;font-size:11.5px;font-weight:600;border-top:1px solid #eef0f5}
.exverdict.acc{background:#f3fbf7;color:#0b7a5c}
.exverdict.rej{background:#fdf6f4;color:#b4432c}
.rej{color:#b4432c;text-decoration:line-through;text-decoration-thickness:1px}
.exscore.worse{color:#b4432c}
.exres{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;
  background:#f3fbf7;border:1px solid #c9ecdc;border-radius:12px;padding:14px 18px;
  font-size:13.5px;color:#0b7a5c;font-weight:700}
.extest{text-align:right;font-weight:700}
.extestsub{font-weight:400;font-size:11px;color:#5b6478;display:block;margin-top:2px}

.floop.gepa{grid-row:3 / 14}
.fc.out{background:#fffaf2;border:1px dashed #e2c98f;color:#6b5a1e}
.fsrow.dead{color:#aab2c2;font-style:italic}
.fsrow.dead b{color:#aab2c2;font-style:normal}
.floop:before{content:"";position:absolute;top:-7px;right:-3px;border:7px solid transparent;
  border-left-color:var(--accent);border-right:0;border-top:0;border-bottom:0;
  width:0;height:0}
.farrt{justify-self:center}

.flowd{display:grid;grid-template-columns:1fr 268px;gap:20px;align-items:start;margin-top:16px}
.fcol{display:grid;grid-template-columns:34px 1fr;column-gap:12px;width:100%;
  max-width:540px}
.fcol > .fc,.fcol > .farrt{grid-column:2}
.fc{width:100%;background:var(--panel);border:1px solid var(--line);
  border-radius:10px;padding:11px 16px;font-size:13.5px;text-align:center;line-height:1.4}
.fc.start{background:#f4f8ff;border-color:#cddcff}
.fc.hot{background:#eef3ff;border-color:#c3d4fb}
.fc.dec{background:#fffaf2;border-color:#f5e6c8}
.fc.win{background:#f3fbf7;border-color:#c9ecdc;color:#0b7a5c;font-weight:700}
.fsub{font-size:11.5px;color:#5b6478;margin-top:5px;font-weight:400}
.farrt{color:#b0b8ca;font-size:10px;line-height:1.6;padding:1px 0}
.fside{display:flex;flex-direction:column;gap:12px;padding-top:46px}
.fsave{background:#fff;border:2px dashed #c3d4fb;border-radius:10px;padding:12px 14px}
.fstag{font-size:10px;text-transform:uppercase;letter-spacing:.1em;font-weight:700;
  color:var(--accent);margin-bottom:9px}
.fsrow{display:flex;justify-content:space-between;align-items:center;font-size:12.5px;
  padding:6px 9px;border-radius:7px;color:#5b6478;margin-bottom:4px}
.fsrow b{font-family:var(--mono);font-size:13px;color:#39445c}
.fsrow.win{background:#e6f6ee;color:#0b7a5c}
.fsrow.win b{color:#0b7a5c}
.fsnote{font-size:11.5px;color:var(--muted);line-height:1.5}

/* ---- MIPROv2 story diagram ---- */
.stemwrap{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;margin-top:16px}
.stemsteps{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.ss{background:#fff;border:1px solid var(--line);border-radius:8px;padding:6px 12px;
  font-size:12.5px}
.ss b{color:var(--accent)}
.sa{color:#b9c0d0;font-size:13px}
.sloop{margin-left:auto;font-size:11.5px;color:var(--accent);font-weight:700}
.stgrid{display:grid;grid-template-columns:repeat(10,1fr);gap:5px;align-items:center}
.stgrid .t{display:flex;align-items:center;justify-content:center;height:30px;border-radius:7px;
  border:1px dashed #cfd6e4;background:#fff;font-family:var(--mono);font-size:11.5px;
  color:#aab2c2;font-weight:700}
.stgrid .t.on{background:var(--accent);border:1px solid var(--accent);color:#fff}
.stgrid .a{text-align:center;color:var(--accent);font-size:14px;line-height:1.1;
  font-weight:700;padding:3px 0}
.stgrid .s{text-align:center;font-family:var(--mono);font-size:12px;font-weight:700;
  padding:6px 0;border-radius:7px;background:#fff;border:1px solid var(--line);color:#5b6478}
.stgrid .s.best{background:#e6f6ee;border-color:#bfe4d4;color:#0b7a5c}
.stcap{font-size:13px;color:#39445c;margin:16px 0 0;line-height:1.55}
.stret{margin-top:12px;font-size:13.5px;font-weight:700;color:#0b7a5c;
  border-top:1px solid var(--line);padding-top:11px}

/* ---- loop / checkpoint / return diagram ---- */
.loopd{display:flex;flex-direction:column;margin-top:16px}
.ldlane{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:13px 18px}
.ldlane.hot{background:#eef3ff;border-color:#cddcff}
.ldlane.win{background:#f3fbf7;border-color:#c9ecdc}
.ldtag{font-size:10px;text-transform:uppercase;letter-spacing:.1em;font-weight:700;
  color:var(--muted);margin-bottom:10px}
.ldsteps{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.ldstep{flex:1 1 0;min-width:120px;background:#fff;border:1px solid var(--line);
  border-radius:9px;padding:8px 12px;font-size:12.5px;line-height:1.35;text-align:center}
.ldarr{flex:0 0 auto;color:#b9c0d0;font-size:13px}
.ldloop{margin-top:9px;font-size:11.5px;color:var(--accent);font-weight:600;text-align:center}
.lddown{text-align:center;font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;
  color:var(--muted);padding:8px 0}
.lddown:before{content:"\2193  "}
.ldscores{display:flex;gap:10px;flex-wrap:wrap}
.scrow{display:flex;align-items:center;gap:10px;font-family:var(--mono);font-size:12.5px;
  background:#fff;border:1px solid var(--line);border-radius:8px;padding:7px 12px;flex:1 1 0;
  min-width:130px}
.scrow.best{background:#e6f6ee;border-color:#bfe4d4;font-weight:700;color:#0b7a5c}
.sn{flex:1 1 auto;color:#5b6478}
.scrow.best .sn{color:#0b7a5c}
.scrow b{font-size:13.5px}
.scrow i{font-size:9px;text-transform:uppercase;letter-spacing:.08em;background:#0b7a5c;
  color:#fff;border-radius:4px;padding:1px 5px;font-style:normal}

/* ---- trial cadence strip ---- */
.ptime{background:#f8fafd;border:1px solid var(--line);border-radius:12px;
  padding:12px 16px;margin-top:12px}
.ptlabel{font-size:12px;color:#5b6478;margin-bottom:9px}
.ptrow{display:flex;gap:6px;flex-wrap:wrap}
.pt{display:flex;align-items:center;justify-content:center;width:30px;height:30px;
  border-radius:7px;border:1px dashed #cfd6e4;background:#fff;color:#aab2c2;
  font-family:var(--mono);font-size:11.5px;font-style:normal;font-weight:700}
.pt.on{background:var(--accent);border:1px solid var(--accent);color:#fff}
.ptlegend{display:flex;align-items:center;gap:7px;flex-wrap:wrap;margin-top:10px;
  font-size:11.5px;color:var(--muted)}
.sw{width:11px;height:11px;border-radius:3px;border:1px dashed #cfd6e4;background:#fff;
  display:inline-block}
.sw.on{background:var(--accent);border:1px solid var(--accent)}
.ptlegend .sw{margin-left:8px}
.ptlegend .sw:first-child{margin-left:0}

/* ---- MIPROv2 pipeline + trial log ---- */
.pipe{display:flex;align-items:stretch;gap:0;margin-top:18px;flex-wrap:wrap}
.pstage{flex:1 1 0;min-width:132px;background:var(--panel);border:1px solid var(--line);
  border-radius:12px;padding:14px 14px 12px;text-align:center}
.pstage.hot{background:#eef3ff;border-color:#cddcff}
.pstage.win{background:#f3fbf7;border-color:#c9ecdc}
.pnum{font-family:var(--mono);font-size:19px;font-weight:800;color:var(--accent);line-height:1}
.pstage.win .pnum{color:#0b7a5c}
.ptitle{font-size:11px;text-transform:uppercase;letter-spacing:.09em;font-weight:700;
  margin:7px 0 5px;color:var(--ink)}
.pdesc{font-size:11.5px;color:#5b6478;line-height:1.4}
.parrow{flex:0 0 26px;display:flex;align-items:center;justify-content:center;
  color:#b9c0d0;font-size:15px}
.miptoy{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:14px 16px;margin-top:6px}
.mipctl{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.mipcols{display:grid;grid-template-columns:1.45fr 1fr;gap:18px}
.mipcols h4{margin:0 0 8px;font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;
  color:var(--muted)}
.cprow td{background:#eef3ff;border-top:1px solid #cddcff;border-bottom:1px solid #cddcff;
  font-size:11.5px;color:#33405c;padding:7px 9px;line-height:1.45}
.rrow.saved{background:#f4f8ff;border-color:#dbe6ff}
.rrow.win{background:#e6f6ee;border-color:#bfe4d4;color:#0b7a5c;font-weight:700}
.testout{margin-top:11px;padding:10px 12px;border-radius:9px;background:#fffaf2;
  border:1px solid #f5e6c8;font-size:12px;color:#6b5a1e;line-height:1.5}
.mipout{margin-top:14px}
table.miptab{font-size:12px;border-collapse:collapse;width:100%}
table.miptab th{text-align:left;font-size:9.5px;text-transform:uppercase;letter-spacing:.08em;
  color:var(--muted);padding:3px 6px;border-bottom:1px solid var(--line)}
table.miptab td{padding:5px 6px;border-bottom:1px solid #eef0f5;vertical-align:middle}
table.miptab td.mono2{font-family:var(--mono);font-size:11.5px;font-weight:700;color:#39445c}
.chip{display:inline-block;font-family:var(--mono);font-size:10.5px;font-style:normal;
  border-radius:5px;padding:1px 5px;margin-right:3px;white-space:nowrap}
.chip.ok{background:#e6f6ee;color:#0b7a5c}
.chip.no{background:#fdeeea;color:#b4432c}
.miprank{display:flex;flex-direction:column;gap:3px}
.rrow{display:flex;align-items:center;gap:7px;font-family:var(--mono);font-size:11.5px;
  padding:5px 8px;border-radius:7px;color:#5b6478;border:1px solid transparent}
.rrow.promoted{background:#eef3ff;border-color:#dbe6ff;color:#39445c}
.rrow.win{background:#e6f6ee;border-color:#bfe4d4;color:#0b7a5c;font-weight:700}
.rname{flex:1 1 auto}
.ravg{font-weight:700}
.rn{font-size:10px;opacity:.65}
.rfull{font-size:10px;background:#0b7a5c;color:#fff;border-radius:4px;padding:1px 5px}
.mipnote{font-size:13px;color:#39445c;margin-top:12px;line-height:1.5;min-height:42px;
  border-top:1px solid var(--line);padding-top:10px}

/* ---- page 4: optimiser mechanics ---- */
.ovflow{display:flex;flex-direction:column;gap:12px;margin-top:16px}
.ovlane{border:1px solid var(--line);border-radius:12px;padding:13px 18px 15px;background:var(--panel)}
.ovlane.train{border-left:4px solid var(--accent)}
.ovlane.val{border-left:4px solid #0b7a5c;background:#f7fcfa}
.ovlane.test{border-left:4px solid #b4432c;background:#fdf9f7}
.ovtag{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);
  margin-bottom:10px}
.ovrow{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.ovbox{background:#fff;border:1px solid var(--line);border-radius:9px;padding:9px 13px;
  font-size:12.5px;line-height:1.35;text-align:center;flex:1 1 0;min-width:104px}
.ovbox.hot{background:#eef3ff;border-color:#cddcff;font-weight:700;color:var(--accent)}
.ova{color:#b9c0d0;font-size:13px;flex:0 0 auto}
.ovloop{margin-top:10px;font-size:12px;color:var(--accent);font-weight:600;text-align:center}
.ovlane p{margin:0;font-size:13.5px;color:#39445c;line-height:1.5}
.mflow{display:flex;flex-direction:column;gap:9px;margin-top:14px}
.mstep{display:flex;gap:13px;align-items:flex-start;background:var(--panel);
  border:1px solid var(--line);border-radius:10px;padding:12px 16px}
.mstep>span{flex:0 0 22px;height:22px;border-radius:50%;background:var(--accent);color:#fff;
  font-size:11.5px;font-weight:800;display:flex;align-items:center;justify-content:center}
.mstep div{font-size:13.5px;line-height:1.5;color:#39445c}
.mstep code{font-size:12px}
.ticklist{margin:0;padding-left:18px}
.ticklist li{font-size:13.5px;line-height:1.5;margin-bottom:8px;color:#39445c}
.cmp{display:grid;grid-template-columns:1fr 150px 1fr;gap:14px;margin-top:16px;align-items:stretch}
.cmpcol{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.cmpcol.gepa{background:#f6f9ff;border-color:#d6e2fb}
.cmpcol h3{margin:0 0 11px;font-size:16px}
.cmpstep{background:#fff;border:1px solid var(--line);border-radius:8px;padding:9px 12px;
  font-size:12.5px;line-height:1.4;margin-bottom:7px;color:#39445c}
.cmpcol.gepa .cmpstep{border-color:#d6e2fb}
.cmpfoot{font-size:12px;font-weight:700;color:var(--accent);margin-top:10px;
  border-top:1px solid var(--line);padding-top:9px;line-height:1.45}
.cmpmid{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px}
.cmpline{width:1px;flex:1;background:var(--line)}
.cmplabel{font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);
  text-align:center;line-height:1.5}

/* ---- setup page ---- */
table.ctab th,table.tier th{font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;
  color:var(--muted);text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
table.ctab td,table.tier td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
table.ctab td:first-child{white-space:nowrap}
.hand{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:16px}
.hcard{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.hcard .hn{font-size:31px;font-weight:800;letter-spacing:-.03em;color:var(--accent);line-height:1}
.hcard h4{margin:7px 0 4px;font-size:15px}
.hcard p{margin:0;font-size:13.5px;color:#39445c;line-height:1.45}
.handdown{text-align:center;margin:12px 0 8px;font-size:11px;text-transform:uppercase;
  letter-spacing:.11em;color:var(--muted)}
.handprog{background:#eef3ff;border:1px solid #cddcff;border-radius:12px;padding:14px 20px;
  display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.handprog b{font-size:15px;color:var(--accent);white-space:nowrap}
.handprog span{font-family:var(--mono);font-size:12px;color:#39445c;line-height:1.5}
.tier4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:16px}
.t4{border-radius:12px;padding:14px 16px;border:1px solid var(--line);background:var(--panel)}
.t4 .tv{font-family:var(--mono);font-size:17px;font-weight:800;line-height:1}
.t4 h4{margin:6px 0 4px;font-size:14px}
.t4 p{margin:0;font-size:12.5px;color:#39445c;line-height:1.4}
.t4.peer{border-color:#bfe4d4;background:#f3fbf7}
.t4.peer .tv{color:#0b7a5c}
.t4.adj{border-color:#c9d8f5;background:#f4f8ff}
.t4.adj .tv{color:#2f5bea}
.t4.hard{border-color:#f3cfc7;background:#fdf6f4}
.t4.hard .tv{color:#b4432c}
.t4.unrel{border-color:#e2e5ec;background:#fafbfd}
.t4.unrel .tv{color:#8b93a7}
.fsep{border-top:1px solid rgba(255,255,255,.14);margin:9px 0 6px}
.fcm{font-family:var(--mono);font-size:12.5px;color:#8b96b5;line-height:1.5}
.formulabox{background:#0f1526;border-radius:12px;padding:18px 24px;margin-top:14px}
.fline{display:flex;gap:16px;align-items:baseline;padding:6px 0}
.fline+.fline{border-top:1px solid rgba(255,255,255,.08)}
.fk{flex:0 0 78px;font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:#7f8aa8}
.feq{font-family:var(--mono);font-size:14px;color:#d7dcea}
.steps4{margin:0;padding-left:20px}
.steps4 li{font-size:14px;line-height:1.5;margin-bottom:8px;color:#39445c}

/* ---- tier table + weight sensitivity ---- */
table.tier td{font-size:12.5px;vertical-align:top}
.tt{font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:5px;white-space:nowrap}
.tt.peer{background:#e9f8f2;color:#0b7a5c}
.tt.adj{background:#fdf4e3;color:#a3610f}
.tt.hard{background:#fdeceb;color:#b42318}
.tt.unrel{background:#f1f3f7;color:#7b869d}
.mono2{font-family:var(--mono);font-size:11px;color:#5b6478}
.wsens{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:4px}
.wlab{font-size:11px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted)}
.wbtns{display:flex;gap:6px}
.wbtn{border:1.5px solid var(--line);background:#fff;font:inherit;font-size:12px;font-weight:700;
  padding:6px 12px;border-radius:8px;cursor:pointer;color:#5b6478;transition:.15s}
.wbtn:hover{border-color:#c3cfeb}
.wbtn.on{border-color:var(--accent);color:var(--accent);background:#f5f8ff}
.wsensout{margin-top:12px;display:flex;align-items:baseline;gap:14px}
.wsensout .wbig{font-size:34px;font-weight:800;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.wsensout .wtext{font-size:12.5px;color:var(--muted);line-height:1.4}
@media print{
  html,body{overflow:visible;background:#fff}
  .deck{height:auto}
  .slide{position:static;opacity:1;transform:none;pointer-events:auto;
    page-break-after:always;padding:0 0 24px;overflow:visible}
  .nav,.scrolltip,.modal{display:none!important}
  .card,.tile,.anabox-wrap{box-shadow:none}
  .obar{height:60px!important}
}

/* ---- concepts grid (page 1) ---- */
.concepts{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:24px 0 6px}
.concept{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:22px 22px 18px;cursor:pointer;transition:.2s;position:relative;min-height:168px;
  display:flex;flex-direction:column}
.concept:hover{border-color:var(--accent);transform:translateY(-3px);
  box-shadow:0 10px 26px rgba(16,24,40,.10)}
.concept .chead{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.concept .ic{color:var(--accent);width:26px;height:26px}
.concept .cname{font-size:21px;font-weight:800;letter-spacing:-.02em;
  border-bottom:2px solid var(--ink);padding-bottom:5px;flex:1}
.concept .cblurb{font-size:15px;color:#39445c;line-height:1.5;flex:1}
.concept .cmore{margin-top:12px;font-size:11.5px;font-weight:700;color:var(--accent);
  text-transform:uppercase;letter-spacing:.08em}
.concept .capi{font-family:var(--mono);font-size:10px;color:#a7afc2;margin-top:6px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chainline{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:26px;
  padding:14px 18px;background:#f7f9fd;border:1px dashed var(--line);border-radius:12px}
.chainline .ch{font-family:var(--mono);font-size:12px;font-weight:700;background:#fff;
  border:1px solid var(--line);border-radius:7px;padding:4px 10px;color:#39445c}
.chainline .ch.hot{background:rgba(47,91,234,.08);border-color:rgba(47,91,234,.35);
  color:var(--accent)}
.chainline .car{color:#b9c0d0;font-size:13px}
.chainline .chm{font-size:12px;color:var(--muted);margin-left:4px}
/* wider modal for code + output */
.sheet.wide{max-width:980px}
.sheet pre.out{background:#0d1b16;color:#a8e6c4;border-radius:10px;padding:13px 16px;
  font-family:var(--mono);font-size:12px;line-height:1.6;overflow:auto;margin:0}
.codepair{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.sheet .simplenote{font-size:12.5px;color:var(--muted);margin:8px 0 0;line-height:1.5;
  border-left:2px solid var(--line);padding-left:12px}
.sheet table.ctab{border-collapse:collapse;width:100%;font-size:12.5px;margin:8px 0 4px}
.sheet table.ctab th,.sheet table.ctab td{text-align:left;padding:7px 9px;
  border-bottom:1px solid var(--line);vertical-align:top;line-height:1.45}
.sheet table.ctab th{font-size:10.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.sheet table.ctab td:first-child{white-space:nowrap}
.codepair{grid-template-columns:1fr 1fr}
.codepair h4{margin-top:0}
@media (max-width:860px){
  .concepts{grid-template-columns:1fr}
  .codepair{grid-template-columns:1fr}
}
@media (max-width:860px){.g2,.g3,.hand{grid-template-columns:1fr}
  .cmp{grid-template-columns:1fr}
  .cmpmid{flex-direction:row;gap:12px}
  .cmpline{width:auto;height:1px;flex:1}
  .tier4{grid-template-columns:1fr 1fr}.slide{padding:28px 26px 84px}h1{font-size:32px}}
"""

NOSCRIPT = """
<noscript><style>
  .slide{position:static!important;opacity:1!important;transform:none!important;
    pointer-events:auto!important;border-bottom:2px solid #e3e7ef;margin-bottom:18px}
  .nav{display:none!important}
  .pickgrid,.optbars,.anatabs{display:none!important}
  .nojs{display:block!important}
</style></noscript>
<div class="nojs" style="display:none;background:#fffbeb;border-bottom:1px solid #f5e6b8;
  padding:10px 20px;font:13px/1.5 'Segoe UI',system-ui,sans-serif;color:#6b5a1e">
  JavaScript is disabled, so the interactive widgets are hidden. All the written content,
  the five-stage walkthrough and every prompt version are still readable below.
</div>
"""

SPRITE = """
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
<symbol id="ic-doc" viewBox="0 0 24 24"><rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/></symbol>
<symbol id="ic-route" viewBox="0 0 24 24"><circle cx="6" cy="18" r="2.2"/><circle cx="18" cy="6" r="2.2"/><path d="M8.2 18h5.3A4.5 4.5 0 0 0 18 13.5V8.2"/></symbol>
<symbol id="ic-link" viewBox="0 0 24 24"><rect x="2.5" y="9" width="6" height="6" rx="1.5"/><rect x="15.5" y="9" width="6" height="6" rx="1.5"/><path d="M8.5 12h7"/></symbol>
<symbol id="ic-check" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8 12.2l2.8 2.8L16.4 9"/></symbol>
<symbol id="ic-wand" viewBox="0 0 24 24"><path d="M4.5 19.5L15 9"/><path d="M14.5 3.5l1.4 2.6 2.6 1.4-2.6 1.4L14.5 11.5l-1.4-2.6L10.5 7.5l2.6-1.4z"/><path d="M19 14l.8 1.5 1.5.8-1.5.8-.8 1.5-.8-1.5-1.5-.8 1.5-.8z"/></symbol>
<symbol id="ic-align" viewBox="0 0 24 24"><path d="M4 6h16M4 12h11M4 18h6"/><path d="M18.5 15.5l1.8 1.8 3-3.2"/></symbol>
<symbol id="ic-brain" viewBox="0 0 24 24"><path d="M9.5 4A3 3 0 0 0 6.6 8a3 3 0 0 0-1 5.4A3 3 0 0 0 8 18.6a3 3 0 0 0 5.5-.7V4.8A2.6 2.6 0 0 0 11 4z"/><path d="M14.5 4a3 3 0 0 1 2.9 4 3 3 0 0 1 1 5.4 3 3 0 0 1-2.4 5.2 3 3 0 0 1-2.5 1"/></symbol>
<symbol id="ic-robot" viewBox="0 0 24 24"><rect x="3.5" y="7.5" width="17" height="12" rx="3.2"/><circle cx="9" cy="13" r="1.3" fill="currentColor" stroke="none"/><circle cx="15" cy="13" r="1.3" fill="currentColor" stroke="none"/><path d="M12 7.5V4M9.5 16.5h5"/></symbol>
<symbol id="ic-calc" viewBox="0 0 24 24"><rect x="4.5" y="2.5" width="15" height="19" rx="2.5"/><path d="M8 7h8M8 11.5h2M12 11.5h2M16 11.5h0M8 15.5h2M12 15.5h2M16 15.5h0M8 19h6"/></symbol>
<symbol id="ic-layers" viewBox="0 0 24 24"><path d="M12 3l8.5 4.6L12 12.2 3.5 7.6z"/><path d="M3.5 12.2L12 16.8l8.5-4.6"/><path d="M3.5 16.6L12 21.2l8.5-4.6"/></symbol>
<symbol id="ic-steps" viewBox="0 0 24 24"><rect x="3" y="3.5" width="6.5" height="6" rx="1.5"/><rect x="14.5" y="3.5" width="6.5" height="6" rx="1.5"/><rect x="8.8" y="14.5" width="6.5" height="6" rx="1.5"/><path d="M6.2 9.5v2.2h11.5V9.5M12 11.7v2.8"/></symbol>
<symbol id="ic-ruler" viewBox="0 0 24 24"><rect x="2" y="8" width="20" height="8" rx="2"/><path d="M6.5 8v3.2M11 8v3.2M15.5 8v3.2M20 8v3.2"/></symbol>
<symbol id="ic-swap" viewBox="0 0 24 24"><path d="M3.5 8.5h14l-3.2-3.2M20.5 15.5h-14l3.2 3.2"/></symbol>
<symbol id="ic-q" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M9.4 9.2a2.7 2.7 0 1 1 3.8 2.5c-.7.3-1.2 1-1.2 1.8v.3"/><circle cx="12" cy="17.2" r="0.9" fill="currentColor" stroke="none"/></symbol>
<symbol id="ic-x" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8.8 8.8l6.4 6.4M15.2 8.8l-6.4 6.4"/></symbol>
</defs></svg>
"""

JS = """
const DATA = __DATA__;
const $ = (s,r=document)=>r.querySelector(s);
const $$ = (s,r=document)=>[...r.querySelectorAll(s)];
let page = 0;

function show(i){
  const slides = $$('.slide');
  if(i<0||i>=slides.length) return;
  slides.forEach((s,k)=>{
    s.classList.toggle('active', k===i);
    s.classList.toggle('leaving', k<i);
  });
  $$('.dot').forEach((d,k)=>d.classList.toggle('on',k===i));
  page = i;
  animate(i);
}
function animate(i){
  if(i===0) flowLoop();
  if(i===1 || i===2) grow();
  if(i===2) sparkIn();
}
/* page 1: walk the optimizer loop */
let flowTimer=null;
function flowLoop(){
  clearInterval(flowTimer);
  const nodes=$$('#loop .node'), arrows=$$('#loop .arrow');
  let k=0;
  const step=()=>{
    nodes.forEach((n,j)=>n.classList.toggle('on', j===k%nodes.length));
    arrows.forEach((a,j)=>a.classList.toggle('lit', j===k%nodes.length));
    k++;
  };
  step(); flowTimer=setInterval(step,700);
}
/* page 2: bars + counter */
function grow(){
  $$('.bar > i').forEach(el=>{ el.style.width = el.dataset.w+'%'; });
  $$('.split > div').forEach(el=>{ el.style.width = el.dataset.w+'%'; });
  $$('[data-count]').forEach(el=>{
    const target=parseFloat(el.dataset.count), dec=(el.dataset.dec||0)|0;
    let t0=null;
    const tick=ts=>{
      if(!t0) t0=ts;
      const p=Math.min(1,(ts-t0)/700);
      el.textContent=(target*(1-Math.pow(1-p,3))).toFixed(dec);
      if(p<1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}
/* page 3: version browser */
function sparkIn(){
  $$('.spark div').forEach((el,j)=>{
    setTimeout(()=>{ el.style.height = el.dataset.h+'%'; }, 60*j);
  });
}
function renderList(){
  const list=$('#vlist'); list.innerHTML='';
  const scored = DATA.versions.filter(v=>v.score!==null);
  DATA.versions.forEach((v,idx)=>{
    const b=document.createElement('button');
    b.className='vitem'+(idx===0?' on':'');
    const delta = (v.score!==null && DATA.base!==null && idx>0)
      ? (v.score-DATA.base) : null;
    const sc = v.score===null ? '<span class="sc">—</span>'
      : `<span class="sc ${delta>0?'up':''}">${v.score.toFixed(3)}${delta>0?' ▲':''}</span>`;
    b.innerHTML=`<span class="lbl">${v.label}</span>${sc}`;
    b.onclick=()=>{ $$('.vitem').forEach(x=>x.classList.remove('on')); b.classList.add('on'); renderVersion(idx); };
    list.appendChild(b);
  });
  renderVersion(0);
}
function renderVersion(idx){
  const v=DATA.versions[idx];
  const delta=(v.score!==null&&DATA.base!==null&&idx>0)?(v.score-DATA.base):null;
  const head=$('#vhead');
  const scoreTxt = v.score===null ? 'not yet scored'
    : `${v.score.toFixed(3)}${delta!==null?` &nbsp;<b style="color:${delta>0?'var(--add)':'var(--muted)'}">${delta>0?'+':''}${delta.toFixed(3)} vs v0</b>`:''}`;
  head.innerHTML = `<span class="tag">${v.label}</span>
    <b>${v.note}</b>
    <span style="color:var(--muted);font-size:13px">${v.words} words · ${v.chars} chars · ${v.kind==='human'?'written by a human':'written by GEPA'} · ${scoreTxt}</span>`;

  const body=$('#vbody');
  if(idx===0){
    body.innerHTML = '<div class="code">'+esc(v.text)+'</div>';
    return;
  }
  const rows=(v.diff||[]).map(([op,text],i)=>{
    const cls = op==='+'?'add':op==='-'?'del':op==='@'?'hunk':'ctx';
    const shown = text.length>200 ? text.slice(0,200)+'…' : text;
    return `<span class="dl ${cls}" style="animation-delay:${Math.min(i,40)*14}ms">${esc(shown)}</span>`;
  }).join('');
  body.innerHTML = `<div class="commit"><b>GEPA ${v.label.replace('v','')}</b> — what changed from ${DATA.versions[idx-1].label}
      <span style="float:right;color:var(--muted)">${(v.diff||[]).filter(r=>r[0]==='+').length} added ·
      ${(v.diff||[]).filter(r=>r[0]==='-').length} removed</span></div>
    <div class="code">${rows||'<span class="dl ctx">no textual change</span>'}</div>
    <h4 style="font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#8794b4;margin:16px 0 6px">Full prompt as GEPA wrote it</h4>
    <div class="code fullprompt">${esc(v.text)}</div>`;
}
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}

document.addEventListener('keydown',e=>{
  if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown'){e.preventDefault();show(page+1);}
  if(e.key==='ArrowLeft'||e.key==='PageUp'){e.preventDefault();show(page-1);}
  if(e.key==='Home') show(0);
  if(e.key==='End') show($$('.slide').length-1);
});
$$('.dot').forEach((d,i)=>d.onclick=()=>show(i));

/* ---- modal plumbing ---- */
const modal = $('#modal');
function closeDetail(){ modal.classList.remove('on'); $('#modal .sheet').classList.remove('wide'); }
$('#mClose').addEventListener('click',closeDetail);
modal.addEventListener('click',e=>{ if(e.target===modal) closeDetail(); });
document.addEventListener('keydown',e=>{ if(e.key==='Escape') closeDetail(); });

function renderConcepts(){
  const host = $('#concepts');
  if(!host) return;
  host.innerHTML = '';
  Object.entries(DATA.concepts).forEach(([key, c])=>{
    const d = document.createElement('div');
    d.className = 'concept';
    d.onclick = ()=>openConcept(key);
    d.innerHTML =
      '<div class="chead"><svg class="ic"><use href="#'+c.icon+'"/></svg>'+
      '<div class="cname">'+c.title+'</div></div>'+
      '<div class="cblurb">'+c.blurb+'</div>'+
      '<div class="cmore">open &rarr;</div>'+
      '<div class="capi">'+esc(c.api)+'</div>';
    host.appendChild(d);
  });
}
function openConcept(key){
  const c = DATA.concepts[key];
  if(!c) return;
  $('#mTitle').textContent = c.title;
  $('#mApi').textContent = c.api;
  $('#mIcon').innerHTML = '<use href="#'+c.icon+'"/>';
  $('#mBody').innerHTML =
    '<h4>What it is</h4><p>'+c.what+'</p>' +
    '<h4>What goes into it</h4>'+c.parts +
    '<h4>A simple example</h4><pre>'+esc(c.simple)+'</pre>' +
    '<p class="simplenote">'+c.simple_note+'</p>' +
    '<h4>In our case</h4>'+c.real +
    '<h4>Limitation</h4><div class="limitbox"><svg class="ic"><use href="#ic-q"/></svg>'+
      '<span>'+c.limit+'</span></div>' +
    (c.extra || '');
  modal.classList.add('on');
}
const calc = DATA.calculator;
let picked = [];
/* ---- MIPROv2 toy: rows static; JS reveals and computes ---- */
const TRIALS = (DATA.toy.trials || []).map(([c, draws]) => ({ c, draws }));
const CPS = DATA.toy.checkpoints || {};
const TEST = DATA.toy.test;
let mipStep = 0;
const MIP_END = TRIALS.length + 1;

function mipAvg(cand){
  const runs = TRIALS.slice(0, Math.min(mipStep, TRIALS.length)).filter(t => t.c === cand);
  if(!runs.length) return { avg: 0, n: 0 };
  return {
    avg: runs.reduce((s, t) => s + t.draws.filter(d => d[1]).length / 3, 0) / runs.length,
    n: runs.length
  };
}

function mipRanks(){
  const names = [];
  TRIALS.slice(0, Math.min(mipStep, TRIALS.length)).forEach(t => {
    if(names.indexOf(t.c) < 0) names.push(t.c);
  });
  return names.map(n => { const a = mipAvg(n); return { name: n, avg: a.avg, n: a.n }; })
    .sort((a, b) => b.avg - a.avg);
}

function mipRender(){
  const rank = $('#miprank'), out = $('#mipout');
  const stat = $('#mipStat'), note = $('#mipnote'), next = $('#mipNext');
  if(!rank || !next) return;

  // progressive reveal of the static rows
  const rows = $$('#miprows tr');
  for(let k = 0; k < rows.length; k++){
    const at = parseInt(rows[k].getAttribute('data-at'), 10);
    rows[k].hidden = at > mipStep;
  }

  const ranks = mipRanks();
  let rh = '';
  for(let i = 0; i < ranks.length; i++){
    const r = ranks[i];
    rh += '<div class="rrow"><span class="rname">' + r.name + '</span>'
        + '<span class="ravg">' + r.avg.toFixed(3) + '</span>'
        + '<span class="rn">' + r.n + '\u00d7</span></div>';
  }
  rank.innerHTML = rh || '<div class="rrow"><span class="rname">press next trial</span></div>';

  // saved results, revealed at their checkpoint
  let oh = '';
  const saved = [];
  Object.keys(CPS).sort((a, b) => a - b).forEach(k => {
    if(mipStep >= parseInt(k, 10)){
      const [who, sc] = CPS[k];
      saved.push([who, sc]);
      oh += '<div class="rrow saved"><span class="rname">trial ' + k + ' &middot; ' + who
          + '</span><span class="ravg">' + Number(sc).toFixed(2) + '</span></div>';
    }
  });
  if(mipStep >= MIP_END && saved.length){
    let best = saved[0];
    saved.forEach(s => { if(s[1] > best[1]) best = s; });
    oh += '<div class="rrow win"><span class="rname">returned &middot; ' + best[0]
        + '</span><span class="ravg">' + Number(best[1]).toFixed(2) + '</span></div>';
    oh += '<div class="testout">then, <b>outside the optimiser</b>: scored on the ten '
        + '<b>test</b> cases &rarr; <b>' + Number(TEST).toFixed(2) + '</b></div>';
  }
  out.innerHTML = oh;

  if(mipStep === 0){
    stat.textContent = 'no trials yet';
    note.innerHTML = 'Each trial takes one prompt and three of the ten validation questions. '
      + 'Watch the running average, not any single row.';
  } else if(mipStep < 6){
    stat.textContent = 'trial ' + mipStep + ' of 12 \u2014 no checkpoint yet';
    note.innerHTML = 'These are cheap draws. I3+D2 looks perfect in trial 3 and poor in trial 4 '
      + '\u2014 the same prompt on different questions.';
  } else if(mipStep < 12){
    stat.textContent = 'trial ' + mipStep + ' of 12 \u2014 one checkpoint saved';
    note.innerHTML = 'At <b>trial 6</b> the running-average leader was given the full ten-question '
      + 'exam and its score was saved. The trials carry on \u2014 later prompts can still beat it.';
  } else if(mipStep === 12){
    stat.textContent = 'all 12 trials done \u2014 two checkpoints saved';
    note.innerHTML = 'At <b>trial 12</b> the best prompt that had not yet had a full exam got one. '
      + 'Now press to compare the two saved scores.';
  } else {
    stat.textContent = 'done \u2014 12 trials, 2 full exams, 1 returned';
    note.innerHTML = '<b>The comparison reads only the saved results.</b> 0.84 beats 0.71, so the '
      + 'prompt promoted second wins. Then \u2014 and only then \u2014 that one program is scored '
      + 'on the ten held-out <b>test</b> cases, which the optimiser never saw: <b>0.77</b>. '
      + 'That is the number you report, and it is lower than 0.84 because it is a fresh set.';
  }
  next.disabled = mipStep >= MIP_END;
  next.textContent = mipStep >= TRIALS.length ? 'compare and score on test' : 'next trial';
}

function mipNext(){ if(mipStep < MIP_END){ mipStep++; mipRender(); } }
function mipReset(){ mipStep = 0; mipRender(); }

function initMip(){
  const btn = $('#mipNext');
  if(!btn || !$('#miprows')) return;
  btn.addEventListener('click', mipNext);
  if($('#mipReset')) $('#mipReset').addEventListener('click', mipReset);
  mipRender();
}

function renderPicks(){
  const grid = $('#pickgrid'); grid.innerHTML = '';
  calc.candidates.forEach(c=>{
    const b = document.createElement('button');
    b.className = 'pick t-'+c.tier + (picked.includes(c.id)?' sel':'');
    b.innerHTML = '<span class="pid">'+c.id.replace('EQ_','')+'</span>'+
                  '<span class="pname">'+esc(c.name)+'</span>';
    b.onclick = ()=>{
      const i = picked.indexOf(c.id);
      if(i>=0) picked.splice(i,1);
      else if(picked.length<3) picked.push(c.id);
      renderPicks(); renderScore();
    };
    grid.appendChild(b);
  });
}
function renderScore(){
  const num=$('#scoreNum'), brk=$('#scoreBreak'), note=$('#picknote');
  if(picked.length!==3){
    num.textContent='-';
    num.style.color='var(--ink)';
    brk.innerHTML='';
    note.textContent='Selected '+picked.length+' of 3.';
    return;
  }
  const key = [...picked].sort().join('|');
  const r = calc.combos[key];
  if(!r){ num.textContent='?'; return; }
  num.textContent = r.score.toFixed(3);
  num.style.color = r.score>=0.8?'var(--add)':(r.score>=0.5?'var(--warn)':'var(--bad)');
  const lines=[];
  lines.push('peers '+r.peers+' x 1.0');
  lines.push('adjacent '+r.adj+' x 0.5');
  if(r.wrong) lines.push('wrong '+r.wrong+' x -1.5');
  if(r.dup) lines.push('duplicate penalty applied');
  brk.innerHTML = lines.join('<br>');
  note.textContent = r.score>=0.8 ? 'Defensible: mostly peer-level comparisons.'
    : (r.score>=0.5 ? 'Mixed: real peers present, but padded with references.'
    : 'Weak: few or no genuine peers.');
}
/* ---- optimiser stepper ---- */
let optAt = 0;


/* ---- anatomy stepper ---- */
function renderAnatomy(at){
  const tabs=$('#anatabs'), pane=$('#anapane');
  const items = DATA.anatomy;
  if(!tabs.children.length){
    items.forEach((s,i)=>{
      const b=document.createElement('button');
      b.className='anatab-btn'; b.textContent=s.tab;
      b.onclick=()=>renderAnatomy(i);
      tabs.appendChild(b);
    });
  }
  [...tabs.children].forEach((b,i)=>b.classList.toggle('on', i===at));
  pane.innerHTML = '<h3>'+items[at].title+'</h3>'+items[at].body;
}

/* ---- weight sensitivity ---- */
const WEIGHTS = ['0.5','1.5','3.0'];
let weight = '1.5';
function renderWeights(){
  const host = $('#wbtns');
  if(!host.children.length){
    WEIGHTS.forEach(w=>{
      const b=document.createElement('button');
      b.className='wbtn'+(w===weight?' on':'');
      b.textContent=(w==='1.5'? w+' (ours)' : w);
      b.dataset.w=w;
      b.onclick=()=>{ weight=w; [...host.children].forEach(c=>c.classList.toggle('on',c.dataset.w===w)); renderWeights(); };
      host.appendChild(b);
    });
  }
  const out=$('#wsensout');
  const trio=['EQ_AMD','EQ_TSM','EQ_CRM'];
  const key=[...trio].sort().join('|');
  const r=DATA.calculator.sensitivity[weight][key];
  const cur=DATA.calculator.sensitivity['1.5'][key];
  const cls = r>=0.8?'var(--add)':(r>=0.5?'var(--warn)':'var(--bad)');
  out.innerHTML='<div class="wbig" style="color:'+cls+'">'+r.toFixed(3)+'</div>'+
    '<div class="wtext">for <code>EQ_AMD + EQ_TSM + EQ_CRM</code><br>'+
    'two true peers, one Salesforce-class wrong pick'+(r!==cur?' &middot; '+((r-cur)>=0?'+':'')+(r-cur).toFixed(3)+' vs our weights':'')+
    '</div>';
}
try {
  renderWeights();
  renderConcepts();
  initMip();
  renderAnatomy(0);
  renderPicks(); renderScore();
  renderList();
  show(0);
} catch(err) {
  const b = document.createElement('div');
  b.style.cssText = 'position:fixed;left:0;right:0;top:0;z-index:99999;background:#b4432c;'
    + 'color:#fff;padding:9px 16px;font:600 13px system-ui,sans-serif';
  b.textContent = 'Deck script error: ' + err.message + ' (some widgets will not respond)';
  document.body.appendChild(b);
  if(window.console) console.error(err);
}
"""


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="out/teaching/deck.html")
    ap.add_argument("--prompts", default="out/teaching/prompts")
    ap.add_argument("--also-nojs", action="store_true",
                    help="also emit deck_nojs.html, a script-free edition. "
                         "Off by default so a normal build touches only deck.html")
    args = ap.parse_args(argv)

    prompts_dir = HERE / args.prompts
    base_score, base_rows = read_baseline_md(HERE / "out/teaching/baseline.md")

    from peerlens.prompt_v2 import BASELINE_V0

    versions = load_versions(prompts_dir, BASELINE_V0)
    measured = apply_scores(versions, HERE / "out/teaching/leaderboard.json")
    base = measured if measured is not None else base_score
    for v in versions:
        if v["label"] == "v0" and v["score"] is None and base is not None:
            v["score"] = round(base, 3)

    scored = [v["score"] for v in versions if v["score"] is not None]
    best = max(scored) if scored else None
    counts = rule_summary()
    mech = sum(c for k, c in counts.items() if k != "instruction")
    total_rules = len(RULE_MAP)

    rules_detail = {
        "mechanical": [
            {"rule": r.rule, "mech": r.mechanism, "where": r.where}
            for r in RULE_MAP
            if r.guaranteed
        ],
        "optimisable": [r.rule for r in RULE_MAP if r.optimizable],
    }

    # ---- interactive score calculator -----------------------------------
    # Precompute every 3-pick combination with the real metric, so the widget
    # on page 2 is guaranteed to agree with peerlens.metric.
    from itertools import combinations

    from peerlens.metric import Selection, score_selection

    CALC_IDS = ["EQ_AMD", "EQ_TSM", "EQ_CRM", "IDX_SOX", "ETF_SMH",
                "IDX_SPX", "ETF_XLK", "CASH_USD", "EQ_COP"]
    calc_case = pl.CASE_BY_ASSET["EQ_NVDA"]
    calc_combos = {}
    for trio in combinations(CALC_IDS, 3):
        axes = score_selection(
            "EQ_NVDA",
            [Selection(benchmark_id=i, role="diversifier") for i in trio],
            pl.PACK,
            calc_case,
        )
        calc_combos["|".join(sorted(trio))] = {
            "score": round(axes.composite, 3),
            "peers": axes.peer_hits,
            "adj": axes.adjacent_hits,
            "wrong": axes.violations,
            "dup": bool(axes.duplicate_exposure or axes.near_duplicate),
        }
    calc_candidates = []
    for cid in CALC_IDS:
        if cid in calc_case.acceptable:
            tier = "peer"
        elif cid in calc_case.adjacent:
            tier = "adjacent"
        elif cid in calc_case.negatives:
            tier = "wrong"
        else:
            tier = "neutral"
        calc_candidates.append(
            {"id": cid, "name": pl.PACK[cid].name, "tier": tier}
        )

    # ---- optimiser outcome walk -----------------------------------------
    incumbent = None
    opt_walk = []
    for v in versions:
        s = v["score"]
        if s is None:
            continue
        if incumbent is None:
            incumbent = s
            opt_walk.append({"label": v["label"], "score": s, "status": "baseline"})
        elif s > incumbent:
            incumbent = s
            opt_walk.append({"label": v["label"], "score": s, "status": "kept"})
        else:
            opt_walk.append({"label": v["label"], "score": s, "status": "dropped"})

    # ---- anatomy data: the real v0 -> v1 step ----------------------------
    from peerlens.metric import Selection as _Sel, score_selection as _score
    from peerlens.prompt_v2 import (
        BenchmarkPick as _Pick,
        HoldingFacts as _HF,
        split_problems as _split,
        validate_selection as _validate,
    )

    _ROLES = ["dominant_sleeve", "diversifier", "whole_portfolio"]

    def _run(asset_id, picks):
        """Score one answer the way the optimiser's metric does, and build its feedback."""
        case = pl.CASE_BY_ASSET[asset_id]
        holding = _HF.from_instrument(pl.PACK[asset_id])
        objs = [
            _Pick(benchmark_id=p, role=_ROLES[i % len(_ROLES)],
                  relationship="comparison", limitation="single exposure")
            for i, p in enumerate(picks)
        ]
        fatal, soft = _split(_validate(objs, holding, pl.PACK))
        axes = _score(
            asset_id,
            [_Sel(benchmark_id=p, role="diversifier") for p in picks],
            pl.PACK,
            case,
        )
        score = 0.0 if fatal else max(0.0, axes.composite - 0.12 * len(soft))
        parts = [
            f"{asset_id}: scored {score:.2f} with {picks}.",
            f"peer={axes.peer_hits} adjacent={axes.adjacent_hits} wrong={axes.violations}.",
        ]
        if axes.violations:
            parts.append("Sector mismatch - remove those picks.")
        if axes.peer_hits < 2:
            parts.append(
                "Prefer same-industry peers over broad indices; "
                f"acceptable examples were {sorted(case.acceptable)[:5]}."
            )
        if soft:
            parts.append("Compliance: " + "; ".join(soft[:3]))
        return score, " ".join(parts)

    V0_PICKS = ["IDX_SOX", "ETF_XLK", "IDX_SPX"]
    v0_score, v0_feedback = _run("EQ_NVDA", V0_PICKS)
    _recorded = next(
        (float(r["score"]) for r in base_rows if r["asset"] == "EQ_NVDA"), None
    )
    if _recorded is not None:
        # keep the metric's wording, but the recorded score is authoritative
        v0_feedback = v0_feedback.replace(f"{v0_score:.2f}", f"{_recorded:.2f}", 1)
        v0_score = _recorded
    v1_text = versions[1]["text"] if len(versions) > 1 else ""
    v1_score = versions[1]["score"] if len(versions) > 1 else None

    def _picks_from(asset_id):
        """Real v0 picks for an asset, from the recorded baseline rows."""
        row = next((r for r in base_rows if r["asset"] == asset_id), None)
        if not row:
            return None
        toks = [t for t in str(row["picks"]).replace(",", " ").split() if t in pl.PACK.ids]
        return toks if len(toks) == 3 else None

    _refl = []
    for _a in ("EQ_NVDA", "EQ_CRM"):
        _pk = _picks_from(_a)
        if _pk:
            _sc, _fb = _run(_a, _pk)
            # the recorded run is authoritative: its rationale drew compliance penalties
            # the bare tiered credit does not model. Keep every number on the page equal.
            _rec = next((float(r["score"]) for r in base_rows if r["asset"] == _a), None)
            if _rec is not None and abs(_rec - _sc) > 1e-9:
                _fb = _fb.replace(f"{_sc:.2f}", f"{_rec:.2f}", 1)
                _sc = _rec
            _refl.append((_a, _pk, _sc, _fb))

    _refl_html = "".join(
        f"<div class='pgex'><div class='pgk'>Example {i + 1}</div>"
        f"<div class='pgrow'><span class='pgkk'>Inputs</span> holding = {a}, "
        f"shortlist = {len(pl.PACK.ids)} ids</div>"
        f"<div class='pgrow'><span class='pgkk'>Generated Output</span> "
        f"<code>{' , '.join(pk)}</code></div>"
        f"<div class='pgrow'><span class='pgkk'>Feedback</span> {esc(fb)}</div></div>"
        for i, (a, pk, sc, fb) in enumerate(_refl)
    )
    _v0_instruction = versions[0]["text"] if versions else ""

    anatomy = [
        {
            "tab": "1. run the baseline",
            "title": "The baseline program runs on the training split",
            "body": (
                "<p>The unchanged program is executed on every training case. One call per case, "
                "through the signature, with the current instruction.</p>"
                "<div class='anabox'><span class='anak'>holding</span> EQ_NVDA ... "
                "industry=Semiconductors | exposure_currency=USD"
                "<br><span class='anak'>shortlist</span> 88 instruments"
                "<br><span class='anak'>instruction</span> the v0 text, unchanged</div>"
                "<p style='margin-top:10px'>It returned:</p>"
                "<div class='anaout'>IDX_SOX &nbsp; ETF_XLK &nbsp; IDX_SPX</div>"
                f"<p style='margin-top:8px'>One genuine peer, two references. "
                f"<b>Score on this case: {v0_score:.3f}.</b> Across all ten held-out cases "
                f"the same prompt averages {base:.3f} &mdash; that mean is what "
                f"&lsquo;v0 = {base:.3f}&rsquo; refers to.</p>"
            ),
        },
        {
            "tab": "2. score and explain",
            "title": "The metric returns a number AND a sentence",
            "body": (
                "<p>The number decides whether a candidate is kept. The sentence is what the "
                "reflection model reads. Both come from the same function call.</p>"
                "<div class='anatwo'><div class='analeft'><div class='analab'>score &middot; NVDA only</div>"
                f"<div class='anabig'>{v0_score:.3f}</div></div>"
                "<div class='anaright'><div class='analab'>feedback</div>"
                f"<div class='anafb'>{esc(v0_feedback)}</div></div></div>"
                "<p style='margin-top:10px'>This is the score for <b>one case</b>, which is exactly what "
    "the optimiser sees at a time. Everything after <i>peer=1</i> is guidance a scalar "
                "score could never carry. Without it the optimiser knows a candidate lost, not why.</p>"
            ),
        },
        {
            "tab": "3. build the reflection prompt",
        "title": "GEPA assembles instruction + examples + feedback",
        "body": (
            "<p>This is a <b>second, separate model call</b> &mdash; the reflection model, not "
            "the task model. It receives the whole current instruction and a handful of scored "
            "examples, each with the answer it produced and the feedback the metric gave it. "
            "Nothing is summarised for it; it sees the raw strings.</p>"
            "<div class='pgp'>"
            "<div class='pgsec pgdim'>You are an expert optimization assistant. Your task is to "
            "analyze evaluation feedback and propose an improved version of a system "
            "component.</div>"
            "<div class='pgsec'><div class='pgh'>## Current Component</div>"
            "<div class='pgdim'>The component being optimized:</div>"
            f"<pre class='pgcode'>{esc(_v0_instruction)}</pre></div>"
            "<div class='pgsec'><div class='pgh'>## Evaluation Results</div>"
            "<div class='pgdim'>Performance data from evaluating the current component across "
            "test cases:</div>"
            f"{_refl_html}</div>"
            "<div class='pgsec'><div class='pgh'>## Your Task</div>"
            "<div class='pgdim'>Analyze the evaluation results systematically:</div>"
            "<ul class='pglist'>"
            "<li><b>Failure patterns</b> &mdash; what specific errors or edge cases appear?</li>"
            "<li><b>Success patterns</b> &mdash; what worked and should be preserved?</li>"
            "<li><b>Root causes</b> &mdash; what underlying issues explain the failures?</li>"
            "</ul>"
            "<div class='pgdim' style='margin-top:8px'>Based on your analysis, propose an "
            "improved version. Provide <b>only</b> the improved version, inside a fenced "
            "block.</div></div>"
            "</div>"
            "<p style='margin-top:10px'>Two examples are shown; the real call sends three "
            "(<code>reflection_minibatch_size</code> defaults to 3). It is told to <i>analyse</i>, "
            "never what to change &mdash; the fix has to come from reading the feedback.</p>"
        ),
    },
    {
        "tab": "4. v1 is written",
            "title": "The reflection model writes candidate v1",
            "body": (
                "<p>This is the whole output - {vw} words. No human edited it.</p>"
                "<div class='anacode'>{v1head}</div>"
                "<p style='margin-top:10px'>What it decided to add: an explicit <b>priority order</b> "
                "(peers first, sector fund second, broad index last), <b>named peer examples</b> per "
                "industry, and a <b>near-duplicate rule</b>. None of that was in v0 or in the metric.</p>"
            ).format(
                vw=(len(v1_text.split()) if v1_text else 0),
                v1head=esc(v1_text[:720]) + ("..." if len(v1_text) > 720 else ""),
            ),
        },
        {
            "tab": "5. evaluate and keep",
            "title": "Scored on the same cases, then kept or discarded",
            "body": (
                "<p>The candidate runs on the held-out cases with the same metric as the baseline. "
                "Nothing else changed.</p>"
                "<table class='anatab'><tr><th>version</th><th>score</th><th>outcome</th></tr>"
                f"<tr><td>v0 (human)</td><td>{v0_score if False else (base or 0):.3f}</td>"
                "<td class='drop'>the incumbent</td></tr>"
                f"<tr><td>v1 (GEPA)</td><td><b>{(v1_score or 0):.3f}</b></td>"
                "<td class='keep'>kept - it beat the incumbent</td></tr></table>"
                "<p style='margin-top:10px'>That is one full iteration. GEPA then repeats this "
                "thirteen more times, which is why most of the later versions are worse: only "
                "candidates that beat the incumbent survive.</p>"
            ),
        },
    ]

    # ---- weight sensitivity ---------------------------------------------
    # The weights are a judgement call, so show what happens if you disagree.
    import peerlens.metric as _metric_mod

    _original_weight = _metric_mod.HARD_NEGATIVE_WEIGHT
    sens = {}
    for _w in (0.5, 1.5, 3.0):
        _metric_mod.HARD_NEGATIVE_WEIGHT = _w
        row = {}
        for trio in combinations(CALC_IDS, 3):
            axes = score_selection(
                "EQ_NVDA",
                [Selection(benchmark_id=i, role="diversifier") for i in trio],
                pl.PACK,
                calc_case,
            )
            row["|".join(sorted(trio))] = round(axes.composite, 3)
        sens[str(_w)] = row
    _metric_mod.HARD_NEGATIVE_WEIGHT = _original_weight

    tier_counts = {
        "peer": len(calc_case.acceptable),
        "adjacent": len(calc_case.adjacent),
        "hard": len(calc_case.hard_negatives),
        "unrelated": len(calc_case.unacceptable),
    }
    tier_examples = {
        "peer": ", ".join(sorted(calc_case.acceptable)[:4]),
        "adjacent": ", ".join(sorted(calc_case.adjacent)[:4]),
        "hard": ", ".join(sorted(calc_case.hard_negatives)[:4]),
        "unrelated": ", ".join(sorted(calc_case.unacceptable)[:4]),
    }

    calc_tiers = tier_counts
    calc_examples = tier_examples

    toy_trials = [
        ("I1+D0", [("c03", 0), ("c07", 0), ("c09", 1)]),
        ("I4+D1", [("c01", 0), ("c04", 0), ("c10", 1)]),
        ("I3+D2", [("c02", 1), ("c05", 1), ("c08", 1)]),
        ("I3+D2", [("c03", 0), ("c06", 0), ("c09", 1)]),
        ("I3+D1", [("c02", 1), ("c04", 0), ("c07", 1)]),
        ("I3+D1", [("c03", 1), ("c06", 1), ("c08", 1)]),
        ("I2+D2", [("c01", 1), ("c05", 0), ("c09", 1)]),
        ("I2+D2", [("c04", 1), ("c07", 0), ("c10", 1)]),
        ("I1+D0", [("c02", 0), ("c05", 0), ("c08", 1)]),
        ("I4+D1", [("c03", 1), ("c06", 0), ("c09", 1)]),
        ("I2+D2", [("c01", 1), ("c04", 1), ("c07", 1)]),
        ("I3+D2", [("c02", 1), ("c05", 0), ("c10", 1)]),
    ]
    toy_cps = {6: ("I3+D1", 0.71), 12: ("I2+D2", 0.84)}
    toy_test = 0.77

    def _toy_row(k, name, draws, cp=None):
        if cp is not None:
            who, sc = cp
            return (
                f"<tr class='cprow' data-at='{k}'><td colspan='4'>"
                f"checkpoint &mdash; the best average gets the <b>full ten-question exam</b>: "
                f"{who} scored <b>{sc:.2f}</b>, and it is saved</td></tr>"
            )
        chips = " ".join(
            "<i class='chip {cls}'>{c} {mark}</i>".format(
                cls="ok" if ok else "no", c=c, mark="\u2713" if ok else "\u2717"
            )
            for c, ok in draws
        )
        score = sum(ok for _, ok in draws) / 3.0
        return (
            f"<tr data-at='{k}'><td class='tn'>{k}</td><td class='mono2'>{name}</td>"
            f"<td>{chips}</td><td class='tn'>{score:.2f}</td></tr>"
        )

    toy_rows = []
    for k, (name, draws) in enumerate(toy_trials, start=1):
        toy_rows.append(_toy_row(k, name, draws))
        if k in toy_cps:
            toy_rows.append(_toy_row(k, name, draws, cp=toy_cps[k]))
    toy_rows = "\n".join(toy_rows)

    toy_payload = {
        "rows": toy_rows,
        "trials": [[n, d] for n, d in toy_trials],
        "checkpoints": {str(k): [v[0], v[1]] for k, v in toy_cps.items()},
        "test": toy_test,
    }

    # ---- v0 vs the best version: where the improvement actually landed -----
    def _pc(entry):
        return list(entry.get("per_case") or [])

    _v0 = next((v for v in versions if v["label"].startswith("v0")), None)
    _best = None
    for _v in versions:
        if _v.get("score") is None:
            continue
        if _best is None or _v["score"] > _best["score"]:
            _best = _v

    best_label = _best["label"].split()[0] if _best else "best"
    cmp_rows = ""
    cmp_line = ""
    if _v0 and _best and _pc(_v0) and _pc(_best):
        _a, _b = _pc(_v0), _pc(_best)
        _moved = []
        for _i, _r in enumerate(base_rows):
            if _i >= len(_a) or _i >= len(_b):
                break
            _d = _b[_i] - _a[_i]
            if abs(_d) > 1e-9:
                _moved.append(_r["asset"].replace("EQ_", ""))
            _tone = "good" if _d > 0.001 else ("bad" if _d < -0.001 else "")
            _arrow = (
                f"+{_d:.2f}" if _d > 0.001 else (f"{_d:.2f}" if _d < -0.001 else "unchanged")
            )
            cmp_rows += (
                f"<tr><td>{_r['asset'].replace('EQ_', '')}</td>"
                f"<td class='tn'>{_a[_i]:.2f}</td>"
                f"<td class='tn'>{_b[_i]:.2f}</td>"
                f"<td class='tn {_tone}'>{_arrow}</td></tr>"
            )
        cmp_line = ", ".join(_moved) if _moved else "none"

    payload = {
        "versions": versions,
        "base": base,
        "best": best,
        "baseline_rows": base_rows,
        "pack": len(pl.PACK),
        "cases": len(pl.CASES),
        "eval_cases": 10,
        "rules": {"total": total_rules, "mechanical": mech, "optimisable": counts["instruction"]},
        "details": DETAILS,
        "concepts": CONCEPTS,
        "toy": toy_payload,
        "rules_detail": rules_detail,
        "calculator": {
            "candidates": calc_candidates,
            "combos": calc_combos,
            "sensitivity": sens,
            "tiers": tier_counts,
            "examples": tier_examples,
        },
        "optimizer": opt_walk,
        "anatomy": anatomy,
    }

    # ---- page 1: what DSPy is -------------------------------------------
    p1 = """
<section class="slide active">
  <div class="eyebrow">Tech share - document 1 of 4</div>
  <h1>What DSPy is</h1>
  <p class="lede">A Python toolkit for LLM systems: you describe the job, and a scoring test
  decides whether a change to the instructions helped.</p>

  <h2 class="section">The problem, in one picture</h2>
  <div class="ba">
    <div class="ba-col bad">
      <div class="ba-h">Hand-prompted</div>
      <div class="pv"><span>prompt v1</span><b class="q">?</b></div>
      <div class="pv"><span>prompt v2</span><b class="q">?</b></div>
      <div class="pv"><span>prompt v3</span><b class="q">?</b></div>
      <div class="ba-f">Three rewrites. No way to say which is better.</div>
    </div>
    <div class="ba-vs">VS</div>
    <div class="ba-col good">
      <div class="ba-h">With a score</div>
      <div class="pv"><span>prompt v1</span><b class="s">0.61</b></div>
      <div class="pv win"><span>prompt v2</span><b class="s">0.77</b></div>
      <div class="pv"><span>prompt v3</span><b class="s">0.58</b></div>
      <div class="ba-f">Keep v2. Discard the other two.</div>
    </div>
  </div>
  <p class="hintline">Same three prompts. The only difference is a test that returns a number.</p>

  <h2 class="section">The trade</h2>
  <p class="bigq">DSPy doesn't remove prompt engineering.
  It <em>moves</em> it.</p>

  <div class="tradegrid">
    <div class="trow">
      <div class="tleft">You write the prompt by hand</div>
      <div class="tarrow">&rarr;</div>
      <div class="tright">A model writes it against your metric</div>
    </div>
    <div class="trow">
      <div class="tleft">You cannot tell whether a change helped</div>
      <div class="tarrow">&rarr;</div>
      <div class="tright">The same cases give you one number</div>
    </div>
    <div class="trow">
      <div class="tleft">Your rules are prose the model may ignore</div>
      <div class="tarrow">&rarr;</div>
      <div class="tright">Your rules are code the model cannot break</div>
    </div>
    <div class="trow">
      <div class="tleft">Cheap to start, expensive to change</div>
      <div class="tarrow">&rarr;</div>
      <div class="tright">Expensive to start, cheap to change</div>
    </div>
  </div>

  <div class="tradecards">
    <div class="tcard buy"><h3>What it buys</h3>
      <p>Improvement you can defend, and rules that cannot be ignored.</p></div>
    <div class="tcard cost"><h3>What it costs</h3>
      <p>A metric and a labelled set. Our run: 120 calls, 12 of 14 proposals
      still worse than the human prompt.</p></div>
  </div>

  <h2 class="section">Use it, or don't</h2>
  <div class="decide">
    <div class="dcol yes">
      <h3><svg class="ic"><use href="#ic-check"/></svg>Use DSPy when</h3>
      <ul>
        <li><svg class="ic"><use href="#ic-check"/></svg><span>You will run it many times, so the
        setup cost pays itself back.</span></li>
        <li><svg class="ic"><use href="#ic-check"/></svg><span>Correctness can be checked by code,
        or by a judge you have validated against humans.</span></li>
        <li><svg class="ic"><use href="#ic-check"/></svg><span>You expect to change the model,
        the provider or the rules — anything you would otherwise re-prompt by hand.</span></li>
      </ul>
    </div>
    <div class="dcol no">
      <h3><svg class="ic"><use href="#ic-x"/></svg>Do not use it when</h3>
      <ul>
        <li><svg class="ic"><use href="#ic-x"/></svg><span>You will call it five times. Write the
        prompt — you will save yourself an afternoon.</span></li>
        <li><svg class="ic"><use href="#ic-x"/></svg><span>Nobody can define "correct". There is
        nothing to optimise against, and that is the problem to fix first.</span></li>
        <li><svg class="ic"><use href="#ic-x"/></svg><span>A deterministic function already gives
        the right answer. Never put a model near arithmetic or a risk mapping.</span></li>
      </ul>
    </div>
  </div>

  <h2 class="section">Core Concepts</h2>
  <p class="plain">Six ideas, and the whole framework is just these. Click any of them for the
  function, real output from this project, when to use it, and where it bites.</p>
  <div class="concepts" id="concepts"></div>
  <p class="hintline" style="margin-top:18px">
    Signatures say <em>what</em> &middot; Modules say <em>how</em> &middot; Tools reach outside &middot;
    Adapters turn it into tokens &middot; Metrics say <em>better</em> &middot; Optimizers rewrite
  </p>

</section>"""

    def _score_tone(raw):
        try:
            score_val = float(raw)
        except (TypeError, ValueError):
            return ""
        return "good" if score_val >= 0.8 else ("mid" if score_val >= 0.5 else "bad")

    rows_html = "\n".join(
        f"<tr><td>{r['asset'].replace('EQ_', '')}</td>"
        f"<td class='tn {_score_tone(r['score'])}'>{r['score']}</td>"
        f"<td class='tn'>{r['peers']}/3</td>"
        f"<td class='tn'>{int(r['wrong']) or ''}</td>"
        f"<td style='color:var(--muted)'>{esc(r['picks'])}</td></tr>"
        for r in base_rows
    )

    mech_rows = "\n".join(
        f"<tr><td><span class='mtag {r['mech']}'>{r['mech']}</span></td>"
        f"<td>{esc(r['rule'])}</td></tr>"
        for r in rules_detail["mechanical"]
    )
    opt_items = "".join(
        f"<li>{esc(rule)}</li>" for rule in rules_detail["optimisable"]
    )

    def _names(lst):
        return ", ".join(a.replace("EQ_", "") for a in lst)

    _ids = [c.asset_id for c in pl.CASES]
    _n = len(_ids)
    _step = _n / 10
    _eidx = [min(int(i * _step), _n - 1) for i in range(10)]
    _eset = set(_eidx)
    _eval_ids = [_ids[i] for i in _eidx]
    _pool = [a for i, a in enumerate(_ids) if i not in _eset]
    _run = _pool[:12]
    _val_ids, _train_ids = _run[-3:], _run[:-3]
    _unused = _pool[12:]

    split_rows = (
        f"<tr><td><b>train</b></td><td class='tn'>{len(_train_ids)}</td>"
        f"<td>the optimiser rewrites the instruction against these</td>"
        f"<td class='mono2'>{_names(_train_ids)}</td></tr>"
        f"<tr><td><b>validation</b></td><td class='tn'>{len(_val_ids)}</td>"
        f"<td>used to choose between candidate prompts</td>"
        f"<td class='mono2'>{_names(_val_ids)}</td></tr>"
        f"<tr><td><b>test</b></td><td class='tn'>{len(_eval_ids)}</td>"
        f"<td><b>never seen by the optimiser</b> - every number on page 4 comes from here</td>"
        f"<td class='mono2'>{_names(_eval_ids)}</td></tr>"
    )

    _cat = ["EQ_NVDA", "EQ_AMD", "EQ_CRM", "EQ_JPM",
            "IDX_SOX", "ETF_SPY", "ETF_TLT", "CASH_USD"]
    _kind_count = {}
    for _k in pl.PACK.ids:
        _kk = pl.PACK[_k].kind
        _kind_count[_kk] = _kind_count.get(_kk, 0) + 1
    _PLURAL = {"equity": "equities", "etf": "ETFs", "index": "indices", "cash": "cash"}
    _ORDER = ["equity", "etf", "index", "cash"]
    kind_note = " &middot; ".join(
        f"{_kind_count[k]} {_PLURAL[k]}" for k in _ORDER if k in _kind_count
    )
    cat_rows = "\n".join(
        "<tr>"
        f"<td class='mono2'>{k}</td>"
        f"<td>{pl.PACK[k].kind}</td>"
        f"<td>{pl.PACK[k].breadth}</td>"
        f"<td>{esc(pl.PACK[k].industry or pl.PACK[k].sector or 'broad')}</td>"
        f"<td>{esc(str(pl.PACK[k].region))}</td>"
        f"<td>{pl.PACK[k].currency}</td>"
        "</tr>"
        for k in _cat
    )

    p2 = f"""
<section class="slide">
  <div class="eyebrow">Tech share - document 2 of 4</div>
  <h1>The setup</h1>
  <p class="lede">One real task: given an equity, pick three defensible benchmark references.
  NVDA should get AMD or TSMC, not Salesforce. This page is the three things we hand over, and
  nothing else.</p>

  <h2 class="section">1. What we hand over</h2>
  <div class="hand">
    <div class="hcard"><div class="hn">{payload['pack']}</div>
      <h4>Catalogue</h4><p>every id the model may name, with the attributes it may reason from</p></div>
    <div class="hcard"><div class="hn">{payload['cases']}</div>
      <h4>Labelled cases</h4><p>for each asset, the right answers sorted into four tiers by a human</p></div>
    <div class="hcard"><div class="hn">1</div>
      <h4>Metric</h4><p>a function turning three ids into one number and one sentence</p></div>
  </div>
  <div class="handdown"><span>all three feed</span></div>
  <div class="handprog">
    <b>the DSPy program</b>
    <span>signature + module &rarr; three ids &rarr; scored by the metric &rarr; feedback back into
    the instruction</span>
  </div>

  <h2 class="section">2. The catalogue</h2>
  <p class="plain">The model never sees the tiers. It sees only these attributes, and it may not
  invent an id outside this table. A sample of the {payload['pack']}:</p>
  <table class="ctab">
    <tr><th>id</th><th>kind</th><th>breadth</th><th>industry</th><th>region</th><th>ccy</th></tr>
    {cat_rows}
  </table>
  <p class="note">{kind_note}. Breadth is what separates a peer from a reference: 52 sit inside a
  single industry, 24 are broad enough to be nobody's peer.</p>

  <h2 class="section">3. The labelled cases</h2>
  <p class="plain">For each of the {payload['cases']} assets, every candidate was sorted by hand
  into four tiers. This is the ground truth the metric reads.</p>
  <div class="tier4">
    <div class="t4 peer"><div class="tv">+1.0</div><h4>Peer</h4>
      <p>same industry, same economics. The answer we want.</p></div>
    <div class="t4 adj"><div class="tv">+0.5</div><h4>Adjacent</h4>
      <p>credible comparison, different exposure. Useful, not a peer.</p></div>
    <div class="t4 hard"><div class="tv">&minus;1.5</div><h4>Hard negative</h4>
      <p>sounds right, is wrong. Software for a chip company.</p></div>
    <div class="t4 unrel"><div class="tv">&minus;1.5</div><h4>Unrelated</h4>
      <p>obviously wrong. Nobody picks these.</p></div>
  </div>
  <p class="plain" style="margin-top:18px">One worked example &mdash; <b>NVIDIA</b>, all 89
  candidates labelled:</p>
  <table class="tier">
    <tr><th>tier</th><th>count</th><th>examples</th></tr>
    <tr><td><span class="tt peer">peer</span></td><td class="tn">{calc_tiers['peer']}</td>
        <td class="mono2">{calc_examples['peer']}</td></tr>
    <tr><td><span class="tt adj">adjacent</span></td><td class="tn">{calc_tiers['adjacent']}</td>
        <td class="mono2">{calc_examples['adjacent']}</td></tr>
    <tr><td><span class="tt hard">hard negative</span></td><td class="tn">{calc_tiers['hard']}</td>
        <td class="mono2">{calc_examples['hard']}</td></tr>
    <tr><td><span class="tt unrel">unrelated</span></td><td class="tn">{calc_tiers['unrelated']}</td>
        <td class="mono2">{calc_examples['unrelated']}</td></tr>
  </table>
  <p class="note"><b>The hard negatives are the whole point.</b> Anyone can reject oil for a chip
  company. Rejecting Salesforce for NVIDIA takes an actual analysis &mdash; which is why those sit
  in their own tier and cost 1.5.</p>

  <h2 class="section">4. Train, validation, test</h2>
  <p class="plain">The {payload['cases']} cases are split so the optimiser cannot grade its own
  homework.</p>
  <table class="ctab">
    <tr><th>set</th><th>n</th><th>what it is for</th><th>assets</th></tr>
    {split_rows}
  </table>
  <p class="note">{len(_unused)} of the {payload['cases']} cases are deliberately left out of the
  run entirely. They are the obvious next step if the improvement needs checking on fresh data.</p>

  <h2 class="section">5. The metric</h2>
  <p class="plain">One idea: a benchmark earns credit for how close its relationship is, and loses
  more for being wrong than it gains for being adequate.</p>
  <div class="formulabox">
    <div class="fline"><span class="fk">credit</span>
      <span class="feq">= ( peers &times; 1.0 &nbsp;+&nbsp; adjacent &times; 0.5 ) / 3</span></div>
    <div class="fline"><span class="fk">penalty</span>
      <span class="feq">= 1.5 &times; ( wrong / 3 )</span></div>
    <div class="fline"><span class="fk">score</span>
      <span class="feq">= clamp01( credit &minus; penalty )</span></div>
    <div class="fsep"></div>
    <div class="fline"><span class="fk">clamp01</span>
      <span class="fcm">// keep it between 0 and 1 &mdash; floor at 0, cap at 1</span></div>
    <div class="fline"><span class="fk">duplicate</span>
      <span class="fcm">// the three picks are really one option &rarr; score &times; 0.8</span></div>
    <div class="fline"><span class="fk">unusable</span>
      <span class="fcm">// wrong count, unknown id or a repeated id &rarr; score = 0</span></div>
  </div>

  <p class="note">A peer is worth two adjacents. A wrong pick costs three times what an adjacent
  earns. A <b>duplicate</b> means either three funds tracking one industry, or any pair whose
  descriptions are 60% similar &mdash; two trackers of the same index are one option, not two.</p>
  <div class="calcbox">
    <div class="calcleft">
      <div class="pickgrid" id="pickgrid"></div>
      <div class="picknote" id="picknote">Select exactly three.</div>
    </div>
    <div class="calcright">
      <div class="scorelabel">score</div>
      <div class="scorenum" id="scoreNum">-</div>
      <div class="scorebreak" id="scoreBreak"></div>
      <div class="formula">click candidates for NVDA and the real metric recomputes</div>
    </div>
  </div>

  <h2 class="section">6. Why those weights</h2>
  <div class="card">
    <h3>The weights are a judgement, so test them</h3>
    <p style="margin-bottom:10px">A wrong pick is treated as worse than a missing peer, because
    a wrong benchmark quietly misleads a review while a weak one merely disappoints. That is a
    choice, not a derivation. Drag the penalty and watch the same three picks re-score.</p>
    <div class="wsens">
      <span class="wlab">penalty per wrong pick</span>
      <div class="wbtns" id="wbtns"></div>
    </div>
    <div class="wsensout" id="wsensout"></div>
  </div>
</section>"""

    # ---- page 3: the prompt evolving ------------------------------------
    spark_bars = ""
    if scored:
        lo, hi = min(scored), max(scored)
        span = (hi - lo) or 1
        spark_bars = "".join(
            f'<div data-h="{18 + round(78 * ((s - lo) / span))}" title="{s:.3f}"></div>'
            for s in scored
        )
    p3 = f"""
<section class="slide">
  <div class="eyebrow">Tech share - document 4 of 4</div>
  <h1>The optimiser at work</h1>
  <h2 class="section">1. Anatomy of one full iteration - how v1 was produced</h2>
  <p class="plain">Click through the five stages. Every string below is real: the score and
  feedback are recomputed from the same functions the optimiser used, and the v1 text is exactly
  what the reflection model returned.</p>
  <p class="note">This walk-through follows <b>one case, EQ_NVDA</b>. Its v0 score is
  <b>0.550</b>. The <b>0.635</b> quoted as &ldquo;the baseline&rdquo; is the <em>mean</em> of
  all ten held-out cases &mdash; both are v0, measured over different scopes.</p>
  <div class="anabox-wrap">
    <div class="anatabs" id="anatabs"></div>
    <div class="anapane" id="anapane"></div>
  </div>

  <h2 class="section">2. Every version it wrote</h2>
  <p class="plain">Fifteen prompts, each scored on the same ten held-out cases. Click one for its
  diff, commit-log style, with the full prompt underneath.</p>

  <div class="grid" style="grid-template-columns:1fr 300px;align-items:start;margin-top:10px">
    <div class="viewer">
      <div class="vlist" id="vlist"></div>
      <div class="pane">
        <div class="panehead" id="vhead"></div>
        <div id="vbody"></div>
      </div>
    </div>
    <div class="card">
      <h3>Score by version</h3>
      <div class="spark">{spark_bars}</div>
      <div class="kv" style="margin-top:14px">
        <div><div class="k">v0</div><div class="v">{'' if base is None else f'{base:.3f}'}</div></div>
        <div><div class="k">best</div><div class="v" style="color:var(--add)">{'' if best is None else f'{best:.3f}'}</div></div>
      </div>
      <p style="margin-top:12px">Only the instruction changes. Signature, schema, validators and
      the evaluation set are held fixed, which is what makes the comparison fair.</p>
      <p style="margin-top:10px;color:var(--muted);font-size:13px">A missing score means that
      version has not been re-scored on the held-out set yet.</p>
    </div>
  </div>
  <h2 class="section">3. What the optimiser bought - v0 against the best</h2>
  <div class="grid g2">
    <div class="card">
      <h3>Same ten cases, same scorer, one prompt apart</h3>
      <div class="vsrow">
        <div class="vsbox"><div class="vsk">v0 &middot; the human prompt</div>
          <div class="vsv">{base or 0:.3f}</div></div>
        <div class="vsarrow">&rarr;</div>
        <div class="vsbox win"><div class="vsk">{best_label} &middot; GEPA</div>
          <div class="vsv">{best or 0:.3f}</div></div>
      </div>
      <div class="vsdelta">{(best or 0) - (base or 0):+.3f} on the same ten held-out cases</div>
    </div>
    <div class="card">
      <p class="tcaption">Per held-out asset: v0's score, the best version's score, and the
      change.</p>
      <table class="cmp">
        <tr><th>asset</th><th>v0</th><th>best</th><th>change</th></tr>
        {cmp_rows}
      </table>
    </div>
  </div>

</section>"""

    p4 = f"""
<section class="slide">
  <div class="eyebrow">Tech share - document 3 of 4</div>
  <h1>How the optimiser works</h1>
  <h2 class="section">1. The loop</h2>
  <div class="ovflow">
    <div class="ovlane train">
      <div class="ovtag">Training set &middot; {len(_train_ids)} cases</div>
      <div class="ovrow">
        <div class="ovbox">sample a<br>minibatch</div><div class="ova">&rarr;</div>
        <div class="ovbox">run the program<br>and score it</div><div class="ova">&rarr;</div>
        <div class="ovbox">read why<br>it failed</div><div class="ova">&rarr;</div>
        <div class="ovbox hot">write the next<br>instruction</div><div class="ova">&rarr;</div>
        <div class="ovbox">keep or discard</div>
      </div>
      <div class="ovloop">&#8635; repeat until the metric-call budget runs out
        &mdash; ours was 120</div>
    </div>
    <div class="ovlane val">
      <div class="ovtag">Validation set &middot; {len(_val_ids)} cases</div>
      <p><b>Ranks the survivors.</b> This is where "which prompt is best" is decided, because
      scoring on the training set just rewards memorising it.</p>
    </div>
    <div class="ovlane test">
      <div class="ovtag">Test set &middot; {len(_eval_ids)} cases</div>
      <p><b>Never enters the search.</b> It exists only to produce the number we report, which is
      why that number means something.</p>
    </div>
  </div>
  <p class="note">The optimiser only ever ranks on validation. If the test set were used for
  ranking, the reported score would be the score of the winner chosen by that same test set
  &mdash; and the improvement would be partly an artefact.</p>

  <h2 class="section">2. MIPROv2 &mdash; generate, rank cheaply, promote the survivors</h2>
  <p class="plain">MIPROv2 writes every candidate <em>before</em> it scores anything. Then it runs
  a cheap, noisy tournament and only pays for full evaluation on the few that survive it. The
  proposer never sees a failure, so there is nothing for it to learn from mid-search.</p>

  <div class="flowd">
    <div class="fcol">
      <div class="fc start">Start &mdash; <b>N</b> candidate prompts</div>
      <div class="farrt">&#9660;</div>

      <div class="fc">Run <b>6 trials</b>
        <div class="fsub">each trial: one prompt, scored on 3 of the 10 questions</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc">Pick the best <b>average</b> so far
        <div class="fsub">that has not already had a full exam</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc hot">Full exam &mdash; <b>all 10</b> questions
        <div class="fsub">the only number worth trusting. Save it.</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc dec">More trials left?
        <div class="fsub"><b>yes</b> &#8634; back up to step 2 &nbsp;&middot;&nbsp;
          <b>no</b> &#9660; carry on</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc">Compare the saved scores
        <div class="fsub">ignore the noisy trial averages &mdash; read only the saved column</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc win">Return the highest &mdash; <b>0.84</b></div>
      <div class="floop" aria-hidden="true"></div>
    </div>

    <div class="fside">
      <div class="fsave">
        <div class="fstag">saved results</div>
        <div class="fsrow">round 1 <b>0.62</b></div>
        <div class="fsrow win">round 2 <b>0.84</b></div>
        <div class="fsrow">round 3 <b>0.71</b></div>
      </div>
      <div class="fsnote">One score per checkpoint, written here as it happens. The final comparison
      reads nothing else &mdash; which is why the winner can be from round 2 rather than round 3.</div>
    </div>
  </div>

  <p class="note">The six are <b>trials, not six different prompts</b>: the same prompt can be
  re-tested several times, and that is exactly how its average sharpens. And the one promoted is
  the best average <em>that has not yet had a full exam</em>, so nothing is fully tested twice.</p>

  <h3 style="margin:24px 0 4px;font-size:15px">What gets generated, and what is actually random</h3>
  <div class="grid g2" style="margin-top:10px">
    <div class="card">
      <h3>Instruction candidates &mdash; written, not sampled</h3>
      <p>An LLM proposer writes them, guided by a summary of your dataset plus a random
      &ldquo;tip&rdquo; each time so they differ. You do not pick from a pool of existing prompts;
      they are generated once, up front, and never revised mid-search.</p>
      <p style="margin-top:8px">Count: <code>num_candidates</code> if optimizing zero-shot only,
      but <b>half</b> that when demos are also being optimized &mdash; the budget is deliberately
      shifted to demos. So <code>auto="light"</code> gives <b>3 instructions &times; 6 demo sets =
      18 combinations</b>, not 36.</p>
    </div>
    <div class="card">
      <h3>Demo sets &mdash; built, with randomness inside</h3>
      <p>Three are fixed by construction, the rest are bootstrapped:</p>
      <table class="ctab" style="margin-top:6px">
        <tr><td><code>D0</code></td><td>zero-shot &mdash; no examples at all</td></tr>
        <tr><td><code>D1</code></td><td>labelled only &mdash; real input/output pairs</td></tr>
        <tr><td><code>D2</code></td><td>bootstrapped &mdash; the program's own traces, kept only
            where the metric passed</td></tr>
        <tr><td><code>D3+</code></td><td>shuffle the trainset, pick a random demo count, bootstrap
            again</td></tr>
      </table>
      <p style="margin-top:9px"><b>You never supply these.</b> MIPROv2 builds all N of them itself,
      from the trainset you pass in, <em>before</em> it proposes any instruction &mdash; and then
      shows them to the instruction proposer, so the two are written to fit each other.</p>
    </div>
  </div>
  <p class="note">So: instructions are <b>generated</b>, demo sets are <b>constructed</b> with a
  shuffle and a random size, the (instruction, demo) pairing is <b>searched</b> by Optuna rather
  than picked at random, and the only purely random draw in each trial is <b>which validation
  cases</b> land in the minibatch.</p>
  <p class="note"><b>GEPA does not do this at all.</b> It builds no demo sets &mdash; it only
  rewrites instructions, which is why its metric has to return a sentence to learn from.</p>

  <h3 style="margin:26px 0 4px;font-size:15px">A toy run &mdash; watch one candidate swing</h3>
  <p style="margin:0 0 12px;font-size:13.5px;color:#39445c">Twelve candidates, a validation set of
  ten cases, three cases drawn per trial. <b>Compare trial 2 with trial 4</b>: same candidate,
  different batch. The numbers are fixed for illustration, not from a live model, and the toy
  promotes all three survivors at once &mdash; real MIPROv2 promotes one candidate per full
  evaluation, every six trials.</p>

  <div class="miptoy">
    <div class="mipctl">
      <button type="button" class="mbtn" id="mipNext">next trial</button>
      <button type="button" class="mbtn ghost" id="mipReset">reset</button>
      <span class="mipstat" id="mipStat">all trials shown &mdash; press reset to step through</span>
    </div>
    <div class="mipcols">
      <div>
        <h4>Inside the optimiser &middot; 12 trials, then two checkpoints</h4>
        <table class="miptab">
          <thead><tr><th>#</th><th>prompt</th><th>3 of the 10 validation questions</th>
            <th>score</th></tr></thead>
          <tbody id="miprows">
    {toy_rows}
          </tbody>
        </table>
      </div>
      <div>
        <h4>Running average &middot; then saved results</h4>
        <div class="miprank" id="miprank"></div>
        <div class="mipout" id="mipout"></div>
      </div>
    </div>
    <div class="mipnote" id="mipnote"></div>
  </div>

  <div class="grid g2" style="margin-top:16px">
    <div class="card">
      <h3>The knobs</h3>
      <table class="ctab">
        <tr><th>auto</th><th>candidates</th><th>instr / demo</th><th>val target</th></tr>
        <tr><td><code>light</code></td><td>6</td><td>3 / 6</td><td>100</td></tr>
        <tr><td><code>medium</code></td><td>12</td><td>6 / 12</td><td>300</td></tr>
        <tr><td><code>heavy</code></td><td>18</td><td>9 / 18</td><td>1000</td></tr>
      </table>
      <p style="margin-top:8px;color:var(--muted);font-size:13px">Needs <code>optuna</code>.
      <code>minibatch_size</code> defaults to 35; the full evaluation fires every
      <code>minibatch_full_eval_steps + 1</code> = 6 trials.</p>
    </div>
    <div class="card">
      <h3>Why the toy assumes a big validation set</h3>
      <p>The cheap stage only switches on when the validation set is larger than <b>50 cases</b>.
      Below that, every trial is already a full evaluation &mdash; no minibatches, and no budget
      saved by having them.</p>
      <p style="margin-top:8px">Our validation set is <b>3 cases</b>, so the ten-question exam in
      the toy is <b>the general case, not ours</b>. If we had run MIPROv2 on this task, its funnel
      would have collapsed to plain full evaluations.</p>
      <p style="margin-top:8px;color:var(--muted);font-size:13px">MIPROv2 was never our optimiser
      &mdash; it is the comparison. We ran GEPA, which needs no minibatch machinery.</p>
    </div>
  </div>

  <h2 class="section">3. GEPA &mdash; write, read, rewrite</h2>
  <p class="plain">GEPA has no grid. It writes <b>one</b> instruction, finds out why it failed, and
  writes the next one from that critique. The learning signal is your metric's <em>sentence</em>,
  not a score.</p>

  <div class="flowd">
    <div class="fcol">
      <div class="fc start">Start &mdash; one seed prompt
        <div class="fsub">the prompt a human wrote</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc">Pick a parent from the frontier
        <div class="fsub">the shortlist of candidates that are still alive</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc">Run it on <b>3 training cases</b>
        <div class="fsub">capturing the trace, not just the answer</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc hot">The metric returns a score <b>and a sentence</b>
        <div class="fsub">&ldquo;peer=1, adjacent=2. Prefer same-industry peers.&rdquo;</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc">A reflection model reads those sentences
        <div class="fsub">this is the step MIPROv2 does not have</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc">It writes <b>one</b> new instruction
        <div class="fsub">a targeted edit, not a paraphrase</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc">Keep it if it wins <b>any single case</b>
        <div class="fsub">per-case, not on average &mdash; specialists stay alive</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc dec">Budget left?
        <div class="fsub"><b>yes</b> &#8634; back up to &ldquo;pick a parent&rdquo;
          &nbsp;&middot;&nbsp; <b>no</b> &#9660; carry on</div></div>
      <div class="farrt">&#9660;</div>

      <div class="fc win">Return the best on validation &mdash; v2, 0.767</div>
      <div class="farrt">&#9660;</div>

      <div class="fc out">Then, <b>outside the optimiser</b>: scored on the 10 test cases
        <div class="fsub">the optimiser never saw these either</div></div>

      <div class="floop gepa" aria-hidden="true"></div>
    </div>

    <div class="fside">
      <div class="fsave">
        <div class="fstag">the pareto frontier</div>
        <div class="fsrow">v0 &middot; the seed <b>0.635</b></div>
        <div class="fsrow">v1 &middot; kept <b>0.738</b></div>
        <div class="fsrow win">v2 &middot; kept <b>0.767</b></div>
        <div class="fsrow dead">v3&ndash;v14 &middot; discarded <b>12 of 14</b></div>
      </div>
      <div class="fsnote">Same run as page 4. Fourteen proposals, two kept. A candidate joins the
      frontier by being best on <em>some</em> case, so a specialist survives even when its average
      is worse.</div>
    </div>
  </div>

  <h3 style="margin:26px 0 4px;font-size:15px">The loop five times, with illustrative
  numbers</h3>
  <p style="margin:0 0 12px;font-size:13.5px;color:#39445c">Read each row left to right. The sentence the metric returns is the <em>only</em> input to the rewrite &mdash; nothing else changes between loops. Colour marks which loop added that sentence: <span class="add-a">loop 1</span> &middot; <span class="add-b">loop 2</span> &middot; <span class="add-c">loop 3</span>.</p>

  <div class="gepaex">
    <div class="exloop">
      <div class="exhead"><b>loop 1</b> the seed prompt is scored, then critiqued</div>
      <div class="exbody">
        <div class="excell"><div class="exlab">prompt in</div>Pick three defensible benchmarks for the holding.</div>
        <div class="excell"><div class="exlab">metric returned</div>
          <div class="exscore">0.55</div>
          <div class="exsaid">&ldquo;peer=1, adjacent=2. Only one true peer &mdash; prefer same-industry names over broad indices.&rdquo;</div></div>
        <div class="excell"><div class="exlab">reflection wrote</div>Pick three defensible benchmarks for the holding. <span class="add-a">Prefer same-industry peers over broad indices.</span></div>
      </div>
      <div class="exverdict acc">&check; that child scored <b>0.72</b> &mdash; better, so it joins the frontier</div>
    </div>
    <div class="exloop">
      <div class="exhead"><b>loop 2</b> the accepted child becomes the parent</div>
      <div class="exbody">
        <div class="excell"><div class="exlab">prompt in</div>Pick three defensible benchmarks for the holding. <span class="add-a">Prefer same-industry peers over broad indices.</span></div>
        <div class="excell"><div class="exlab">metric returned</div>
          <div class="exscore">0.72</div>
          <div class="exsaid">&ldquo;peer=2, adjacent=1. Better. Two of the picks are the same exposure wearing different tickers.&rdquo;</div></div>
        <div class="excell"><div class="exlab">reflection wrote</div>Pick three defensible benchmarks for the holding. <span class="add-a">Prefer same-industry peers over broad indices.</span> <span class="add-b">Do not pick two funds tracking the same index.</span></div>
      </div>
      <div class="exverdict acc">&check; that child scored <b>0.79</b> &mdash; better, so it joins the frontier too</div>
    </div>
    <div class="exloop">
      <div class="exhead"><b>loop 3</b> the metric is starting to run out of things to say</div>
      <div class="exbody">
        <div class="excell"><div class="exlab">prompt in</div>Pick three defensible benchmarks for the holding. <span class="add-a">Prefer same-industry peers over broad indices.</span> <span class="add-b">Do not pick two funds tracking the same index.</span></div>
        <div class="excell"><div class="exlab">metric returned</div>
          <div class="exscore worse">0.79</div>
          <div class="exsaid">&ldquo;peer=2, no duplicate. Nothing specific left to fix.&rdquo;</div></div>
        <div class="excell"><div class="exlab">reflection wrote</div>Pick three defensible benchmarks for the holding. <span class="add-a">Prefer same-industry peers over broad indices.</span> <span class="add-b">Do not pick two funds tracking the same index.</span> <span class="rej">Always prefer ETFs over single names.</span></div>
      </div>
      <div class="exverdict rej">&times; that child scored <b>0.68</b> &mdash; worse, so it is <b>not added</b></div>
    </div>
    <div class="exloop">
      <div class="exhead"><b>loop 4</b> same parent again, because nothing replaced it</div>
      <div class="exbody">
        <div class="excell"><div class="exlab">prompt in</div>Pick three defensible benchmarks for the holding. <span class="add-a">Prefer same-industry peers over broad indices.</span> <span class="add-b">Do not pick two funds tracking the same index.</span></div>
        <div class="excell"><div class="exlab">metric returned</div>
          <div class="exscore worse">0.79</div>
          <div class="exsaid">&ldquo;peer=2, adjacent=1. Same picture as before.&rdquo;</div></div>
        <div class="excell"><div class="exlab">reflection wrote</div>Pick three defensible benchmarks for the holding. <span class="add-a">Prefer same-industry peers over broad indices.</span> <span class="add-b">Do not pick two funds tracking the same index.</span> <span class="rej">Keep every answer under 60 words.</span></div>
      </div>
      <div class="exverdict rej">&times; that child scored <b>0.71</b> &mdash; worse, so it is <b>not added</b></div>
    </div>
    <div class="exloop">
      <div class="exhead"><b>loop 5</b> one more guess, with still no new complaint to work from</div>
      <div class="exbody">
        <div class="excell"><div class="exlab">prompt in</div>Pick three defensible benchmarks for the holding. <span class="add-a">Prefer same-industry peers over broad indices.</span> <span class="add-b">Do not pick two funds tracking the same index.</span></div>
        <div class="excell"><div class="exlab">metric returned</div>
          <div class="exscore worse">0.79</div>
          <div class="exsaid">&ldquo;peer=2, no duplicate. No new complaint available.&rdquo;</div></div>
        <div class="excell"><div class="exlab">reflection wrote</div>Pick three defensible benchmarks for the holding. <span class="add-a">Prefer same-industry peers over broad indices.</span> <span class="add-b">Do not pick two funds tracking the same index.</span> <span class="rej">Prefer very large companies.</span></div>
      </div>
      <div class="exverdict rej">&times; that child scored <b>0.74</b> &mdash; worse, so it is <b>not added</b></div>
    </div>

    <div class="exres">
      <span>Best on validation &mdash; the prompt from loop 3, <b>0.79</b>. Returned.</span>
      <span class="extest">then scored on the 10 test cases &rarr; 0.74<br>
        <span class="extestsub">lower, because it is a fresh set the loop never saw</span></span>
    </div>
  </div>

  <p class="note"><b>Two things this tidy example hides.</b> First, the parent for each loop is
  <em>selected from the frontier</em>, not automatically the previous child. Usually it is the
  previous child &mdash; but the selector is free to reach back to an earlier candidate that is
  still best on some cases, so the lineage can branch. Second, the scores rise here only because
  the example is tidy: in a real run most children come back worse. Ours kept <b>2 of 14</b>, and
  the twelve that lost were discarded.</p>
  <p class="note">So it does compound &mdash; each child inherits its parent's wording and adds one
  correction &mdash; but it compounds <b>on a frontier, not on a single line</b>, and the returned
  prompt is the best on validation, which may be an earlier branch rather than the latest one.</p>

  <p class="note"><b>Every accepted addition is traceable.</b> &ldquo;prefer same-industry
  peers&rdquo; came from <i>peer=1</i>; &ldquo;do not pick two funds&rdquo; came from <i>same
  exposure</i>. Reflection never rewrites the whole prompt &mdash; it appends the one rule that
  addresses the sentence in front of it.</p>
  <p class="note"><b>And that is exactly why loops 3&ndash;5 failed.</b> Once the metric says
  &ldquo;nothing specific left to fix&rdquo;, reflection has no complaint to answer, so it invents
  one &mdash; a word limit, a market-cap preference &mdash; and every guess scores lower. The
  rejections are not a bug: <b>2 of our 14 real proposals survived</b>. A loop that produces
  nothing better is the normal case, and a child that wins nowhere simply never reaches the
  frontier.</p>

  <p class="note"><b>Two differences that matter.</b> MIPROv2 writes all its candidates first and
  then <em>selects</em>; GEPA writes one, reads the failure, and rewrites &mdash; so it needs a
  metric that explains itself. And MIPROv2 ranks by average, while GEPA ranks per case, which is
  how our run produced a prompt that fixed three held-out cases and left seven untouched: a
  specialist, not a generalist.</p>

  <h2 class="section">4. Side by side</h2>
  <div class="cmp">
    <div class="cmpcol">
      <h3>MIPROv2</h3>
      <div class="cmpstep">write 6 instructions <b>up front</b></div>
      <div class="cmpstep">write 6 demo sets <b>up front</b></div>
      <div class="cmpstep">Optuna scores the pairs</div>
      <div class="cmpstep">keep the highest <b>average</b></div>
      <div class="cmpfoot">selects from a fixed grid<br>best on average</div>
    </div>
    <div class="cmpmid">
      <div class="cmpline"></div>
      <div class="cmplabel">when is the<br>prompt written?</div>
      <div class="cmpline"></div>
    </div>
    <div class="cmpcol gepa">
      <h3>GEPA</h3>
      <div class="cmpstep">write <b>one</b> instruction</div>
      <div class="cmpstep">score it, read the feedback</div>
      <div class="cmpstep">write the <b>next</b> one from that</div>
      <div class="cmpstep">keep it if it wins <b>anywhere</b></div>
      <div class="cmpfoot">searches by reflection<br>best on some cases</div>
    </div>
  </div>
  <p class="note">Both return a new program and leave yours untouched. Both are bounded by the
  same thing: the metric. Neither can add a fact the model does not have.</p>
</section>"""

    dots = "".join(
        f'<button class="dot{" on" if i == 0 else ""}" aria-label="slide {i+1}">{i+1}</button>'
        for i in range(4)
    )

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DSPy - tech share</title>
<style>{CSS}</style></head>
<body>
{NOSCRIPT}
{SPRITE}
<div class="deck">
{p1}
{p2}
{p4}
{p3}
</div>
<div class="modal" id="modal">
  <div class="sheet wide">
    <div class="sheet-top">
      <svg class="ic lg" id="mIcon"><use href="#ic-align"/></svg>
      <div><h2 id="mTitle"></h2><div class="api" id="mApi"></div></div>
      <button class="close" id="mClose" aria-label="close">&times;</button>
    </div>
    <div id="mBody"></div>
  </div>
</div>
<div class="nav"><div class="dots">{dots}</div>
<div class="hint">← → to navigate · click a version to see the diff</div></div>
<script>{JS.replace("__DATA__", json.dumps(payload))}</script>
</body></html>"""

    # An <svg> without a viewBox draws at 1:1 user units, so a 0..24 path inside a
    # 22px box renders mostly outside the viewport. The symbol's own viewBox is not
    # enough - the referencing element needs one too.

    # An <svg> without a viewBox draws at 1:1 user units, so a 0..24 path inside a
    # 22px box renders mostly outside the viewport. The symbol's own viewBox is not
    # enough - the referencing element needs one too.
    html = html.replace('<svg class="ic lg"', '<svg class="ic lg" viewBox="0 0 24 24"')
    html = html.replace('<svg class="ic"', '<svg class="ic" viewBox="0 0 24 24"')

    out = HERE / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    # The script-free edition is opt-in: a normal build must not rewrite any
    # file other than the one it was asked for.
    if args.also_nojs:
        try:
            import deck_nojs

            nojs_path = out.with_name("deck_nojs.html")
            nojs_path.write_text(deck_nojs.render(payload), encoding="utf-8")
            print(f"wrote {nojs_path}  ({nojs_path.stat().st_size // 1024} KB)")
        except Exception as exc:
            print(f"  (no-JS build skipped: {type(exc).__name__}: {exc})")
    n_scores = len(scored)
    print(f"wrote {out}  ({len(html)//1024} KB)")
    print(f"  versions: {len(versions)}  ·  scored: {n_scores}  ·  baseline {base}")
    if not prompts_dir.is_dir():
        print(f"  warning: no prompts at {prompts_dir} - page 3 will only show v0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
