"""Teaching demo: watch a deliberately bad prompt get better, version by version.

The narrative for a tech share:

    1. start from a prompt a sharp intern would write in one line
    2. score it on the same ruler every later version uses
    3. let GEPA propose new instructions
    4. score EVERY proposal on that same ruler
    5. read the diffs to see what it actually learned

Step 4 is the part that matters. GEPA's internal bookkeeping is not the point -
the point is that one fixed evaluation set is applied unchanged to every prompt
version, so the improvement is comparable rather than asserted.

    python run_teach.py --lm deepseek/deepseek-flash
    python run_teach.py --lm deepseek/deepseek-flash --limit 10 --eval-limit 8
"""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (_ROOT / ".pydeps", _ROOT):   # vendored dspy, then the package itself
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import peerlens as pl
from peerlens.metric import Selection, score_selection
from peerlens.prompt_v2 import (
    BenchmarkPick,
    HoldingFacts,
    build_signature,
    render_holding,
    render_shortlist,
    split_problems,
    to_picks,
    validate_selection,
)

# ---------------------------------------------------------------------------
# v0: the realistic mediocre prompt.
#
# Clear role, clear task, pick-from-list constraint, sensible criteria, asks for
# a rationale. This is what a competent analyst writes on the first pass, and it
# is what passes review in a demo. It is NOT a strawman.
#
# What it omits - and what GEPA therefore has to discover:
#   * look-through: economic exposure != settlement/valuation currency
#   * peer companies as distinct from broad or sector indices
#   * mismatch disclosure (currency / geography)
#   * a role taxonomy across the three picks
#   * any no-numerics guardrail
# ---------------------------------------------------------------------------
from peerlens.prompt_v2 import BASELINE_V0

NAIVE_PROMPT = BASELINE_V0

SOFT_PENALTY = 0.12


def build_examples(limit: int):
    import dspy

    pack = pl.PACK
    out = []
    for case in pl.CASES[:limit]:
        holding = HoldingFacts.from_instrument(pack[case.asset_id])
        out.append(
            dspy.Example(
                holding=render_holding(holding),
                risk_level="pre-mapped upstream; do not re-map",
                shortlist=render_shortlist(pack, holding),
                asset_id=case.asset_id,
                gold_case=case,
                holding_facts=holding,
            ).with_inputs("holding", "risk_level", "shortlist")
        )
    return out


def make_metric():
    """Same metric as the baseline run: fatal gates zero, soft penalties subtract."""
    import dspy

    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        picks = to_picks(getattr(pred, "selections", []))
        fatal, soft = split_problems(
            validate_selection(picks, gold.holding_facts, pl.PACK)
        )
        selections = [Selection(benchmark_id=p.benchmark_id, role=p.role) for p in picks]
        axes = score_selection(gold.asset_id, selections, pl.PACK, gold.gold_case)
        picked = [p.benchmark_id for p in picks]

        if fatal:
            return dspy.Prediction(
                score=0.0,
                feedback=f"{gold.asset_id}: unusable. " + "; ".join(fatal[:3])
                + f". Picks {picked}. Return three distinct ids from the shortlist.",
            )

        score = max(0.0, axes.composite - SOFT_PENALTY * len(soft))
        parts = [
            f"{gold.asset_id}: scored {score:.2f} with {picked}.",
            f"peer={axes.peer_hits} adjacent={axes.adjacent_hits} wrong={axes.violations}.",
        ]
        if axes.violations:
            parts.append("Sector mismatch - remove those picks.")
        if axes.peer_hits < 2:
            parts.append(
                "Prefer same-industry peers over broad indices; "
                f"acceptable examples were {sorted(gold.gold_case.acceptable)[:5]}."
            )
        if soft:
            parts.append("Compliance: " + "; ".join(soft[:3]))
        return dspy.Prediction(score=float(score), feedback=" ".join(parts))

    return metric


class RecordingProposer:
    """Wraps GEPA's proposer, keeping and persisting every instruction it writes.

    Writes each proposal to disk *before* returning it, so a crash costs at most
    one prompt. Losing a long run's output because everything lived in memory is
    a mistake worth engineering against.
    """

    def __init__(self, inner, dump_dir: Path | None = None):
        self.inner = inner
        self.proposals: list[str] = []
        self.dump_dir = dump_dir
        self._n = 0

    def __call__(self, candidate, reflective_dataset, components_to_update):
        out = self.inner(candidate, reflective_dataset, components_to_update)
        for _name, text in out.items():
            if text and text.strip():
                clean = text.strip()
                self.proposals.append(clean)
                self._n += 1
                if self.dump_dir is not None:
                    self.dump_dir.mkdir(parents=True, exist_ok=True)
                    (self.dump_dir / f"proposal_{self._n:03d}.md").write_text(
                        clean + "\n", encoding="utf-8"
                    )
        return out


