"""The scoring function: tiered, asymmetric, and decomposed.

Design choices worth defending:

* **Four tiers, not a single similarity number.** A peer earns full credit, an
  adjacent proxy earns half, an unrelated instrument costs.  Collapsing these
  into one similarity score is what makes prompt comparison useless.
* **Asymmetric.** A hard negative - a payments network offered as a peer of a
  bank - costs more than a miss, because an undisclosed mismatch is the failure
  mode the review process actually cares about.
* **Broad indices are adjacent, never peers.** An S&P 500 reference is a
  legitimate whole-portfolio reference for almost any equity, so punishing it
  would be wrong.  Rewarding it would let a system score well by picking three
  broad indices, which is exactly the behaviour we are trying to detect.
  Half credit is the honest setting, and it is why ``breadth`` is data.
* **Decomposed.** A composite that hides a role-diversity failure is worse than
  no number, so every axis is returned alongside it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from .model import BR_INDUSTRY, Case, Pack

ROLES = (
    "whole_portfolio",
    "dominant_sleeve",
    "diversifier",
    "liquidity_reference",
)

ADJACENT_CREDIT = 0.5
HARD_NEGATIVE_WEIGHT = 1.5
DUPLICATE_PENALTY = 0.80
NEAR_DUPLICATE_COSINE = 0.60


@dataclass(frozen=True)
class Selection:
    """One benchmark choice produced by a system under test."""

    benchmark_id: str
    role: str = "diversifier"
    rationale: str = ""

    def __post_init__(self) -> None:
        if self.role not in ROLES:
            object.__setattr__(self, "role", "diversifier")


@dataclass(frozen=True)
class AxisScores:
    peer_hits: int
    adjacent_hits: int
    violations: int
    peer_credit: float
    hard_negative_rate: float
    unknown_ids: tuple[str, ...]
    wrong_count: bool
    duplicate_exposure: bool
    near_duplicate: bool
    distinct_roles: int
    composite: float

    def as_row(self) -> dict[str, object]:
        return {
            "peer_hits": self.peer_hits,
            "adjacent_hits": self.adjacent_hits,
            "violations": self.violations,
            "peer_credit": round(self.peer_credit, 3),
            "hard_negative_rate": round(self.hard_negative_rate, 3),
            "duplicate_exposure": self.duplicate_exposure,
            "near_duplicate": self.near_duplicate,
            "distinct_roles": self.distinct_roles,
            "composite": round(self.composite, 3),
        }


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _near_duplicate(picked: set[str], pack: Pack) -> bool:
    """Two trackers of the same index are one option, not two.

    Detected on description similarity because the catalogue has no explicit
    'tracks the same underlying' field.  A production system should have one.
    """
    from .signals import description_scores

    ids = sorted(picked)
    if len(ids) < 2:
        return False
    for i, a in enumerate(ids):
        scores = description_scores(pack, a, ids[i + 1:])
        if any(v >= NEAR_DUPLICATE_COSINE for v in scores.values()):
            return True
    return False


def score_selection(
    asset_id: str,
    selections: Sequence[Selection],
    pack: Pack,
    case: Case,
) -> AxisScores:
    ids = [s.benchmark_id for s in selections]
    picked = set(ids)

    unknown = tuple(sorted(i for i in picked if i not in pack))
    wrong_count = len(ids) != 3 or len(picked) != len(ids)

    peer_hits = len(picked & case.acceptable)
    adjacent_hits = len(picked & case.adjacent)
    violations = len(picked & case.negatives)

    peer_credit = (peer_hits + ADJACENT_CREDIT * adjacent_hits) / 3.0
    hard_negative_rate = violations / 3.0

    industries = {pack[i].industry for i in picked if i in pack and pack[i].industry}
    # Three different companies in one industry is a legitimate peer set - it is
    # what the task asks for.  Three *funds* tracking the same industry is the
    # redundancy the review rules forbid, so that is what gets flagged.  All
    # three must carry an industry: a broad index has none, and "one peer plus
    # two broad indices" is a correct answer, not a duplicate.
    same_tier_redundant = (
        len(picked) == 3
        and all(
            i in pack and pack[i].kind in ("index", "etf") and pack[i].industry
            for i in picked
        )
        and len(industries) == 1
    )
    duplicate_exposure = same_tier_redundant
    near_dup = _near_duplicate(picked, pack) if len(picked) >= 2 else False

    distinct_roles = len({s.role for s in selections})

    if unknown or wrong_count:
        composite = 0.0
    else:
        base = _clamp01(peer_credit - HARD_NEGATIVE_WEIGHT * hard_negative_rate)
        if duplicate_exposure or near_dup:
            base *= DUPLICATE_PENALTY
        composite = _clamp01(base)

    return AxisScores(
        peer_hits=peer_hits,
        adjacent_hits=adjacent_hits,
        violations=violations,
        peer_credit=peer_credit,
        hard_negative_rate=hard_negative_rate,
        unknown_ids=unknown,
        wrong_count=wrong_count,
        duplicate_exposure=duplicate_exposure,
        near_duplicate=near_dup,
        distinct_roles=distinct_roles,
        composite=composite,
    )


# ---------------------------------------------------------------------------
# DSPy-shaped adapter
# ---------------------------------------------------------------------------
def _coerce_selection(item) -> Optional[Selection]:
    """Accept a Selection, a pydantic model, a dict, or a bare id string."""
    if isinstance(item, Selection):
        return item
    if isinstance(item, dict):
        bench_id = item.get("benchmark_id") or item.get("id")
        if not bench_id:
            return None
        return Selection(
            benchmark_id=str(bench_id),
            role=item.get("role") or "diversifier",
            rationale=item.get("rationale") or "",
        )
    bench_id = getattr(item, "benchmark_id", None) or getattr(item, "id", None)
    if bench_id:
        return Selection(
            benchmark_id=str(bench_id),
            role=getattr(item, "role", None) or "diversifier",
            rationale=getattr(item, "rationale", "") or "",
        )
    if isinstance(item, str) and item:
        return Selection(benchmark_id=item)
    return None


def peer_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    """``dspy.Prediction(score, feedback)`` when DSPy is installed, else a float.

    Follows the DSPy 3.5 metric contract: continuous at evaluation time,
    binarised during optimisation, feedback always populated.
    """
    selections = [
        s for s in (_coerce_selection(item) for item in getattr(pred, "selections", []))
        if s is not None
    ]
    axes = score_selection(gold.asset_id, selections, gold.pack, gold.case)

    problems = []
    if axes.wrong_count:
        problems.append("did not return exactly three distinct ids")
    if axes.unknown_ids:
        problems.append(f"ids not in pack: {list(axes.unknown_ids)}")
    if axes.violations:
        names = sorted(s.benchmark_id for s in selections
                       if s.benchmark_id in gold.case.negatives)
        problems.append(f"unrelated selections: {names}")
    if axes.duplicate_exposure:
        problems.append("all three share one industry")
    if axes.near_duplicate:
        problems.append("two selections track the same underlying")
    if axes.peer_hits == 0 and axes.violations == 0:
        problems.append("no peer-level benchmark selected")

    feedback = "; ".join(problems) if problems else "all selections defensible"

    try:
        import dspy
    except Exception:  # pragma: no cover - DSPy absent
        return float(axes.composite)

    if trace is not None:
        return dspy.Prediction(score=(axes.composite >= 0.66), feedback=feedback)
    return dspy.Prediction(score=float(axes.composite), feedback=feedback)


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------
@dataclass
class Aggregate:
    n: int
    composite: float
    peer_credit: float
    peer_hit_rate: float
    adjacent_rate: float
    hard_negative_rate: float
    format_rate: float
    duplicate_rate: float
    mean_distinct_roles: float
    per_case: dict[str, float] = field(default_factory=dict)

    def as_row(self) -> dict[str, object]:
        return {
            "n": self.n,
            "score": round(self.composite, 3),
            "peer_credit": round(self.peer_credit, 3),
            "peer_hit_rate": round(self.peer_hit_rate, 3),
            "hard_neg_rate": round(self.hard_negative_rate, 3),
            "format_ok": round(self.format_rate, 3),
            "dup_rate": round(self.duplicate_rate, 3),
            "roles": round(self.mean_distinct_roles, 2),
        }


def aggregate(scores: Sequence[tuple[str, AxisScores]]) -> Aggregate:
    if not scores:
        return Aggregate(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    n = len(scores)
    return Aggregate(
        n=n,
        composite=sum(s.composite for _, s in scores) / n,
        peer_credit=sum(s.peer_credit for _, s in scores) / n,
        peer_hit_rate=sum(s.peer_hits for _, s in scores) / (3.0 * n),
        adjacent_rate=sum(s.adjacent_hits for _, s in scores) / (3.0 * n),
        hard_negative_rate=sum(s.hard_negative_rate for _, s in scores) / n,
        format_rate=sum(0.0 if (s.wrong_count or s.unknown_ids) else 1.0
                        for _, s in scores) / n,
        duplicate_rate=sum(
            1.0 if (s.duplicate_exposure or s.near_duplicate) else 0.0
            for _, s in scores
        ) / n,
        mean_distinct_roles=sum(s.distinct_roles for _, s in scores) / n,
        per_case={case_id: s.composite for case_id, s in scores},
    )
