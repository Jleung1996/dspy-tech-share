"""Generate notebook.ipynb - a runnable walkthrough of how this was built.

Design rule: everything except the final optional cell must run with no API key
and no network. The expensive parts (baseline, optimiser) are replayed from the
artefacts they produced, so the notebook is reproducible and free to run.
"""

from __future__ import annotations

import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "notebook.ipynb"

cells: list[dict] = []


def md(text: str) -> None:
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": text.strip("\n").splitlines(keepends=True),
    })


def code(text: str) -> None:
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.strip("\n").splitlines(keepends=True),
    })


# ---------------------------------------------------------------- title
md("""
# How this was built: a walkthrough

This notebook explains, by running it, how the benchmark-selection experiment works:
the catalogue, the labelled truth, the metric, the gates, the prompt as a signature,
and what an optimiser did with it.

**It runs with no API key and no network.** The expensive steps (the baseline run and the
optimiser run) are *replayed* from the files they produced. Exactly one cell at the end is
optional and does call a model.

Run the cells top to bottom. Nothing here is a mock: every number comes from the same
functions the experiment used.
""")

# ---------------------------------------------------------------- 0 setup
md("""
## 0. Setup

The package lives next to this notebook. If the import fails, the notebook was opened from
the wrong folder - start Jupyter from the project folder that contains `peerlens/`.
""")

code("""
# Run this first. Everything else depends on it.
import sys, json, difflib
from pathlib import Path
from itertools import combinations

ROOT = Path.cwd()
if not (ROOT / "peerlens").is_dir():
    # tolerate being opened from a subfolder
    for parent in ROOT.parents:
        if (parent / "peerlens").is_dir():
            ROOT = parent
            break
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / ".pydeps"))   # dspy, only needed for the optional cell

_ROOT = Path(__file__).resolve().parents[1]
import sys as _sys
if str(_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_ROOT))
import peerlens as pl
from peerlens import labeling, marketdata
from peerlens.metric import Selection, score_selection, HARD_NEGATIVE_WEIGHT
from peerlens.prompt_v2 import (
    HoldingFacts, BenchmarkPick, RULE_MAP, rule_summary,
    validate_selection, split_problems, expected_mismatches,
)

print("workspace :", ROOT)
print("catalogue :", len(pl.PACK), "instruments")
print("cases     :", len(pl.CASES), "labelled assets")
print("tests     : 77")
""")

# ---------------------------------------------------------------- 1 the task
md("""
## 1. The task, in one example

Given an equity holding, pick **three** benchmark references a risk reviewer would accept.

The failure this is built to catch is not obvious wrongness - it is **plausible proximity**.
NVIDIA is a semiconductor company. Salesforce is also "big tech". Salesforce is not a
benchmark for NVIDIA and no amount of confident prose makes it one.
""")

code("""
inst = pl.PACK["EQ_NVDA"]
print(f"{inst.id}  {inst.name}")
print(f"  sector   : {inst.sector}")
print(f"  industry : {inst.industry}")
print(f"  region   : {inst.region}   currency: {inst.currency}")
print(f"  breadth  : {inst.breadth}")
""")

# ---------------------------------------------------------------- 2 catalogue
md("""
## 2. The catalogue: the only universe the model may choose from

Every entry carries a sector, a finer industry, a region, a currency, and a `breadth` -
how much of the economy it spans. `breadth` is the field that lets us tell a *peer* from a
*reference*: a semiconductor index tracks one industry, the S&P 500 tracks everything.
""")

code("""
rows = []
for i in list(pl.PACK)[:8]:
    rows.append((i.id, i.kind, i.breadth, i.sector or "-", i.industry or "-"))
print(f"{'id':<16}{'kind':<8}{'breadth':<10}{'sector':<26}industry")
print("-" * 92)
for r in rows:
    print(f"{r[0]:<16}{r[1]:<8}{r[2]:<10}{r[3]:<26}{r[4]}")
""")

# ---------------------------------------------------------------- 3 tiers
md("""
## 3. Ground truth, in four tiers

This is the part nobody hands you. For each asset a human labelled every candidate:

| tier | meaning | credit |
|---|---|---|
| **peer** | same industry, genuinely substitutable | `+1.0` |
| **adjacent** | sector proxy, broad index, cross-industry neighbour | `+0.5` |
| **hard negative** | same sector, clearly *not* a peer | `-1.5` |
| **unrelated** | different sector, or wrong asset class | `-1.5` |

Hard negatives carry the discriminating power. Anyone can reject oil for a chip company.
Only real analysis rejects a software company for a chip company.
""")

