"""The real DSPy program behind the comparison table.

This module is optional.  Everything else in ``peerlens`` works without DSPy;
import this only when you have a model configured.

The experiment it implements is deliberately narrow, because the harness exists
to answer one question: **does richer context beat a better-worded prompt?**

    A: naive      - "find similar instruments", ids only
    B: current    - the carefully written review prompt, ids only
    C: enriched   - same prompt, plus sector / industry / currency / breadth
                    metadata AND measured co-movement supplied per candidate

Holding the prompt constant between B and C is the point.  If C wins, the lever
was context, not wording.

Notes on DSPy 3.5 specifics worth knowing before you edit this:

* ``XMLAdapter`` is the default adapter now. Scalar values are literal text,
  not XML-escaped, and ``<value/>`` means null while ``<value></value>`` means
  an empty string - so avoid ``Any`` and string/container unions in fields.
* ``ChainOfThought``'s ``reasoning`` is ``dspy.Reasoning | None``, not a string.
  Pass ``rationale_field_type=str`` if you want a text field you can inspect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal, Optional, Sequence

from .marketdata import ReturnPanel
from .metric import Selection
from .model import Case, Instrument, Pack

try:  # pragma: no cover - exercised only when DSPy is installed
    import dspy

    HAS_DSPY = True
except Exception:  # pragma: no cover
    dspy = None  # type: ignore[assignment]
    HAS_DSPY = False

import pydantic

Role = Literal[
    "whole_portfolio", "dominant_sleeve", "diversifier", "liquidity_reference"
]


class Pick(pydantic.BaseModel):
    """Structured output for one benchmark choice."""

    benchmark_id: str
    role: Role
    rationale: str


# ---------------------------------------------------------------------------
# prompts
# ---------------------------------------------------------------------------
NAIVE_PROMPT_MINIMAL = """
Pick the three benchmarks from the shortlist that are most similar to the holding.

Return exactly three distinct benchmark_id values from the shortlist.
"""

CURRENT_PROMPT = """
You are a benchmark research agent supporting a private-banking investment review.

Select exactly three candidate benchmarks for the holding and explain why each is
a defensible reference. You are not writing a marketing description, a
performance forecast or a customer recommendation.

Look through the trading wrapper: for marketable equities the benchmark follows
the underlying economic exposure, not the account, settlement or custody
currency, and not the listing venue. A US company held in HKD is US equity
exposure. Do not infer country exposure from the currency used to value the
holding.

Hard rules:
- Return exactly three distinct benchmarks, every id present in the shortlist.
- Do not select three near-duplicates of the same exposure without explaining
  the distinct role of each.
- State the role each benchmark plays: whole portfolio, dominant sleeve,
  diversifier or liquidity reference.
- State how asset class, geography, currency and return basis relate to the
  holding.
- State at least one material limitation or mismatch for each.
- Do not call a benchmark equivalent, accurate, verified, perfect or approved.
- Do not recommend a trade, product or customer action.
- Disclose currency, geography or duration mismatches plainly.

