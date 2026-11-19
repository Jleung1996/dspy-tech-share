"""Triangulate the three signals into labels, and measure each signal honestly.

The output is not 'the answer'.  It is:

1. a label per pair (``accept`` / ``reject`` / ``conflict`` / ``insufficient``);
2. a conflict queue - the pairs a human should actually look at;
3. an agreement report that says, per signal, how well it predicts curated
   truth, split by how hard the negative was.

Item 3 is why the harness is worth building.  It answers a question you cannot
answer by reading prompts: *which* of your similarity notions is doing the work,
and which one is quietly wrong.

A note on honesty: cross-sector negatives follow mechanically from the taxonomy
definition, so every signal scores well on them.  The number that actually
discriminates is ``fp_hard`` - false positives on within-sector confusions like
'bank' vs 'payments network'.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Sequence

from .marketdata import ReturnPanel
from .model import Case, Pack
from .signals import (
    DEFAULT_CONFIG,
    SIGNAL_NAMES,
    SignalConfig,
    comovement_scores,
    description_scores,
    taxonomy_scores,
    votes,
)

ACCEPT = "accept"
REJECT = "reject"
CONFLICT = "conflict"
INSUFFICIENT = "insufficient"

MIN_VOTES_FOR_ACCEPT = 2
MIN_AVAILABLE = 2


@dataclass(frozen=True)
class PairVerdict:
    asset_id: str
    bench_id: str
    scores: Mapping[str, Optional[float]]
    votes_for: int
    available: int
    label: str
    config: SignalConfig = DEFAULT_CONFIG

    @property
    def disagreeing(self) -> tuple[str, ...]:
        cast = []
        for name in SIGNAL_NAMES:
            value = self.scores.get(name)
            if value is None:
                continue
            cast.append((name, value >= self.config.threshold(name)))
        if len(cast) < 2:
            return ()
        if all(flag for _, flag in cast) or not any(flag for _, flag in cast):
            return ()
        return tuple(name for name, _ in cast)

    def as_row(self) -> dict[str, object]:
        row: dict[str, object] = {
            "asset_id": self.asset_id,
            "bench_id": self.bench_id,
            "votes": self.votes_for,
            "available": self.available,
            "label": self.label,
            "disagreeing": "|".join(self.disagreeing),
        }
        for name in SIGNAL_NAMES:
            row[name] = self.scores.get(name)
        return row


def label_pair(
    scores: Mapping[str, Optional[float]],
    config: SignalConfig = DEFAULT_CONFIG,
) -> tuple[str, int, int]:
    cast, available = votes(scores, config)
    if available < MIN_AVAILABLE:
        return INSUFFICIENT, cast, available
    if cast >= MIN_VOTES_FOR_ACCEPT:
        return ACCEPT, cast, available
    if cast == 0:
        return REJECT, cast, available
    return CONFLICT, cast, available


def _pair_scores(pack: Pack, panel: Optional[ReturnPanel], asset_id: str,
                 bench_id: str) -> dict[str, Optional[float]]:
    return {
        "taxonomy": taxonomy_scores(pack, asset_id, [bench_id]).get(bench_id),
        "comovement": comovement_scores(panel, asset_id, [bench_id]).get(bench_id),
        "description": description_scores(pack, asset_id, [bench_id]).get(bench_id),
    }


def build_verdicts(
    cases: Sequence[Case],
    pack: Pack,
    panel: Optional[ReturnPanel] = None,
    config: SignalConfig = DEFAULT_CONFIG,
) -> list[PairVerdict]:
    """Score every (asset, candidate) pair in the pack."""
    all_ids = sorted(pack.ids)
    out: list[PairVerdict] = []

    for case in cases:
        if case.asset_id not in pack:
            raise KeyError(f"case asset {case.asset_id} not in pack")
        candidates = [i for i in all_ids if i != case.asset_id]

        tax = taxonomy_scores(pack, case.asset_id, candidates)
        com = comovement_scores(panel, case.asset_id, candidates)
        txt = description_scores(pack, case.asset_id, candidates)

        for bench_id in candidates:
            scores = {
                "taxonomy": tax.get(bench_id),
                "comovement": com.get(bench_id),
                "description": txt.get(bench_id),
            }
            label, cast, available = label_pair(scores, config)
            out.append(
                PairVerdict(
                    asset_id=case.asset_id,
                    bench_id=bench_id,
                    scores=scores,
                    votes_for=cast,
                    available=available,
                    label=label,
                    config=config,
                )
            )
    return out


# ---------------------------------------------------------------------------
# curated truth
# ---------------------------------------------------------------------------
def truth_pairs(cases: Sequence[Case]) -> Iterable[tuple[str, str, bool, bool]]:
    """Yield (asset, bench, is_peer, is_hard_negative) for every curated pair."""
    for case in cases:
        for bench_id in sorted(case.acceptable):
            yield case.asset_id, bench_id, True, False
        for bench_id in sorted(case.hard_negatives):
            yield case.asset_id, bench_id, False, True
        for bench_id in sorted(case.unacceptable):
            yield case.asset_id, bench_id, False, False


# ---------------------------------------------------------------------------
# agreement against curated truth
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SignalAgreement:
    signal: str
    tp: int
    fp: int
    fn: int
    tn: int
    abstained: int
    fp_hard: int
    tn_hard: int
    hard_support: int

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else float("nan")

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else float("nan")

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        if math.isnan(p) or math.isnan(r) or (p + r) == 0:
            return float("nan")
        return 2 * p * r / (p + r)

    @property
    def accuracy(self) -> float:
        denom = self.tp + self.fp + self.fn + self.tn
        return (self.tp + self.tn) / denom if denom else float("nan")

    @property
    def hard_accuracy(self) -> float:
        """Accuracy on within-sector negatives only - the discriminating test.

        Includes true positives so it reads as 'how often does this signal get
        the hard cases right overall', not just how often it stays quiet.
        """
        denom = self.tp + self.fn + self.fp_hard + self.tn_hard
        if not denom:
            return float("nan")
        return (self.tp + self.tn_hard) / denom

    @property
    def support_pos(self) -> int:
        return self.tp + self.fn

    @property
    def support_neg(self) -> int:
        return self.tn + self.fp


def agreement_report(
    cases: Sequence[Case],
    pack: Pack,
    panel: Optional[ReturnPanel] = None,
    config: SignalConfig = DEFAULT_CONFIG,
) -> dict[str, SignalAgreement]:
    tally: dict[str, dict[str, int]] = {
        name: {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "abstained": 0,
               "fp_hard": 0, "tn_hard": 0, "hard_support": 0}
        for name in SIGNAL_NAMES
    }

    for asset_id, bench_id, is_peer, is_hard in truth_pairs(cases):
        scores = _pair_scores(pack, panel, asset_id, bench_id)
        for name in SIGNAL_NAMES:
            value = scores[name]
            if value is None:
                tally[name]["abstained"] += 1
                continue
            said_yes = value >= config.threshold(name)
            if is_peer and said_yes:
                tally[name]["tp"] += 1
            elif is_peer and not said_yes:
                tally[name]["fn"] += 1
            elif not is_peer and said_yes:
                tally[name]["fp"] += 1
            else:
                tally[name]["tn"] += 1
                if is_hard:
                    tally[name]["tn_hard"] += 1
            if is_hard:
                tally[name]["hard_support"] += 1
                if said_yes and not is_peer:
                    tally[name]["fp_hard"] += 1

    return {
        name: SignalAgreement(
            signal=name,
            tp=t["tp"], fp=t["fp"], fn=t["fn"], tn=t["tn"],
            abstained=t["abstained"],
            fp_hard=t["fp_hard"], tn_hard=t["tn_hard"],
            hard_support=t["hard_support"],
        )
        for name, t in tally.items()
    }


def triangulation_summary(verdicts: Sequence[PairVerdict]) -> dict[str, int]:
    return dict(Counter(v.label for v in verdicts))


def conflict_queue(
    cases: Sequence[Case],
    verdicts: Sequence[PairVerdict],
    limit: Optional[int] = None,
) -> list[PairVerdict]:
    """Conflicts restricted to pairs where curated truth exists."""
    truth = {(a, b) for a, b, _, _ in truth_pairs(cases)}
    out = [
        v for v in verdicts
        if v.label == CONFLICT and (v.asset_id, v.bench_id) in truth
    ]
    out.sort(key=lambda v: (v.asset_id, v.bench_id))
    return out[:limit] if limit else out


def curated_vs_triangulated(
    cases: Sequence[Case], verdicts: Sequence[PairVerdict]
) -> dict[str, int]:
    """How often the 2-of-3 rule reproduces the hand-curated label."""
    truth = {(a, b): is_peer for a, b, is_peer, _ in truth_pairs(cases)}
    counts: Counter[str] = Counter()
    for v in verdicts:
        key = (v.asset_id, v.bench_id)
        if key not in truth:
            continue
        expected = ACCEPT if truth[key] else REJECT
        if v.label == expected:
            counts["agree"] += 1
        elif v.label in (CONFLICT, INSUFFICIENT):
            counts["abstain"] += 1
        else:
            counts["disagree"] += 1
    return dict(counts)


def missed_peers(
    cases: Sequence[Case], verdicts: Sequence[PairVerdict]
) -> list[tuple[str, str, str]]:
    """Curated peers that every signal rejects - the human-review shortlist.

    These are the supply-chain and business-model links no taxonomy or return
    correlation will surface, so they are exactly where a human is still needed.
    """
    by_pair = {(v.asset_id, v.bench_id): v for v in verdicts}
    out: list[tuple[str, str, str]] = []
    for asset_id, bench_id, is_peer, _ in truth_pairs(cases):
        if not is_peer:
            continue
        v = by_pair.get((asset_id, bench_id))
        if v is None:
            continue
        if v.label in (REJECT,):
            worst = sorted(
                ((n, s) for n, s in v.scores.items() if s is not None),
                key=lambda kv: -kv[1],
            )
            out.append((asset_id, bench_id, worst[0][0] if worst else "none"))
    return out