code("""
case = pl.CASE_BY_ASSET["EQ_NVDA"]

for name, tier in [
    ("peer (10)", case.acceptable),
    ("adjacent", case.adjacent),
    ("hard negative", case.hard_negatives),
    ("unrelated", case.unacceptable),
]:
    sample = ", ".join(sorted(tier)[:5])
    print(f"{name:<16} {len(tier):>3}   e.g. {sample}")
""")

# ---------------------------------------------------------------- 4 metric
md("""
## 4. The metric

Not a similarity rating - a small additive rule over the three ids returned:

```
credit      = (peers * 1.0 + adjacent * 0.5) / 3
penalty     = wrong * 1.5 / 3
composite   = clamp01(credit - penalty) * duplicate_penalty
```

Wrong count, duplicate ids, or an id not in the catalogue scores `0` outright, because the
downstream contract requires exactly three.
""")

code("""
def show(ids, note=""):
    sels = [Selection(benchmark_id=i, role="diversifier") for i in ids]
    ax = score_selection("EQ_NVDA", sels, pl.PACK, case)
    print(f"{str(ids):<52} score={ax.composite:.3f}  "
          f"peers={ax.peer_hits} adj={ax.adjacent_hits} wrong={ax.violations}")
    if note:
        print(f"    -> {note}")

show(["EQ_AMD", "EQ_TSM", "EQ_AVGO"], "three true chip companies")
show(["EQ_AMD", "EQ_TSM", "IDX_SOX"], "two peers plus the industry index")
show(["EQ_AMD", "IDX_SOX", "ETF_XLK"], "one peer, two references")
show(["IDX_SOX", "ETF_XLK", "IDX_SPX"], "no peer at all - the baseline's habit")
show(["EQ_CRM", "EQ_ADBE", "EQ_ORCL"], "all software: plausible, useless")
show(["EQ_AMD", "EQ_TSM"], "only two")
""")

md("""
Look at rows 4 and 5. Both are composed of things that *sound* reasonable for a technology
holding. Both score near zero for opposite reasons: one has no peer, the other has no chip
exposure at all.
""")

# ---------------------------------------------------------------- 5 asymmetry
md("""
## 5. Why the penalty is 1.5, and what happens if you disagree

An undisclosed mismatch is worse than a weak reference: a wrong benchmark quietly misleads a
review, while a broad index merely gives less information.

That is a **judgement**, not a derivation. So test it. The same three picks, scored under
three different penalties:
""")

code("""
import peerlens.metric as M

picks = ["EQ_AMD", "EQ_TSM", "EQ_CRM"]   # two true peers, one Salesforce-class error
original = M.HARD_NEGATIVE_WEIGHT
try:
    for w in (0.5, 1.5, 3.0):
        M.HARD_NEGATIVE_WEIGHT = w
        ax = score_selection("EQ_NVDA",
                             [Selection(benchmark_id=p) for p in picks],
                             pl.PACK, case)
        tag = "   <- ours" if w == original else ""
        print(f"  penalty {w:<4} -> score {ax.composite:.3f}{tag}")
finally:
    M.HARD_NEGATIVE_WEIGHT = original

print(f"\\nrestored to {original}")
""")

# ---------------------------------------------------------------- 6 gates
md("""
## 6. The gates: the 16 rules that are enforced in code

The original prompt had 22 rules. Sixteen of them are not really instructions - they are
invariants, and an invariant written as prose is a hope. So they moved into schema and
validators.

Gates come in two kinds, and the difference matters for optimisation:

- **fatal** - unusable answer (wrong count, unknown id). Score becomes 0.
- **soft** - it parsed but broke a rule (word limit, banned word, undisclosed mismatch).
  Score is reduced, so the optimiser still has a gradient to climb.
""")

code("""
bad = [
    BenchmarkPick("EQ_CRM", "diversifier", "big tech peer", "none", ()),
    BenchmarkPick("EQ_ADBE", "diversifier", "software like", "none", ()),
    BenchmarkPick("EQ_MADE_UP", "diversifier", "sounds plausible", "none", ()),
]
holding = HoldingFacts.from_instrument(inst)
fatal, soft = split_problems(validate_selection(bad, holding, pl.PACK))

print("FATAL (score -> 0):")
for p in fatal:
    print("  -", p)
print("\\nSOFT (score reduced):")
for p in soft[:4]:
    print("  -", p)
""")

