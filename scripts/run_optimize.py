"""Run GEPA against the decomposed equity prompt, then diff what it wrote.

This is the deliverable: DSPy rewriting the 6 optimisable instructions while the
16 mechanical gates refuse to let it break anything.

    python run_optimize.py --lm deepseek/deepseek-flash --auto light
    python run_optimize.py --lm deepseek/deepseek-flash --auto light --limit 6

Why the budget knobs are small by default: GEPA proposes candidates, evaluates
each on the trainset, and reflects. A "light" run on 30 cases is already a few
hundred LM calls. Start small, confirm the loop turns, then spend.

The metric is deliberately two-part, because the two parts fail differently:

    gates   deterministic - exactly three, in pack, no banned words, word limit,
            mismatch disclosed. A candidate that fails a gate scores 0 no matter
            how good its reasoning was.
    quality peer tier score (peer 1.0 / adjacent 0.5 / wrong -1.5)

So GEPA can only earn score by choosing better benchmarks *within* the rules.
It cannot trade compliance for relevance, which is the failure mode of
optimising a monolithic prompt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (_ROOT / ".pydeps", _ROOT):   # vendored dspy, then the package itself
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import peerlens as pl
from peerlens import regression
from peerlens.metric import Selection, score_selection
from peerlens.prompt_v2 import (
    EQUITY_INSTRUCTIONS,
    BenchmarkPick,
    HoldingFacts,
    build_signature,
    render_holding,
    render_shortlist,
    to_picks,
    validate_selection,
)

CASES_FILE = Path(__file__).resolve().parents[1] / "cases" / "regressions.yaml"


def build_examples(limit: int | None = None):
    import dspy

    pack = pl.PACK
    examples = []
    for case in pl.CASES[: limit or len(pl.CASES)]:
        holding = HoldingFacts.from_instrument(pack[case.asset_id])
        examples.append(
            dspy.Example(
                holding=render_holding(holding),
                risk_level="pre-mapped upstream; do not re-map",
                shortlist=render_shortlist(pack, holding),
                asset_id=case.asset_id,
                gold_case=case,
                holding_facts=holding,
            ).with_inputs("holding", "risk_level", "shortlist")
        )
    return examples


def make_metric():
    """GEPA-shaped metric: fatal gates zero the score, soft ones subtract.

    The split matters. If every candidate scores 0 the optimiser has no gradient
    and cannot learn anything - which is exactly what happened on the first
    attempt, where strict word-count and banned-word checks zeroed every answer.
    A soft penalty keeps the signal while still pointing at what to fix.
    """
    import dspy
    from peerlens.prompt_v2 import split_problems

    SOFT_PENALTY = 0.12

    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        picks = to_picks(getattr(pred, "selections", []))
        case = gold.gold_case
        holding = gold.holding_facts

        fatal, soft = split_problems(validate_selection(picks, holding, pl.PACK))

        selections = [
            Selection(benchmark_id=p.benchmark_id, role=p.role) for p in picks
        ]
        axes = score_selection(gold.asset_id, selections, pl.PACK, case)

        picked = [p.benchmark_id for p in picks]

        if fatal:
            return dspy.Prediction(
                score=0.0,
                feedback=(
                    f"{gold.asset_id}: unusable answer. " + "; ".join(fatal[:4])
                    + f". Picks were {picked}. Return exactly three distinct ids "
                    "from the shortlist."
                ),
            )

        score = max(0.0, axes.composite - SOFT_PENALTY * len(soft))

        parts = [
            f"{gold.asset_id}: score {score:.2f}. Picked {picked}.",
            f"peer={axes.peer_hits} adjacent={axes.adjacent_hits} "
            f"wrong={axes.violations}.",
        ]
        if axes.violations:
            parts.append("Remove the wrong-sector picks.")
        if axes.peer_hits < 2:
            missed = sorted(case.acceptable)[:6]
            parts.append(f"Prefer true same-industry peers such as {missed}.")
        if soft:
            parts.append("Compliance: " + "; ".join(soft[:3]))
        return dspy.Prediction(score=float(score), feedback=" ".join(parts))

    return metric


def instruction_diff(before: str, after: str) -> list[str]:
    """Line-level diff, so the change is readable in a review."""
    import difflib

    a = before.strip().splitlines()
    b = after.strip().splitlines()
    return [
        line
        for line in difflib.unified_diff(a, b, fromfile="original", tofile="gepa", lineterm="")
        if line and not line.startswith(("---", "+++"))
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lm", required=True, help="task model, e.g. deepseek/deepseek-flash")
    ap.add_argument("--reflection-lm", help="stronger model for proposals; defaults to --lm")
    ap.add_argument("--auto", default="light", choices=["light", "medium", "heavy"])
    ap.add_argument("--limit", type=int, help="fewer cases = faster, weaker signal")
    ap.add_argument("--adapter", default="chat", choices=["xml", "chat"])
    ap.add_argument("--max-instruction-chars", type=int, default=2400,
                    help="cap on proposed instruction length")
    ap.add_argument("--out", default="out")
    ap.add_argument("--dry-run", action="store_true",
                    help="score the current prompt only; no optimisation")
    args = ap.parse_args(argv)

    import dspy

    lm = dspy.LM(args.lm)
    reflection = dspy.LM(args.reflection_lm or args.lm)
    adapter = (
        dspy.ChatAdapter(use_native_function_calling=False, use_json_adapter_fallback=False)
        if args.adapter == "chat"
        else dspy.XMLAdapter(use_native_function_calling=False, use_json_adapter_fallback=False)
    )

    examples = build_examples(args.limit)
    program = dspy.ChainOfThought(build_signature())
    metric = make_metric()

    # GEPA's reflective mutation needs a *working* proposer. Its default
    # InstructionProposer uses JSONAdapter, which DeepSeek rejects outright -
    # so every reflection call failed silently and GEPA reported
    # "did not propose a new candidate" 135 times while changing nothing.
    # Point the proposer at the same non-JSON adapter the task model uses.
    from dspy.teleprompt.gepa import InstructionProposer

    proposer = InstructionProposer(adapter=adapter)
    if args.max_instruction_chars:
        proposer = InstructionProposer(
            adapter=adapter, max_chars=args.max_instruction_chars
        )

    # Hold out a valset so GEPA selects for generalisation, not memorisation of
    # the train split.
    n_val = max(2, len(examples) // 4) if len(examples) >= 8 else 0
    trainset = examples[:-n_val] if n_val else examples
    valset = examples[-n_val:] if n_val else None

    print(f"optimising over {len(examples)} cases, model={args.lm}, auto={args.auto}")
    print(f"trainset {len(trainset)}, valset {len(valset or [])}")

    with dspy.context(lm=lm, adapter=adapter):
        if args.dry_run:
            scores = []
            for ex in examples:
                try:
                    pred = program(
                        holding=ex.holding,
                        risk_level=ex.risk_level,
                        shortlist=ex.shortlist,
                    )
                    result = metric(ex, pred)
                    scores.append(float(result.score))
                    print(f"  {ex.asset_id}: {float(result.score):.2f}  "
                          f"{str(getattr(result, 'feedback', ''))[:110]}")
                except Exception as exc:
                    print(f"  {ex.asset_id}: FAIL {type(exc).__name__}")
                    scores.append(0.0)
            mean = sum(scores) / len(scores) if scores else 0.0
            print(f"baseline mean score: {mean:.3f} over {len(scores)} cases")
            return 0

        optimizer = dspy.GEPA(
            metric=metric,
            auto=args.auto,
            reflection_lm=reflection,
            instruction_proposer=proposer,
        )
        optimized = (
            optimizer.compile(program, trainset=trainset, valset=valset)
            if valset
            else optimizer.compile(program, trainset=trainset)
        )

    before = EQUITY_INSTRUCTIONS
    after = optimized.predict.signature.instructions if hasattr(optimized, "predict") else ""

    print("\n" + "=" * 78)
    print("INSTRUCTIONS GEPA WROTE")
    print("=" * 78)
    print(after.strip())

    print("\n" + "=" * 78)
    print("DIFF vs ORIGINAL")
    print("=" * 78)
    for line in instruction_diff(before, after):
        print(line)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "optimized_instructions.txt").write_text(after, encoding="utf-8")
    (out / "prompt_diff.txt").write_text(
        "\n".join(instruction_diff(before, after)), encoding="utf-8"
    )
    try:
        optimized.save(str(out / "equity_benchmark_v2.json"))
        print(f"\nsaved program -> {out/'equity_benchmark_v2.json'}")
    except Exception as exc:  # pragma: no cover
        print(f"\ncould not save program: {type(exc).__name__}: {exc}")

    print(f"wrote {out/'optimized_instructions.txt'} and {out/'prompt_diff.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
