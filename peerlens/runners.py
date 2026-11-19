"""The systems under test.

``ScriptedRunner`` variants are deterministic stand-ins that model three
different *qualities* of prompt.  They exist so the harness, metric and report
can be validated end to end with no API key and no cost.  They are **not** a
measurement of any language model - see README.

``DspyRunner`` (in ``dspy_program.py``) is the real path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

from .marketdata import ReturnPanel
from .metric import ROLES, Selection
from .model import BR_BROAD, BR_INDUSTRY, BR_SECTOR, Case, Instrument, Pack
from .signals import description_scores, taxonomy_score


class Runner(Protocol):
    name: str

    def select(self, case: Case, pack: Pack, panel: Optional[ReturnPanel] = None) -> list[Selection]:
        ...


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------
def _role_for(inst: Optional[Instrument]) -> str:
    """Assign a role the way a careful human would: by what the instrument is."""
    if inst is None:
        return "diversifier"
    if inst.kind == "cash":
        return "liquidity_reference"
    if inst.breadth == BR_BROAD:
        return "whole_portfolio"
    if inst.breadth == BR_INDUSTRY:
        return "dominant_sleeve"
    return "diversifier"


def _finalise(ids: Sequence[str], pack: Pack, case: Case) -> list[Selection]:
    """Ensure exactly three distinct selections, never the asset itself.

    ``ids`` must be a full preference ranking, not just the top three, so that
    topping up stays principled instead of falling back to alphabetical order.
    """
    out: list[str] = []
    for i in ids:
        if i == case.asset_id or i in out or i not in pack:
            continue
        out.append(i)
        if len(out) == 3:
            break
    if len(out) < 3:
        raise ValueError(
            f"{case.asset_id}: ranking only produced {len(out)} usable candidates"
        )
    return [Selection(benchmark_id=i, role=_role_for(pack.get(i))) for i in out]


# ---------------------------------------------------------------------------
# A: naive - description similarity only
# ---------------------------------------------------------------------------
@dataclass
class NaiveDescriptionRunner:
    """Models a prompt that just asks 'find similar instruments' and hands the
    model the whole catalogue.  No structured reasoning about exposure, so it
    leans on wording and drifts toward whatever the pack describes most often.
    """

    name: str = "A: naive (description only)"

    def select(self, case, pack, panel=None):
        scores = description_scores(pack, case.asset_id, [i for i in pack.ids])
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
        return _finalise([k for k, _ in ranked], pack, case)


# ---------------------------------------------------------------------------
# B: sector-only
# ---------------------------------------------------------------------------
@dataclass
class SectorOnlyRunner:
    """Models a prompt that reasons about *sector* but never drills into
    industry.  This is the realistic mid-quality prompt, and it is exactly the
    one that puts a payments network next to a bank.
    """

    name: str = "B: sector-only"

    def select(self, case, pack, panel=None):
        asset = pack[case.asset_id]
        scored: list[tuple[float, str]] = []
        for inst in pack:
            if inst.id == case.asset_id:
                continue
            same_sector = 1.0 if (inst.sector and inst.sector == asset.sector) else 0.0
            same_class = 1.0 if inst.asset_class == asset.asset_class else 0.0
            scored.append((2.0 * same_sector + 1.0 * same_class, inst.id))
        scored.sort(key=lambda kv: (-kv[0], kv[1]))
        return _finalise([i for _, i in scored], pack, case)


# ---------------------------------------------------------------------------
# C: industry-aware + enriched pack
# ---------------------------------------------------------------------------
@dataclass
class IndustryAwareRunner:
    """Models an enriched prompt: structured industry metadata plus measured
    co-movement supplied as context, and an explicit instruction to diversify.

    This is the 'context engineering beats prompt engineering' hypothesis made
    executable.
    """

    name: str = "C: industry-aware + enriched pack"
    use_comovement: bool = True

    def select(self, case, pack, panel=None):
        asset = pack[case.asset_id]
        desc = description_scores(pack, case.asset_id, [i for i in pack.ids])

        com: dict[str, float] = {}
        if self.use_comovement and panel is not None:
            from .signals import comovement_scores

            raw = comovement_scores(panel, case.asset_id, [i for i in pack.ids])
            com = {k: v for k, v in raw.items() if v is not None}

        scored: list[tuple[float, str]] = []
        for inst in pack:
            if inst.id == case.asset_id:
                continue
            tax = taxonomy_score(asset, inst)
            c = com.get(inst.id, float("nan"))
            c_score = 0.0 if c != c else max(0.0, c)
            total = 2.0 * tax + 0.8 * c_score + 0.6 * desc.get(inst.id, 0.0)
            scored.append((total, inst.id))

        scored.sort(key=lambda kv: (-kv[0], kv[1]))
        ranked = [i for _, i in scored]

        # Answer shape borrowed from the real task: keep one or two anchor
        # peers in the asset's own industry, then add genuinely distinct
        # comparison references.  A broad index is a reference, never an
        # anchor; two trackers of the same index are one option, not two.
        asset_industry = asset.industry
        strong = [i for i in ranked
                  if pack[i].industry and pack[i].industry == asset_industry]
        refs = [i for i in ranked
                if i not in strong and pack[i].breadth in (BR_SECTOR, BR_BROAD)]

        def distinct(candidate: str, chosen: list[str]) -> bool:
            if not chosen:
                return True
            scores = description_scores(pack, candidate, chosen)
            return all(v < 0.60 for v in scores.values())

        picked: list[str] = []
        for pool, cap in ((strong, 2), (refs, 3)):
            for inst_id in pool:
                if len(picked) >= cap:
                    break
                if inst_id in picked or not distinct(inst_id, picked):
                    continue
                picked.append(inst_id)
        for inst_id in ranked:
            if len(picked) == 3:
                break
            if inst_id not in picked:
                picked.append(inst_id)

        order = picked + [i for i in ranked if i not in picked]
        return _finalise(order, pack, case)


SCRIPTED_RUNNERS: tuple[Runner, ...] = (
    NaiveDescriptionRunner(),
    SectorOnlyRunner(),
    IndustryAwareRunner(),
    IndustryAwareRunner(name="C': industry-aware, no co-movement", use_comovement=False),
)