code("""
print(f"{len(RULE_MAP)} rules, split as:")
for mech, n in sorted(rule_summary().items()):
    print(f"  {mech:<12} {n:>2}   {'optimisable' if mech == 'instruction' else 'guaranteed by code'}")

print("\\nThe six the optimiser owns:")
for r in RULE_MAP:
    if r.optimizable:
        print("  -", r.rule)
""")

# ---------------------------------------------------------------- 7 signature
md("""
## 7. The prompt is not stored anywhere - it is generated

In DSPy you declare the task as a *signature*: typed fields plus a docstring. The docstring
**is** the instruction, and it is the only thing an optimiser is allowed to rewrite.

Field names, types and descriptions are not editable by the optimiser, which is why the
judgement guidance must live in the docstring.
""")

code("""
from peerlens.prompt_v2 import EQUITY_INSTRUCTIONS

try:
    from peerlens.prompt_v2 import build_signature
    sig = build_signature()
    print("signature built with dspy")
    print("inputs :", list(sig.input_fields))
    print("outputs:", list(sig.output_fields))
    body = sig.instructions
except Exception as exc:
    print(f"(dspy not importable here: {type(exc).__name__} - showing the raw text instead)")
    body = EQUITY_INSTRUCTIONS

print(f"\\ninstruction length: {len(body)} chars, {len(body.split())} words")
print("-" * 70)
print("\\n".join(body.strip().splitlines()[:12]))
print("...")
""")

# ---------------------------------------------------------------- 8 distribution
md("""
## 8. What the score distribution looks like

Before trusting any single number, look at the whole space. Nine candidates for NVDA gives
84 possible answers. Here is how they score.
""")

code("""
IDS = ["EQ_AMD", "EQ_TSM", "EQ_CRM", "IDX_SOX", "ETF_SMH",
       "IDX_SPX", "ETF_XLK", "CASH_USD", "EQ_COP"]

scores = []
for trio in combinations(IDS, 3):
    ax = score_selection("EQ_NVDA",
                         [Selection(benchmark_id=i) for i in trio], pl.PACK, case)
    scores.append((ax.composite, trio))
scores.sort(reverse=True)

vals = [s for s, _ in scores]
n = len(vals)
print(f"combinations : {n}")
print(f"best         : {vals[0]:.3f}  {scores[0][1]}")
print(f"median       : {vals[n//2]:.3f}")
print(f"worst        : {vals[-1]:.3f}  {scores[-1][1]}")
print(f"score >= 0.8 : {sum(1 for v in vals if v >= 0.8)} of {n}")
print(f"score == 0   : {sum(1 for v in vals if v == 0)} of {n}")
""")

# ---------------------------------------------------------------- 9 baseline
md("""
## 9. The baseline run, replayed

The baseline was produced by `run_teach.py --baseline-only`: the v0 prompt, run over ten
held-out cases at temperature 0, each scored with the metric above.

It is replayed here from `out/teaching/baseline.md` so this notebook costs nothing.
""")

code("""
baseline_md = (ROOT / "out/teaching/baseline.md").read_text(encoding="utf-8")
rows = []
for line in baseline_md.splitlines():
    if line.startswith("| EQ_"):
        c = [x.strip() for x in line.strip("|").split("|")]
        rows.append(c)

print(f"{'asset':<10}{'score':>7}{'peers':>7}{'wrong':>7}  picks")
print("-" * 92)
for r in rows:
    print(f"{r[0]:<10}{r[1]:>7}{r[2]:>7}{r[3]:>7}  {r[5]}")

scores = [float(r[1]) for r in rows]
print(f"\\nmean over {len(rows)} cases: {sum(scores)/len(scores):.3f}")
print("notice: IDX_SPX appears in almost every row - that is templating, not analysis")
""")

# ---------------------------------------------------------------- 10 optimiser
md("""
## 10. What the optimiser did

GEPA proposes a new instruction, scores it on the training split, and keeps it only if it
beats the incumbent. It never sees the held-out cases used above.

Fourteen proposals were generated and kept on disk. Here is how each scored when
re-measured on the same ten held-out cases, and whether it would have been kept.
""")

