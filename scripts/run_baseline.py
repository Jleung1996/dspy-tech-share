"""Baseline run: the first honest number for the equity benchmark agent.

Until this has run once against a real model, nobody knows whether the system is
at 0.4 or 0.9 - and that number decides what to do next. Optimising before you
have it means optimising a guess.

    python run_baseline.py --lm openai/gpt-4o-mini
    python run_baseline.py --dry-run          # plumbing check, scripted stand-in

Writes:
    out/baseline.json     {case_id: [picks…]}   feeds run_regression.py --outputs
    out/baseline.md       the readable report

Reports four things, because they lead to different fixes:

    peer score      selection quality        -> pack / shortlist / retrieval
    validator pass  rationale compliance     -> prompt instructions, retry count
    regression      reported-bug recurrence  -> gate
    failures        what actually went wrong -> the next prompt revision
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
from peerlens.metric import Selection, aggregate, score_selection
from peerlens.prompt_v2 import (
    EQUITY_INSTRUCTIONS,
    BenchmarkPick,
    HoldingFacts,
    render_holding,
    render_shortlist,
    to_picks,
    validate_selection,
)

CASES_FILE = Path(__file__).resolve().parents[1] / "cases" / "regressions.yaml"


def curated_holdings() -> list[HoldingFacts]:
    """The 30 curated assets, converted to holding facts."""
    out: list[HoldingFacts] = []
    for case in pl.CASES:
        inst = pl.PACK[case.asset_id]
        out.append(HoldingFacts.from_instrument(inst))
    return out


def picks_from_scripted(ticker: str, pack) -> list[BenchmarkPick]:
    """Scripted stand-in so the plumbing is testable without a model."""
    from peerlens import runners
    from peerlens.model import Case

    runner = next(r for r in runners.SCRIPTED_RUNNERS if r.name.startswith("C:"))
    proxy = Case(asset_id=ticker, acceptable=frozenset(), adjacent=frozenset(),
                 hard_negatives=frozenset(), unacceptable=frozenset())
    return [
        BenchmarkPick(benchmark_id=s.benchmark_id, role=s.role,
                      relationship="", limitation="")
        for s in runner.select(proxy, pack)
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lm", help="DSPy LM string, e.g. openai/gpt-4o-mini")
    ap.add_argument("--dry-run", action="store_true",
                    help="use the scripted stand-in instead of a model")
    ap.add_argument("--adapter", default="chat", choices=["xml", "chat", "json"],
                    help="output adapter. 'chat' is the default here: DeepSeek "
                         "rejects JSON response_format, and its long free-text "
                         "fields break XML parsing more often than chat "
                         "delimiters do")
    ap.add_argument("--limit", type=int, help="only the first N curated cases")
    ap.add_argument("--retries", type=int, default=2,
                    help="retry a case this many times on adapter/parse failure. "
                         "A parse failure is recorded as a measurement, not a crash")
    ap.add_argument("--out", default="out")
    ap.add_argument("--show-instructions", action="store_true",
                    help="print the optimisable prompt and exit")
    args = ap.parse_args(argv)

    if args.show_instructions:
        print(EQUITY_INSTRUCTIONS)
        return 0

    pack = pl.PACK
    holdings = curated_holdings()
    if args.limit:
        holdings = holdings[: args.limit]

    program = None
    lm = None
    adapter = None
    if not args.dry_run:
        if not args.lm:
            ap.error("give --lm <model> or --dry-run")
        try:
            import dspy
        except ImportError:
            sys.exit("DSPy not importable. Expected it in .pydeps; see README.")
        from peerlens.prompt_v2 import build_signature

        lm = dspy.LM(args.lm)
        program = dspy.ChainOfThought(build_signature())

        # DeepSeek (and some others) reject `response_format`, so the JSON
        # adapter fallback must be off. DSPy 3.5 can otherwise retry through it
        # after a Chat/XML parse failure and hard-fail the request.
        if args.adapter == "xml":
            adapter = dspy.XMLAdapter(
                use_native_function_calling=False, use_json_adapter_fallback=False
            )
        elif args.adapter == "chat":
            adapter = dspy.ChatAdapter(
                use_native_function_calling=False, use_json_adapter_fallback=False
            )
        else:
            adapter = dspy.JSONAdapter()

    scores: list[tuple[str, object]] = []
    outputs: dict[str, list[BenchmarkPick]] = {}
    rows: list[dict] = []
    errors: list[tuple[str, str]] = []

    for holding in holdings:
        case = pl.CASE_BY_ASSET.get(holding.ticker)
        if case is None:
            continue

        picks: list[BenchmarkPick] = []
        if args.dry_run or program is None or lm is None:
            picks = picks_from_scripted(holding.ticker, pack)
        else:
            context = {"lm": lm}
            if adapter is not None:
                context["adapter"] = adapter
            last_error = ""
            for _attempt in range(args.retries + 1):
                try:
                    with dspy.context(**context):
                        pred = program(
                            holding=render_holding(holding),
                            risk_level="pre-mapped upstream; do not re-map",
                            shortlist=render_shortlist(pack, holding),
                        )
                    picks = to_picks(getattr(pred, "selections", []))
                    if picks:
                        break
                    last_error = "adapter returned no selections"
                except Exception as exc:
                    last_error = f"{type(exc).__name__}: {str(exc)[:140]}"
            if not picks:
                errors.append((holding.ticker, last_error))

        outputs[holding.ticker] = picks
        selections = [Selection(benchmark_id=p.benchmark_id, role=p.role) for p in picks]
        axes = score_selection(holding.ticker, selections, pack, case)
        scores.append((holding.ticker, axes))

        problems = validate_selection(picks, holding, pack)
        rows.append({
            "asset": holding.ticker,
            "picks": [p.benchmark_id for p in picks],
            "score": axes.composite,
            "peers": axes.peer_hits,
            "adjacent": axes.adjacent_hits,
            "wrong": axes.violations,
            "validator_problems": problems,
        })

    agg = aggregate(scores)
    n = len(rows) or 1
    validator_clean = sum(1 for r in rows if not r["validator_problems"]) / n
    peer_total = sum(r["peers"] for r in rows)
    wrong_total = sum(r["wrong"] for r in rows)

    # Split the headline number. A case that failed to *parse* is an
    # infrastructure defect; a case that parsed but chose badly is a judgement
    # defect. They need different fixes, so they need different numbers.
    parsed = [r for r in rows if r["picks"]]
    parse_adjusted = (
        sum(r["score"] for r in parsed) / len(parsed) if parsed else float("nan")
    )

    # regression gate over the cases that map onto a real holding
    reg_cases = regression.load_cases(CASES_FILE, pack)
    reg_outputs = {
        c.id: outputs.get(c.holding.ticker, []) for c in reg_cases
    }
    reg_results = regression.run_suite(reg_cases, reg_outputs, pack)
    reg_stats = regression.summarise(reg_results)

    print("=" * 78)
    print("BASELINE -", "dry run (scripted stand-in, NOT a model)" if args.dry_run
          else f"model: {args.lm}")
    print("=" * 78)
    print(f"cases                 {len(rows)}")
    print(f"peer score            {agg.composite:.3f}   (all cases, unparseable counted as 0)")
    print(f"peer score (parsed)   {parse_adjusted:.3f}   ({len(parsed)} cases that parsed)")
    print(f"  peer picks          {peer_total}   of {3*len(rows)} slots")
    print(f"  wrong picks         {wrong_total}")
    print(f"  peer precision      {agg.peer_hit_rate:.3f}")
    print(f"validator clean       {validator_clean:.1%} of cases")
    print(f"parse failures        {len(errors)} of {len(rows)} cases")
    print(f"regression            {reg_stats['passed']}/{reg_stats['total']} pass, "
          f"{reg_stats['blocking']} blocking")

    if errors:
        print("\nunparseable cases (a real failure mode, counted not hidden):")
        for ticker, err in errors[:5]:
            print(f"  {ticker:10s} {err}")

    # failure taxonomy - this is the thing that tells you what to fix
    from collections import Counter

    kinds: Counter[str] = Counter()
    for r in rows:
        for p in r["validator_problems"]:
            key = p.split(":")[-1].split("(")[0].strip()[:40]
            kinds[key] += 1
    if kinds:
        print("\nvalidator failure modes:")
        for k, c in kinds.most_common(8):
            print(f"  {c:3d}  {k}")

    worst = sorted(rows, key=lambda r: r["score"])[:5]
    print("\nweakest cases:")
    for r in worst:
        print(f"  {r['asset']:10s} {r['score']:.2f}  {', '.join(r['picks']) or '-'}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "baseline.json").write_text(
        json.dumps(
            {
                case_id: [
                    {"benchmark_id": p.benchmark_id, "role": p.role,
                     "relationship": p.relationship, "limitation": p.limitation,
                     "mismatches": list(p.mismatches)}
                    for p in picks
                ]
                for case_id, picks in outputs.items()
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    lines = [
        "# Baseline",
        "",
        f"source: {'scripted stand-in (not a model)' if args.dry_run else args.lm}",
        "",
        f"- peer score: **{agg.composite:.3f}**",
        f"- peer score on parsed cases: {parse_adjusted:.3f}",
        f"- parse failures: {len(errors)}/{len(rows)}",
        f"- peer picks: {peer_total}/{3*len(rows)}",
        f"- wrong picks: {wrong_total}",
        f"- validator clean: {validator_clean:.1%}",
        f"- regression: {reg_stats['passed']}/{reg_stats['total']} "
        f"({reg_stats['blocking']} blocking)",
        "",
        "| asset | score | peers | adj | wrong | picks | validator |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda x: x["score"]):
        note = "; ".join(r["validator_problems"][:2]) or "ok"
        lines.append(
            f"| {r['asset']} | {r['score']:.2f} | {r['peers']} | {r['adjacent']} "
            f"| {r['wrong']} | {', '.join(r['picks']) or '-'} | {note} |"
        )
    (out / "baseline.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nwrote: {out/'baseline.json'}, {out/'baseline.md'}")
    print("\nnext: python run_regression.py --outputs out/baseline.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
