"""Run every runner over the test bed, then render the comparison.

The output answers one question - *does better context or a better prompt move
the peer number?* - and it answers it as a table, not an opinion.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Sequence

from .marketdata import ReturnPanel
from .metric import AxisScores, Aggregate, Selection, aggregate, score_selection
from .model import Case, Pack
from .runners import Runner


@dataclass
class RunnerResult:
    runner: str
    aggregate: Aggregate
    per_case: dict[str, AxisScores] = field(default_factory=dict)
    picks: dict[str, list[Selection]] = field(default_factory=dict)

    def hardest_cases(self, n: int = 5) -> list[tuple[str, float]]:
        return sorted(self.per_case.items(), key=lambda kv: kv[1].composite)[:n]

    def violations(self, cases: Sequence[Case]) -> dict[str, int]:
        """Which unrelated instruments did this runner reach for, and how often?"""
        by_asset = {c.asset_id: c for c in cases}
        tally: dict[str, int] = {}
        for asset_id, picks in self.picks.items():
            case = by_asset.get(asset_id)
            if case is None:
                continue
            for sel in picks:
                if sel.benchmark_id in case.unacceptable:
                    tally[sel.benchmark_id] = tally.get(sel.benchmark_id, 0) + 1
        return dict(sorted(tally.items(), key=lambda kv: -kv[1]))


def evaluate_runner(
    runner: Runner,
    cases: Sequence[Case],
    pack: Pack,
    panel: Optional[ReturnPanel] = None,
) -> RunnerResult:
    scores: list[tuple[str, AxisScores]] = []
    per_case: dict[str, AxisScores] = {}
    picks: dict[str, list[Selection]] = {}

    for case in cases:
        selections = runner.select(case, pack, panel)
        axes = score_selection(case.asset_id, selections, pack, case)
        per_case[case.asset_id] = axes
        picks[case.asset_id] = list(selections)
        scores.append((case.asset_id, axes))

    return RunnerResult(
        runner=runner.name,
        aggregate=aggregate(scores),
        per_case=per_case,
        picks=picks,
    )


def compare(
    runners: Iterable[Runner],
    cases: Sequence[Case],
    pack: Pack,
    panel: Optional[ReturnPanel] = None,
) -> list[RunnerResult]:
    return [evaluate_runner(r, cases, pack, panel) for r in runners]


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------
def render_comparison(results: Sequence[RunnerResult]) -> str:
    if not results:
        return "_no results_\n"

    headers = [
        "system under test",
        "score",
        "peer credit",
        "peer hits",
        "hard neg",
        "format ok",
        "dup exp",
        "mean roles",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for res in results:
        a = res.aggregate
        lines.append(
            "| "
            + " | ".join(
                [
                    res.runner,
                    f"**{a.composite:.3f}**",
                    f"{a.peer_credit:.3f}",
                    f"{a.peer_hit_rate:.3f}",
                    f"{a.hard_negative_rate:.3f}",
                    f"{a.format_rate:.3f}",
                    f"{a.duplicate_rate:.3f}",
                    f"{a.mean_distinct_roles:.2f}",
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_per_case(results: Sequence[RunnerResult], cases: Sequence[Case]) -> str:
    headers = ["asset", *[r.runner.split(":")[0] for r in results]]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for case in cases:
        row = [case.asset_id.replace("EQ_", "")]
        for res in results:
            axes = res.per_case.get(case.asset_id)
            if axes is None:
                row.append("-")
                continue
            flag = "" if not axes.duplicate_exposure else " !dup"
            if axes.wrong_count or axes.unknown_ids:
                flag += " !fmt"
            row.append(f"{axes.composite:.2f}{flag}")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def render_picks(result: RunnerResult, cases: Sequence[Case], pack: Pack) -> str:
    lines = [f"### {result.runner}", "", "| asset | picks | roles | score |", "|---|---|---|---|"]
    for case in cases:
        picks = result.picks.get(case.asset_id, [])
        labels = []
        for sel in picks:
            inst = pack.get(sel.benchmark_id)
            name = inst.name if inst else sel.benchmark_id
            labels.append(name)
        axes = result.per_case.get(case.asset_id)
        lines.append(
            f"| {case.asset_id.replace('EQ_', '')} | {', '.join(labels)} | "
            f"{', '.join(s.role[:12] for s in picks)} | "
            f"{axes.composite:.2f} |"
        )
    return "\n".join(lines) + "\n"


def write_csv(results: Sequence[RunnerResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "runner",
                "asset",
                "picks",
                "score",
                "peer_credit",
                "peer_hits",
                "adjacent_hits",
                "violations",
                "duplicate_exposure",
                "distinct_roles",
                "format_ok",
            ]
        )
        for res in results:
            for asset_id, axes in sorted(res.per_case.items()):
                picks = "|".join(s.benchmark_id for s in res.picks.get(asset_id, []))
                writer.writerow(
                    [
                        res.runner,
                        asset_id,
                        picks,
                        f"{axes.composite:.4f}",
                        f"{axes.peer_credit:.4f}",
                        axes.peer_hits,
                        axes.adjacent_hits,
                        axes.violations,
                        int(axes.duplicate_exposure or axes.near_duplicate),
                        axes.distinct_roles,
                        int(not (axes.wrong_count or axes.unknown_ids)),
                    ]
                )