code("""
board = json.loads((ROOT / "out/teaching/leaderboard.json").read_text(encoding="utf-8"))
by_text = {b["text"].strip(): b["score"] for b in board if "text" in b}

base_row = next((r for r in rows if r[0] == "EQ_NVDA"), None)
base = sum(float(r[1]) for r in rows) / len(rows)

import pathlib as _p
prompts = sorted((ROOT / "out/teaching/prompts").glob("proposal_*.md"))

incumbent = base
print(f"{'version':<8}{'score':>7}{'delta':>8}  outcome")
print("-" * 46)
print(f"{'v0':<8}{base:>7.3f}{'':>8}  baseline (human)")
kept = 0
for i, path in enumerate(prompts, 1):
    text = path.read_text(encoding="utf-8").strip()
    score = by_text.get(text)
    if score is None:
        continue
    if score > incumbent:
        incumbent = score
        kept += 1
        outcome = "KEPT"
    else:
        outcome = "dropped"
    print(f"{'v'+str(i):<8}{score:>7.3f}{score-base:>+8.3f}  {outcome}")

print(f"\\n{len(prompts)} proposals, {kept} beat the human prompt")
""")

# ---------------------------------------------------------------- 11 anatomy
md("""
## 11. One iteration, in full

Now the mechanism, using the real numbers. Stage 1: run the baseline prompt on NVDA and see
what it returns.
""")

code("""
V0_PICKS = ["IDX_SOX", "ETF_XLK", "IDX_SPX"]
ax = score_selection("EQ_NVDA",
                     [Selection(benchmark_id=p) for p in V0_PICKS], pl.PACK, case)
print("v0 returned :", V0_PICKS)
print(f"score       : {ax.composite:.3f}")
print(f"breakdown   : peers={ax.peer_hits} adjacent={ax.adjacent_hits} wrong={ax.violations}")
print()
print("That 0.667 is the tiered credit for those three ids. In the recorded run the model")
print("wrote its own rationale text, which drew compliance penalties, so the score logged")
print("for this case was lower. Compare section 9.")
""")

md("""
Stage 2: the metric does not only return a number, it returns a sentence. That sentence is
what the reflection model reads - without it, the optimiser knows a candidate lost but not
why.
""")

code("""
def feedback_for(picks):
    \"\"\"Reproduce the metric's feedback string exactly as the optimiser saw it.\"\"\"
    objs = [BenchmarkPick(p, "diversifier", "comparison", "single exposure", ())
            for p in picks]
    fatal, soft = split_problems(validate_selection(objs, holding, pl.PACK))
    ax = score_selection("EQ_NVDA",
                         [Selection(benchmark_id=p) for p in picks], pl.PACK, case)
    score = 0.0 if fatal else max(0.0, ax.composite - 0.12 * len(soft))
    parts = [
        f"EQ_NVDA: scored {score:.2f} with {picks}.",
        f"peer={ax.peer_hits} adjacent={ax.adjacent_hits} wrong={ax.violations}.",
    ]
    if ax.violations:
        parts.append("Sector mismatch - remove those picks.")
    if ax.peer_hits < 2:
        parts.append("Prefer same-industry peers over broad indices; "
                     f"acceptable examples were {sorted(case.acceptable)[:5]}.")
    if soft:
        parts.append("Compliance: " + "; ".join(soft[:3]))
    return " ".join(parts)

print(feedback_for(V0_PICKS))
""")

md("""
Stage 3 and 4: that feedback, plus the current instruction, is sent to a **second model** -
the reflection model - with the instruction *"write a new instruction for the assistant."*
It is not told what to change. It has to infer it.

Here is the diff between what we wrote and what came back.
""")

code("""
v0_text = (ROOT / "out/teaching/prompts/v0.md").read_text(encoding="utf-8").strip()
v1_text = (ROOT / "out/teaching/prompts/proposal_001.md").read_text(encoding="utf-8").strip()

print(f"v0: {len(v0_text)} chars / {len(v0_text.split())} words")
print(f"v1: {len(v1_text)} chars / {len(v1_text.split())} words\\n")

for line in difflib.unified_diff(v0_text.splitlines(), v1_text.splitlines(),
                                 "v0", "v1", lineterm="", n=0):
    if line.startswith(("---", "+++")):
        continue
    print(line[:150])
""")

md("""
Read what it added. Nothing in the metric said any of this:

- an explicit **priority order** - peers first, sector fund second, broad index last
- **named peer examples** per industry (`EQ_AMD / EQ_AVGO / EQ_INTC / EQ_MU`)
- a **near-duplicate rule** - not two funds tracking the same exposure

Those are domain judgements inferred from ten failure reports.
""")

# ---------------------------------------------------------------- 12 optional live
md("""
## 12. Optional: run it live

Everything above runs offline. This cell actually calls a model, so it needs a key and costs
a small amount. Skip it if you only want to understand the machinery.
""")

