"""End-to-end demo: label the pack, measure the signals, compare the prompts.

    python run_demo.py                     # synthetic returns, scripted runners
    python run_demo.py --returns r.csv     # real returns you supply
    python run_demo.py --lm openai/gpt-4o-mini   # run the real DSPy programs

Nothing here needs an API key unless you pass ``--lm``.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# DSPy 3.5.0 is vendored into .pydeps so the optional path works without
# touching the interpreter's environment. Harmless when it is absent.
_ROOT = Path(__file__).resolve().parents[1]
for _p in (_ROOT / ".pydeps", _ROOT):   # vendored dspy, then the package itself
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import peerlens as pl
from peerlens import harness, labeling, marketdata, runners
from peerlens.model import Case, Pack


def build_panel(args, pack: Pack):
    if args.returns:
        path = Path(args.returns)
        if not path.exists():
            sys.exit(f"--returns: no such file {path}")
        return marketdata.load_returns_csv(path)
    return marketdata.synthetic_panel(pack, n_days=args.days, seed=args.seed)


def select_cases(args) -> tuple[Case, ...]:
    if not args.assets:
        return pl.CASES
    wanted = {a.strip().upper() for a in args.assets.split(",") if a.strip()}
    missing = [a for a in wanted if not (a.startswith("EQ_") or True)]
    chosen = tuple(c for c in pl.CASES if c.asset_id in wanted)
    unknown = wanted - {c.asset_id for c in chosen}
    if unknown:
        sys.exit(f"--assets: unknown case(s) {sorted(unknown)}")
    return chosen


def fmt(x: float, nd: int = 2) -> str:
    return "  n/a" if x != x else f"{x:.{nd}f}"


def write_signals_csv(verdicts, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [v.as_row() for v in verdicts]
    fieldnames = list(rows[0].keys()) if rows else ["asset_id", "bench_id"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--returns", help="CSV of real returns (date + tickers)")
    parser.add_argument("--days", type=int, default=750,
                        help="length of the synthetic panel")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--assets", help="comma separated case ids to run")
    parser.add_argument("--out", default="out", help="output directory")
    parser.add_argument("--lm", help="DSPy LM string, e.g. openai/gpt-4o-mini")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    pack = pl.PACK
    cases = select_cases(args)
    panel = build_panel(args, pack)
    out = Path(args.out)

    def say(msg: str = "") -> None:
        if not args.quiet:
            print(msg)

    say("=" * 78)
    say("PEER-LABELLING HARNESS")
    say("=" * 78)
    say(f"catalogue        : {len(pack)} instruments")
    say(f"cases            : {len(cases)}")
    if args.returns:
        say(f"returns          : {args.returns} ({len(panel)} rows)")
    else:
        say(f"returns          : SYNTHETIC factor model, {len(panel)} days, "
            f"seed={args.seed}")
        say("                   not market data - see README")

    # ---------------------------------------------------------------- signals
    say()
    say("-" * 78)
    say("1. WHICH SIGNAL ACTUALLY PREDICTS A PEER?")
    say("-" * 78)
    report = labeling.agreement_report(cases, pack, panel)
    header = (f"{'signal':<13}{'prec':>6}{'recall':>8}{'f1':>7}{'acc':>7}"
              f"{'hardAcc':>9}{'fpHard':>8}{'pos':>6}{'neg':>6}")
    say(header)
    say("-" * len(header))
    for name, a in report.items():
        say(f"{name:<13}{fmt(a.precision):>6}{fmt(a.recall):>8}{fmt(a.f1):>7}"
            f"{fmt(a.accuracy):>7}{fmt(a.hard_accuracy):>9}{a.fp_hard:>8}"
            f"{a.support_pos:>6}{a.support_neg:>6}")
    say()
    say("hardAcc / fpHard are computed on within-sector confusions only - the")
    say("cross-sector column is inflated because those negatives follow from the")
    say("taxonomy definition itself.")

    # ----------------------------------------------------------- triangulate
    say()
    say("-" * 78)
    say("2. TRIANGULATION")
    say("-" * 78)
    verdicts = labeling.build_verdicts(cases, pack, panel)
    summary = labeling.triangulation_summary(verdicts)
    for label in ("accept", "reject", "conflict", "insufficient"):
        say(f"  {label:<14}{summary.get(label, 0):>7}")
    vs = labeling.curated_vs_triangulated(cases, verdicts)
    total = sum(vs.values()) or 1
    say(f"  {'vs curated':<14}{vs.get('agree', 0):>7} agree "
        f"({100 * vs.get('agree', 0) / total:.1f}%), "
        f"{vs.get('disagree', 0)} disagree, {vs.get('abstain', 0)} abstain")

    conflicts = labeling.conflict_queue(cases, verdicts)
    say(f"  conflicts on curated pairs: {len(conflicts)}")

    missed = labeling.missed_peers(cases, verdicts)
    if missed:
        say()
        say(f"  curated peers every signal misses ({len(missed)}) - human review:")
        for asset_id, bench_id, best in missed[:8]:
            say(f"    {asset_id:<10} -> {bench_id:<12} (closest signal: {best})")

    # ------------------------------------------------------------ comparison
    say()
    say("-" * 78)
    say("3. DOES CONTEXT BEAT WORDING?")
    say("-" * 78)

    scripted = harness.compare(runners.SCRIPTED_RUNNERS, cases, pack, panel)
    results = list(scripted)

    if args.lm:
        try:
            import dspy
            from peerlens import dspy_program
        except Exception as exc:  # pragma: no cover
            sys.exit(f"--lm requires dspy installed: {exc}")
        say(f"  running real DSPy programs against {args.lm} ...")
        lm = dspy.LM(args.lm)
        results += harness.compare(dspy_program.dspy_runners(lm), cases, pack, panel)

    say(harness.render_comparison(results))

    # ---------------------------------------------------------------- output
    out.mkdir(parents=True, exist_ok=True)
    (out / "comparison.md").write_text(
        "# Peer-labelling comparison\n\n"
        f"Catalogue: {len(pack)} instruments. Cases: {len(cases)}.\n\n"
        + harness.render_comparison(results)
        + "\n## Per case\n\n"
        + harness.render_per_case(results, cases)
        + "\n## Picks\n\n"
        + "\n".join(harness.render_picks(r, cases, pack) for r in results),
        encoding="utf-8",
    )
    harness.write_csv(results, out / "per_case.csv")
    write_signals_csv(verdicts, out / "signals.csv")

    with (out / "conflicts.md").open("w", encoding="utf-8") as fh:
        fh.write("# Conflict queue\n\n")
        fh.write("Pairs where the signals disagree and curated truth exists.\n\n")
        fh.write("| asset | benchmark | taxonomy | comovement | description |\n")
        fh.write("|---|---|---|---|---|\n")
        for v in conflicts:
            fh.write(
                f"| {v.asset_id} | {v.bench_id} "
                f"| {fmt(v.scores.get('taxonomy') or float('nan'))} "
                f"| {fmt(v.scores.get('comovement') or float('nan'))} "
                f"| {fmt(v.scores.get('description') or float('nan'))} |\n"
            )

    say()
    say(f"wrote: {out/'comparison.md'}, {out/'per_case.csv'}, "
        f"{out/'signals.csv'}, {out/'conflicts.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