A broad index is a reference, not a peer: it may be a legitimate whole-portfolio
reference even when it is not the closest economic match. Prefer a benchmark in
the holding's own geography and currency as the primary reference when the
shortlist offers one.
"""


@dataclass(frozen=True)
class VariantSpec:
    key: str
    label: str
    instructions: str
    include_metadata: bool
    module: str = "cot"  # "predict" | "cot"


VARIANTS: tuple[VariantSpec, ...] = (
    VariantSpec("A", "A: naive prompt, ids only", NAIVE_PROMPT_MINIMAL, False, "predict"),
    VariantSpec("B", "B: current prompt, ids only", CURRENT_PROMPT, False, "cot"),
    VariantSpec("C", "C: current prompt + enrichment", CURRENT_PROMPT, True, "cot"),
)


# ---------------------------------------------------------------------------
# signature
# ---------------------------------------------------------------------------
def build_signature(variant: VariantSpec):
    """Construct the DSPy signature for a variant.

    The fields are identical across variants; only the instructions and the
    *contents* of ``shortlist`` differ.  That is what makes B vs C a fair test
    of context rather than prompt wording.
    """
    if not HAS_DSPY:  # pragma: no cover
        raise RuntimeError(
            "DSPy is not installed in this interpreter. "
            "Install it with `pip install dspy` and re-run."
        )

    class SelectBenchmarks(dspy.Signature):
        """placeholder - replaced by variant instructions"""

        securities: str = dspy.InputField(
            desc="the holding(s) under review, with extracted facts"
        )
        shortlist: str = dspy.InputField(
            desc="the only permitted sources for benchmark_id"
        )
        risk_level: str = dspy.InputField(desc="pre-determined risk level")
        look_through_analysis: str = dspy.OutputField(
            desc="exposure basis for equities, plus any unresolved exposure question"
        )
        selections: list[Pick] = dspy.OutputField(
            desc="exactly three distinct benchmark choices"
        )

    return SelectBenchmarks.with_instructions(variant.instructions)


def build_program(variant: VariantSpec):
    signature = build_signature(variant)
    if not HAS_DSPY:  # pragma: no cover
        raise RuntimeError("DSPy is not installed")
    return dspy.ChainOfThought(signature) if variant.module == "cot" else dspy.Predict(
        signature
    )


# ---------------------------------------------------------------------------
# rendering the pack into the prompt
# ---------------------------------------------------------------------------
def render_shortlist(
    pack: Pack,
    asset_id: str,
    include_metadata: bool,
    comovement: Optional[dict[str, float]] = None,
) -> str:
    """Render the catalogue for the prompt.

    ``include_metadata=False`` gives ids and names only - the model has to
    supply all the exposure knowledge itself.  ``True`` adds the structured
    fields plus measured co-movement, which is the enrichment hypothesis.
    """
    lines: list[str] = []
    for inst in sorted(pack, key=lambda i: i.id):
        if inst.id == asset_id:
            continue
        if not include_metadata:
            lines.append(f"{inst.id} | {inst.name}")
            continue

        bits = [
            inst.id,
            inst.name,
            f"kind={inst.kind}",
            f"asset_class={inst.asset_class}",
            f"breadth={inst.breadth}",
        ]
        if inst.sector:
            bits.append(f"sector={inst.sector}")
        if inst.industry:
            bits.append(f"industry={inst.industry}")
        bits.append(f"region={inst.region}")
        bits.append(f"ccy={inst.currency}")
        if comovement and inst.id in comovement:
            bits.append(f"resid_corr_vs_asset={comovement[inst.id]:+.2f}")
        bits.append(f'desc="{inst.description}"')
        lines.append(" :: ".join(bits))
    return "\n".join(lines)


def render_holding(inst: Instrument) -> str:
    parts = [f"{inst.id} ({inst.name})", f"asset_class={inst.asset_class}"]
    if inst.sector:
        parts.append(f"sector={inst.sector}")
    if inst.industry:
        parts.append(f"industry={inst.industry}")
    parts.append(f"region={inst.region}")
    parts.append(f"valuation_currency={inst.currency}")
    parts.append(f'description="{inst.description}"')
    return " | ".join(parts)


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
def require_dspy() -> None:
    if not HAS_DSPY:  # pragma: no cover
        raise RuntimeError(
            "DSPy is not installed in this interpreter.\n"
            "  python -m pip install dspy\n"
            "then export a model key, e.g. OPENAI_API_KEY, and re-run."
        )


class DspyRunner:
    """Runner backed by a real DSPy program.  Needs an LM and an API key."""

    def __init__(self, variant: VariantSpec, lm=None):
        require_dspy()
        self.variant = variant
        self.lm = lm
        self.name = variant.label
        self._program = None

    @property
    def program(self):
        if self._program is None:
            self._program = build_program(self.variant)
        return self._program

    def select(
        self,
        case: Case,
        pack: Pack,
        panel: Optional[ReturnPanel] = None,
    ) -> list[Selection]:
        asset = pack[case.asset_id]

        com: Optional[dict[str, float]] = None
        if self.variant.include_metadata and panel is not None:
            from .signals import comovement_scores

            raw = comovement_scores(panel, case.asset_id, [i for i in pack.ids])
            com = {k: v for k, v in raw.items() if v is not None}

        shortlist = render_shortlist(
            pack, case.asset_id, self.variant.include_metadata, com
        )

        kwargs = dict(
            securities=render_holding(asset),
            shortlist=shortlist,
            risk_level="pre-mapped upstream; do not re-map",
        )

        if self.lm is not None:
            with dspy.context(lm=self.lm):
                pred = self.program(**kwargs)
        else:
            pred = self.program(**kwargs)

        return self._to_selections(pred)

    @staticmethod
    def _to_selections(pred) -> list[Selection]:
        """Pass through exactly what the model produced.

        Deliberately no padding and no repair: a wrong count or an invented id
        is a real failure and the metric should see it, not be shielded from it.
        """
        out: list[Selection] = []
        for item in getattr(pred, "selections", []) or []:
            bench_id = getattr(item, "benchmark_id", None)
            if bench_id is None and isinstance(item, dict):
                bench_id = item.get("benchmark_id")
            if not bench_id:
                continue
            role = getattr(item, "role", None) or (
                item.get("role") if isinstance(item, dict) else None
            )
            rationale = getattr(item, "rationale", "") or ""
            out.append(
                Selection(benchmark_id=str(bench_id), role=role or "diversifier",
                          rationale=rationale)
            )
        return out


def dspy_runners(lm=None) -> list[DspyRunner]:
    """The three variants as runners, ready for ``harness.compare``."""
    return [DspyRunner(v, lm=lm) for v in VARIANTS]