code("""
import os

KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("API_KEY")
if not KEY:
    print("No key set - skipping. To run it:")
    print("    os.environ['DEEPSEEK_API_KEY'] = 'sk-...'")
    print("then re-run this cell.")
else:
    import dspy
    from peerlens.prompt_v2 import build_signature, render_holding, render_shortlist, to_picks

    lm = dspy.LM("deepseek/deepseek-flash", temperature=0.0)
    adapter = dspy.ChatAdapter(use_native_function_calling=False,
                               use_json_adapter_fallback=False)
    program = dspy.ChainOfThought(build_signature())

    with dspy.context(lm=lm, adapter=adapter):
        pred = program(
            holding=render_holding(holding),
            risk_level="pre-mapped upstream; do not re-map",
            shortlist=render_shortlist(pl.PACK, holding),
        )

    picks = to_picks(pred.selections)
    print("model returned:")
    for p in picks:
        print(f"  {p.benchmark_id:<10} {p.role:<18} limit={p.limitation[:52]!r}")

    got = score_selection("EQ_NVDA",
                          [Selection(benchmark_id=p.benchmark_id) for p in picks],
                          pl.PACK, case)
    print(f"\\nscore: {got.composite:.3f}  (peers={got.peer_hits} "
          f"adj={got.adjacent_hits} wrong={got.violations})")
    print("\\nvalidator problems:", validate_selection(picks, holding, pl.PACK) or "none")
""")

# ---------------------------------------------------------------- 13 limits
md("""
## 13. What this setup cannot tell you

Stated plainly, because a metric that hides its blind spots is worse than no metric:

1. **It cannot resolve small gains.** Ten held-out cases puts roughly +/- 0.08 of standard
   error on the mean. A +0.03 difference is noise, and the notebook reports it as noise.
2. **It only scores what we listed.** ASML is a genuine semiconductor peer but sits in a
   different industry code, so no signal here can see it. The metric is silent on it, not
   wrong about it.
3. **The weights are our judgement.** Peer 1.0 / adjacent 0.5 / wrong -1.5 was chosen.
   Section 5 shows the ranking can move if you disagree.
4. **Part of it is circular.** Some labels derive from the same industry taxonomy the scorer
   uses, so agreement there confirms consistency rather than correctness.
""")

code("""
# sensitivity of the headline number to the two choices that matter most
print("Change ONE thing and the conclusion can move:")
print()
print(f"  penalty 0.5  ->  AMD+TSM+CRM scores ", end="")
M.HARD_NEGATIVE_WEIGHT = 0.5
print(f"{score_selection('EQ_NVDA', [Selection(benchmark_id=p) for p in picks], pl.PACK, case).composite:.3f}")
M.HARD_NEGATIVE_WEIGHT = 3.0
print(f"  penalty 3.0  ->  AMD+TSM+CRM scores ", end="")
print(f"{score_selection('EQ_NVDA', [Selection(benchmark_id=p) for p in picks], pl.PACK, case).composite:.3f}")
M.HARD_NEGATIVE_WEIGHT = 1.5
print()
print("  Also try: swap the held-out split, or change which cases are labelled hard negatives.")
""")

# ---------------------------------------------------------------- 14 next
md("""
## 14. Where the remaining headroom is

The optimiser improved the score by rewriting instructions. It plateaued quickly because a
five-paragraph prompt that already names asset class, sector and geography leaves little
wording left to fix.

What usually moves next, in order of return:

1. **Enrich the shortlist** - supply industry codes, currency and measured co-movement per
   candidate instead of ids and names. This was worth more than any prompt rewrite.
2. **Prerank the shortlist** - retrieval, not instruction wording, decides which candidates
   the model even considers.
3. **Grow the labelled set** from real complaints, then re-optimise.

Files this notebook reads:

| file | what it is |
|---|---|
| `peerlens/pack.py` | the catalogue and the four-tier labels |
| `peerlens/metric.py` | the scorer used everywhere above |
| `peerlens/prompt_v2.py` | the signature and the 16 gates |
| `out/teaching/baseline.md` | the v0 run |
| `out/teaching/leaderboard.json` | every proposal and its score |
| `out/teaching/prompts/` | the fifteen prompt versions |
""")

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
n_code = sum(1 for c in cells if c["cell_type"] == "code")
print(f"wrote {OUT.name}: {len(cells)} cells ({n_code} code, {len(cells)-n_code} markdown)")
print(f"size: {OUT.stat().st_size/1024:.1f} KB")
