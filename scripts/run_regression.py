"""Run the regression suite against a set of outputs.

    python run_regression.py                          # scripted runner as stand-in
    python run_regression.py --outputs out/answers.json
    python run_regression.py --replay                 # show the reported failure

``--replay`` feeds back the ``reported_output`` recorded in each case, which is
the proof that the suite actually catches the bug it was written for. A
regression test that passes on the broken output is worthless.

Exit code is non-zero when a high-severity case fails, so this can gate a build.
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
from peerlens.prompt_v2 import BenchmarkPick, HoldingFacts, to_picks

DEFAULT_CASES = Path(__file__).resolve().parents[1] / "cases" / "regressions.yaml"


def picks_from_ids(ids, pack) -> list[BenchmarkPick]:
    """Minimal picks from bare ids, used for the replay path.

    Relationship and limitation are left empty on purpose: the replay is testing
    whether the *peer selection* was wrong, and reporting empty rationales as a
    separate validator finding keeps the two concerns visible.
    """
    return [
        BenchmarkPick(benchmark_id=str(i), role="diversifier",
                      relationship="", limitation="")
        for i in ids
        if i in pack
    ]


def outputs_from_runner(cases, pack, which: str) -> dict[str, list[BenchmarkPick]]:
    """Stand-in: whatever the scripted runner picks, shaped as picks."""
    from peerlens import runners

    runner = next(r for r in runners.SCRIPTED_RUNNERS if r.name.startswith(which))
    out: dict[str, list[BenchmarkPick]] = {}
    for case in cases:
        holding = case.holding
        inst = pack.get(holding.ticker)
        if inst is None:
            out[case.id] = []
            continue
        from peerlens.model import Case

        proxy = Case(asset_id=holding.ticker, acceptable=frozenset(),
                     adjacent=frozenset(), hard_negatives=frozenset(),
                     unacceptable=frozenset())
        picks = runner.select(proxy, pack)
        out[case.id] = [
            BenchmarkPick(
                benchmark_id=p.benchmark_id,
                role=p.role,
                relationship="",
                limitation="",
            )
            for p in picks
        ]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cases", default=str(DEFAULT_CASES))
    ap.add_argument("--outputs", help="JSON: {case_id: [ {benchmark_id, role, ...} ]}")
    ap.add_argument("--runner", default="C", help="scripted runner letter A|B|C")
    ap.add_argument("--replay", action="store_true",
                    help="feed the recorded reported_output back in")
    ap.add_argument("--out", default="out")
    args = ap.parse_args(argv)

    pack = pl.PACK
    cases = regression.load_cases(args.cases, pack)

    if args.outputs:
        raw = json.loads(Path(args.outputs).read_text(encoding="utf-8"))
        outputs = {k: to_picks(v) for k, v in raw.items()}
        # A batch run naturally emits one answer per *asset*, keyed by ticker,
        # while the suite indexes by case id. Accept either.
        for case in cases:
            if case.id not in outputs and case.holding.ticker in raw:
                outputs[case.id] = to_picks(raw[case.holding.ticker])
        # keep the report portable: never embed an absolute local path
        try:
            source = Path(args.outputs).resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            source = Path(args.outputs).name
    elif args.replay:
        outputs = {
            c.id: picks_from_ids(c.reported_output, pack) for c in cases
        }
        source = "replayed reported_output (should FAIL)"
    else:
        outputs = outputs_from_runner(cases, pack, args.runner)
        source = f"scripted runner {args.runner}"

    results = regression.run_suite(cases, outputs, pack)
    stats = regression.summarise(results)
    ok = regression.suite_passes(results)

    print("=" * 78)
    print(f"REGRESSION SUITE - source: {source}")
    print("=" * 78)
    print(regression.render_results(results))
    print(f"total {stats['total']} | passed {stats['passed']} | "
          f"failed {stats['failed']} | blocking {stats['blocking']}")
    print("RESULT:", "PASS" if ok else "FAIL (blocking)")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "regression.md").write_text(
        f"# Regression suite\n\nsource: {source}\n\n"
        + regression.render_results(results)
        + f"\n**{'PASS' if ok else 'FAIL'}** | {stats['passed']}/{stats['total']}\n",
        encoding="utf-8",
    )
    print(f"wrote: {out/'regression.md'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