def score_instruction(instruction, examples, lm, adapter, metric_impl) -> tuple[float, list]:
    import dspy

    program = dspy.ChainOfThought(build_signature(instruction))
    scores = []
    failures = 0
    for ex in examples:
        try:
            with dspy.context(lm=lm, adapter=adapter):
                pred = program(
                    holding=ex.holding,
                    risk_level=ex.risk_level,
                    shortlist=ex.shortlist,
                )
            scores.append(float(metric_impl(ex, pred).score))
        except Exception:
            failures += 1
            scores.append(0.0)
    mean = sum(scores) / len(scores) if scores else 0.0
    return mean, [round(s, 3) for s in scores]


def diff_lines(before: str, after: str, limit: int = 14) -> list[str]:
    import difflib

    a = before.strip().splitlines()
    b = after.strip().splitlines()
    out = [
        line
        for line in difflib.unified_diff(a, b, lineterm="", n=0)
        if line and not line.startswith(("---", "+++"))
    ]
    return out[:limit]


def stratified_indices(n_total: int, n_pick: int) -> list[int]:
    """Even stride across the catalogue so every sector is represented.

    Taking the first N would give a set that is almost entirely Information
    Technology, because that is how the cases are ordered.
    """
    if n_pick >= n_total:
        return list(range(n_total))
    stride = max(1, n_total // n_pick)
    return list(range(0, n_total, stride))[:n_pick]


def report_baseline(instruction, examples, lm, adapter, metric_impl, out_dir: Path) -> int:
    """Score v0 case by case and print the detail needed to trust the number."""
    import dspy

    program = dspy.ChainOfThought(build_signature(instruction))
    rows = []
    for ex in examples:
        picks = []
        fatal: list[str] = []
        soft: list[str] = []
        axes = None
        score = 0.0
        error = ""
        try:
            with dspy.context(lm=lm, adapter=adapter):
                pred = program(
                    holding=ex.holding,
                    risk_level=ex.risk_level,
                    shortlist=ex.shortlist,
                )
            picks = to_picks(getattr(pred, "selections", []))
            fatal, soft = split_problems(
                validate_selection(picks, ex.holding_facts, pl.PACK)
            )
            selections = [
                Selection(benchmark_id=p.benchmark_id, role=p.role) for p in picks
            ]
            axes = score_selection(ex.asset_id, selections, pl.PACK, ex.gold_case)
            score = (
                0.0 if fatal
                else max(0.0, axes.composite - SOFT_PENALTY * len(soft))
            )
        except Exception as exc:
            error = type(exc).__name__
            fatal = [error]
        rows.append(
            dict(asset=ex.asset_id, picks=[p.benchmark_id for p in picks],
                 score=score, fatal=fatal, soft=soft, axes=axes, error=error)
        )
        flags = ("FATAL " + fatal[0][:28]) if fatal else (f"{len(soft)} soft")
        print(f"  {ex.asset_id:10s} {score:5.2f}  "
              f"{', '.join(r.replace('EQ_', '') for r in rows[-1]['picks']):34s} {flags}")

    mean = sum(r["score"] for r in rows) / len(rows) if rows else 0.0
    print()
    print(f"BASELINE SCORE  {mean:.3f}   over {len(rows)} held-out cases")

    if rows:
        print(f"  mean peer hits   {sum((r['axes'].peer_hits if r['axes'] else 0) for r in rows)/len(rows):.2f} / 3")
        print(f"  mean wrong picks {sum((r['axes'].violations if r['axes'] else 0) for r in rows)/len(rows):.2f} / 3")
        print(f"  fatal answers    {sum(1 for r in rows if r['fatal'])} / {len(rows)}")
        print(f"  soft issues      {sum(len(r['soft']) for r in rows)} total")

    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Baseline (v0)",
        "",
        "```",
        instruction.strip(),
        "```",
        "",
        f"**Score: {mean:.3f}** over {len(rows)} held-out cases, temperature 0.",
        "",
        "| asset | score | peers | adj | wrong | picks | issues |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        a = r["axes"]
        lines.append(
            f"| {r['asset']} | {r['score']:.2f} | {a.peer_hits if a else '-'} "
            f"| {a.adjacent_hits if a else '-'} | {a.violations if a else '-'} "
            f"| {', '.join(r['picks']) or '-'} "
            f"| {'; '.join((r['fatal'] + r['soft'])[:2]) or 'ok'} |"
        )
    (out_dir / "baseline.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {out_dir/'baseline.md'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lm", required=True)
    ap.add_argument("--reflection-lm")
    ap.add_argument("--auto", default="light", choices=["light", "medium", "heavy"])
    ap.add_argument("--max-metric-calls", type=int,
                    help="hard budget; overrides --auto. Keeps a demo run bounded")
    ap.add_argument("--limit", type=int, default=12, help="cases GEPA trains on")
    ap.add_argument("--eval-limit", type=int, default=10,
                    help="cases every prompt version is scored on")
    ap.add_argument("--max-candidates", type=int, default=10,
                    help="cap how many proposed prompts get scored")
    ap.add_argument("--show-prompts", action="store_true",
                    help="print every prompt in full as it is scored")
    ap.add_argument("--adapter", default="chat", choices=["xml", "chat"])
    ap.add_argument("--temperature", type=float, default=0.0,
                    help="0 keeps the baseline reproducible")
    ap.add_argument("--baseline-only", action="store_true",
                    help="score v0 and stop; do not run GEPA")
    ap.add_argument("--out", default="out/teaching")
    args = ap.parse_args(argv)

    import dspy
    from dspy.teleprompt.gepa import InstructionProposer

    lm = dspy.LM(args.lm, temperature=args.temperature)
    reflection = dspy.LM(args.reflection_lm or args.lm)
    adapter = (
        dspy.ChatAdapter(use_native_function_calling=False, use_json_adapter_fallback=False)
        if args.adapter == "chat"
        else dspy.XMLAdapter(use_native_function_calling=False, use_json_adapter_fallback=False)
    )

    all_examples = build_examples(len(pl.CASES))
    eval_idx = stratified_indices(len(all_examples), args.eval_limit)
    eval_set = set(eval_idx)
    eval_examples = [all_examples[i] for i in eval_idx]
    train_pool = [ex for i, ex in enumerate(all_examples) if i not in eval_set]
    trainset = train_pool[: args.limit] if args.limit else train_pool
    n_val = max(2, len(trainset) // 4) if len(trainset) >= 8 else 0
    valset = trainset[-n_val:] if n_val else None
    if valset:
        trainset = trainset[:-n_val]

    metric_impl = make_metric()

    print("=" * 78)
    print("v0 PROMPT")
    print("=" * 78)
    print(NAIVE_PROMPT)
    print()
    print(f"eval set: {len(eval_examples)} cases, held out from optimisation")
    print("  " + ", ".join(ex.asset_id.replace("EQ_", "") for ex in eval_examples))
    print()

    if args.baseline_only:
        return report_baseline(
            NAIVE_PROMPT, eval_examples, lm, adapter, metric_impl, Path(args.out)
        )

    # ---- score the bad prompt on the fixed ruler -------------------------
    print(f"scoring baseline on {len(eval_examples)} held-out cases ...")
    base_score, base_per_case = score_instruction(
        NAIVE_PROMPT, eval_examples, lm, adapter, metric_impl
    )
    print(f"  baseline score: {base_score:.3f}")

    # ---- let GEPA work ---------------------------------------------------
    program = dspy.ChainOfThought(build_signature(NAIVE_PROMPT))
    proposer = RecordingProposer(
        InstructionProposer(adapter=adapter, max_chars=2200),
        dump_dir=Path(args.out) / "prompts",
    )

    print(f"\nrunning GEPA: {len(trainset)} train / {len(valset or [])} val, auto={args.auto}")
    optimizer = dspy.GEPA(
        metric=metric_impl,
        # Exactly one budget knob may be set: a hard metric-call cap, or a preset.
        **(
            {"max_metric_calls": args.max_metric_calls}
            if args.max_metric_calls
            else {"auto": args.auto}
        ),
        reflection_lm=reflection,
        instruction_proposer=proposer,
        # use_merge=False keeps a clean 1:1 mapping between a table row and a
        # prompt GEPA actually wrote. Merge candidates come from a separate
        # proposer and would break that correspondence in a teaching artefact.
        use_merge=False,
        # track_stats exposes GEPA's own per-candidate scores alongside ours.
        track_stats=True,
    )
    # GEPA evaluates the program hundreds of times internally. Those calls need
    # an LM in context - passing `lm=` to dspy.LM is not the same as configuring
    # it. Without this, every metric call raises "No LM is loaded", every answer
    # scores 0, and the reflection step has nothing to learn from.
    with dspy.context(lm=lm, adapter=adapter):
        optimized = (
            optimizer.compile(program, trainset=trainset, valset=valset)
            if valset
            else optimizer.compile(program, trainset=trainset)
        )

    final_instruction = ""
    try:
        final_instruction = optimized.predict.signature.instructions.strip()
    except Exception:
        try:
            final_instruction = optimized.signature.instructions.strip()
        except Exception:
            pass

    # ---- assemble every distinct prompt version --------------------------
    versions: list[tuple[str, str]] = [("v0  bad baseline", NAIVE_PROMPT)]
    seen = {NAIVE_PROMPT.strip()}
    for text in proposer.proposals:
        key = text.strip()
        if key in seen:
            continue
        seen.add(key)
        versions.append((f"v{len(versions)}  GEPA proposal", key))
        if len(versions) >= args.max_candidates + 1:
            break
    if final_instruction and final_instruction not in seen:
        versions.append((f"v{len(versions)}  GEPA final", final_instruction))

    # ---- score every version on the SAME cases ---------------------------
    print(f"\nscoring {len(versions)} prompt versions on the same "
          f"{len(eval_examples)} cases ...")
    results = []
    for i, (label, text) in enumerate(versions):
        score, per_case = score_instruction(
            text, eval_examples, lm, adapter, metric_impl
        )
        results.append({
            "label": label,
            "score": score,
            "chars": len(text),
            "per_case": per_case,
            "text": text,
        })
        delta = "" if i == 0 else f"  ({score - base_score:+.3f} vs v0)"
        print(f"  {label:22s} {score:.3f}{delta}   ({len(text)} chars)")
        if args.show_prompts:
            print("  " + "-" * 70)
            for line in text.strip().splitlines():
                print("  | " + line)
            print("  " + "-" * 70)
            print()

    # ---- render ---------------------------------------------------------
    out = Path(args.out)
    (out / "prompts").mkdir(parents=True, exist_ok=True)

    base = results[0]["score"]
    body = [
        "# Watch a bad prompt get better",
        "",
        f"Model: `{args.lm}` · GEPA `{args.auto}` · "
        f"{len(trainset)} train / {len(valset or [])} val · "
        f"scored on {len(eval_examples)} held-out cases",
        "",
        "Every version below was scored by the **same metric on the same cases**,",
        "so the numbers are comparable. The gates (exactly three, in pack, no",
        "duplicates) zero a bad answer; soft penalties cover rationale rules.",
        "",
        "## Starting prompt",
        "",
        "```",
        NAIVE_PROMPT,
        "```",
        "",
        f"**Score: {base:.3f}**",
        "",
        "## Leaderboard",
        "",
        "| version | score | delta | chars |",
        "|---|---|---|---|",
    ]
    for r in results:
        delta = r["score"] - base
        sign = "+" if delta >= 0 else ""
        body.append(
            f"| {r['label']} | **{r['score']:.3f}** | "
            f"{'' if r is results[0] else f'{sign}{delta:.3f}'} | {r['chars']} |"
        )

    if len(results) > 1:
        best = max(results, key=lambda r: r["score"])
        body += [
            "",
            f"Best: **{best['label']}** at {best['score']:.3f} "
            f"({best['score'] - base:+.3f} vs baseline).",
        ]

    body += ["", "## Every prompt, in the order GEPA wrote it", ""]
    for i, r in enumerate(results):
        tag = r["label"].split()[0]
        (out / "prompts" / f"{tag}.md").write_text(r["text"].strip() + "\n", encoding="utf-8")

        delta = "" if i == 0 else f" ({r['score'] - base:.3f} vs v0)"
        body += [f"### {r['label']} — **{r['score']:.3f}**{delta}", ""]

        if i == 0:
            body.append("The prompt we started from.")
        else:
            changes = diff_lines(results[i - 1]["text"], r["text"])
            body.append("What changed from the previous version:")
            body.append("")
            if changes:
                body.append("```diff")
                body.extend(changes)
                body.append("```")
            else:
                body.append("_no textual change_")
        body += ["", "Full prompt:", "", "```", r["text"].strip(), "```", ""]

    (out / "leaderboard.md").write_text("\n".join(body) + "\n", encoding="utf-8")
    (out / "leaderboard.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"\nwrote {out/'leaderboard.md'} and {out/'leaderboard.json'}")
    print(f"prompt versions in {out/'prompts'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
