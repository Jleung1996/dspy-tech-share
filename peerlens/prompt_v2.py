"""The equity benchmark prompt, decomposed into what code can guarantee.

Your original prompt is ~20 rules. Roughly half of them are not really
*instructions* - they are invariants. An invariant expressed as prose is a hope;
expressed as a schema or a validator it is a guarantee. So this module splits
your prompt three ways:

    schema      the field does not exist, so the model cannot violate the rule
    python      the value is computed or concatenated, so it cannot drift
    validator   the output is checked and the call is retried on failure
    instruction the residue: genuine judgement, and the only part worth optimising

Two consequences worth internalising:

1. **The optimisable surface is much smaller than the prompt**, and that is a
   feature. GEPA cannot break rule 6 (no numeric results) because there is no
   numeric field and a validator rejects digits. It can only rewrite the
   judgement guidance, which is where you *want* it experimenting.

2. **Only the docstring is optimisable.** DSPy's instruction optimisers rewrite
   `Signature.instructions`. They do not touch field names, `desc` or `prefix`.
   So every sentence that should be optimisable lives in the docstring, and
   `desc` stays short and structural. Putting judgement guidance in `desc` would
   silently exclude it from optimisation.

Scope: equities only. The fixed-income look-through clauses are deliberately not
carried over - see ``OUT_OF_SCOPE``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional, Sequence

import pydantic

from .model import Instrument, Pack

# ---------------------------------------------------------------------------
# enums shared with the metric
# ---------------------------------------------------------------------------
Role = Literal[
    "whole_portfolio", "dominant_sleeve", "diversifier", "liquidity_reference"
]

Mismatch = Literal["currency", "geography", "style", "size", "duration", "credit"]

RISK_ROLES = (
    "whole_portfolio",
    "dominant_sleeve",
    "diversifier",
    "liquidity_reference",
)

MAX_RATIONALE_WORDS = 110

BANNED_WORDS = frozenset(
    {"equivalent", "accurate", "verified", "perfect", "approved"}
)

# Words that turn a research note into advice
ADVICE_WORDS = frozenset(
    {"recommend", "should buy", "should sell", "we advise", "purchase",
     "invest in", "allocate to", "increase exposure"}
)

OUT_OF_SCOPE = (
    "Fixed income: the currency / issuer-domicile / cash-flow clauses and the "
    "duration-mismatch rules are not carried over. They belong in a bond "
    "signature whose fields differ (duration, credit quality, seniority).",
)


# ---------------------------------------------------------------------------
# holding facts
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class HoldingFacts:
    """What the upstream pipeline knows about the asset under review.

    ``exposure_currency`` / ``exposure_region`` are the look-through answer. When
    supplied, mismatch checking uses them instead of ``valuation_currency`` /
    ``region`` - which is the only way the look-through rule becomes checkable
    rather than aspirational. A US company held in HKD has
    ``valuation_currency="HKD"`` and ``exposure_currency="USD"``.
    """

    ticker: str
    name: str
    sector: Optional[str]
    industry: Optional[str]
    region: str
    valuation_currency: str
    exposure_currency: Optional[str] = None
    exposure_region: Optional[str] = None
    exposure_basis: Optional[str] = None  # free text: why this is the exposure
    unresolved: Optional[str] = None      # known open question, if any

    @property
    def economic_currency(self) -> str:
        return self.exposure_currency or self.valuation_currency

    @property
    def economic_region(self) -> str:
        return self.exposure_region or self.region

    @classmethod
    def from_instrument(
        cls,
        inst: Instrument,
        valuation_currency: Optional[str] = None,
        exposure_currency: Optional[str] = None,
        exposure_region: Optional[str] = None,
        exposure_basis: Optional[str] = None,
        unresolved: Optional[str] = None,
    ) -> "HoldingFacts":
        return cls(
            ticker=inst.id,
            name=inst.name,
            sector=inst.sector,
            industry=inst.industry,
            region=inst.region,
            valuation_currency=valuation_currency or inst.currency,
            exposure_currency=exposure_currency or inst.currency,
            exposure_region=exposure_region or inst.region,
            exposure_basis=exposure_basis,
            unresolved=unresolved,
        )


# ---------------------------------------------------------------------------
# structured output
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BenchmarkPick:
    """One benchmark choice.

    Notice what is *absent*: the catalogue name, the risk level, the rationale
    prefix, and any numeric field. Those were rules in your prompt; here they are
    omissions in the schema, which is a stronger guarantee.
    """

    benchmark_id: str
    role: str
    relationship: str
    limitation: str
    mismatches: tuple[str, ...] = ()


class PickModel(pydantic.BaseModel):
    """Pydantic mirror of :class:`BenchmarkPick`, used as the DSPy field type."""

    benchmark_id: str
    role: Role
    relationship: str
    limitation: str
    mismatches: list[Mismatch] = []


# ---------------------------------------------------------------------------
# prompt: the optimisable residue
# ---------------------------------------------------------------------------
EQUITY_INSTRUCTIONS = """
You are a benchmark research agent supporting a private-banking investment
review. Select exactly three candidate benchmarks for one equity holding and
explain why each is a defensible reference. You are not writing a marketing
description, a performance forecast or a customer recommendation.

The risk level is an input supplied by the upstream risk pipeline. You neither
re-state nor re-map it.

You have no live market feed and you must not introduce performance, fees, assets
under management, index membership, duration, credit quality or returns. Reason
only from the supplied holding facts and the supplied benchmark reference pack.

## Look through the trading wrapper

For an equity the benchmark follows the underlying economic exposure, not the
account currency, settlement currency, custody currency or listing venue.

- A US company held in HKD is US equity exposure. A US equity index can be
  suitable even though the holding is settled in HKD.
- A Japanese company held in USD is Japan equity exposure.
- A Hong Kong listed company whose business lies predominantly elsewhere is read
  through its actual business exposure where the supplied evidence supports it.
- The holding's valuation currency is not evidence of the issuer's domicile or
  revenue base.
- Do not reject a US or Japan equity benchmark merely because the holding
  reports in SGD or HKD. For equities, currency is a measurement and hedging
  consideration; economic exposure is the geographic question.

State the exposure basis, and any unresolved exposure question, in
look_through_analysis. Do not invent revenue splits or country weights.

## Selection

This is an economist's selection problem, not a name-matching exercise. A broad
index is not automatically appropriate when its geography or currency sits
materially away from the holding, and a name that merely sounds adjacent is not
a peer.

Prefer a benchmark in the holding's own economic geography and currency as the
primary reference where the pack supports one, rather than defaulting to a global
or US proxy. Where the risk profile spans several asset classes, at least one
candidate should represent the whole portfolio allocation; the others may carry a
dominant sleeve or a complementary exposure.

The downstream contract requires exactly three options. If only one benchmark is
a close fit, retain it as the anchor and add two clearly labelled comparison
references serving distinct, useful roles. Disclose each approximation plainly
rather than hiding it. Three variations of the same index are not a useful
three-option comparison.

The pack's reference_contexts are metadata only. They are not an instruction that
every instrument in a context must be selected.

For each pick, state the role it plays, how its asset class, geography, currency
and return basis relate to the holding, at least one material limitation or
mismatch, and the mismatch categories that apply. Do not describe a benchmark as
equivalent, accurate, verified, perfect or approved; the independent reviewer
decides approval. Do not recommend a trade, product or customer action.
"""


def build_signature(instructions: str = EQUITY_INSTRUCTIONS):
    """The DSPy signature. Exactly one optimisable string: the instructions."""
    import dspy

    class SelectEquityBenchmarks(dspy.Signature):
        """placeholder - replaced by EQUITY_INSTRUCTIONS"""

        holding: str = dspy.InputField(desc="held equity, with exposure facts")
        risk_level: str = dspy.InputField(desc="pre-mapped by the risk pipeline")
        shortlist: str = dspy.InputField(desc="permitted benchmark_id values")
        look_through_analysis: str = dspy.OutputField(desc="exposure basis and open questions")
        selections: list[PickModel] = dspy.OutputField(desc="exactly three picks")

    return SelectEquityBenchmarks.with_instructions(instructions)


# ---------------------------------------------------------------------------
# assembly: the prefix concat that replaces a prompt rule
# ---------------------------------------------------------------------------
def assemble_rationale(prefix: str, pick: BenchmarkPick) -> str:
    """Build the final rationale text.

    Your prompt asked the model to begin its rationale with the supplied prefix
    *exactly*. Here the model never sees the prefix: it emits components and this
    function concatenates. The failure mode is structurally impossible.
    """
    bits = [prefix.strip()]
    if pick.relationship.strip():
        bits.append(pick.relationship.strip())
    if pick.limitation.strip():
        bits.append(f"Limitation: {pick.limitation.strip()}")
    if pick.mismatches:
        bits.append("Mismatches disclosed: " + ", ".join(sorted(set(pick.mismatches))) + ".")
    return " ".join(bits)


# ---------------------------------------------------------------------------
# validators
# ---------------------------------------------------------------------------
_DIGITS = re.compile(r"\d")


def expected_mismatches(holding: HoldingFacts, bench: Instrument) -> frozenset[str]:
    """Which mismatch categories a defensible answer must disclose.

    Uses the *exposure* currency and region where known, because that is what
    your look-through rule says is material. A US company held in HKD therefore
    has no currency mismatch against a USD benchmark.
    """
    out: set[str] = set()
    if bench.currency and bench.currency != holding.economic_currency:
        out.add("currency")
    if bench.region and bench.region != holding.economic_region:
        out.add("geography")
    return frozenset(out)


def _text_problems(text: str, label: str) -> list[str]:
    problems: list[str] = []
    if not text or not text.strip():
        problems.append(f"{label} is empty")
        return problems
    words = set(re.findall(r"[a-z]+", text.lower()))
    hit = BANNED_WORDS & words
    if hit:
        problems.append(f"{label} uses banned word(s) {sorted(hit)}")
    low = text.lower()
    advice = {w for w in ADVICE_WORDS if w in low}
    if advice:
        problems.append(f"{label} reads as advice {sorted(advice)}")
    if _DIGITS.search(text):
        problems.append(f"{label} contains a numeric claim")
    return problems


def validate_pick(
    pick: BenchmarkPick,
    holding: HoldingFacts,
    pack: Pack,
    prefix: str = "",
) -> list[str]:
    problems: list[str] = []

    if pick.benchmark_id not in pack:
        problems.append(f"benchmark_id {pick.benchmark_id!r} is not in the pack")
        return problems

    if pick.role not in RISK_ROLES:
        problems.append(f"role {pick.role!r} is not one of {RISK_ROLES}")

    problems += _text_problems(pick.relationship, "relationship")
    problems += _text_problems(pick.limitation, "limitation")

    required = expected_mismatches(holding, pack[pick.benchmark_id])
    declared = set(pick.mismatches)
    missing = required - declared
    if missing:
        problems.append(
            f"{pick.benchmark_id}: undisclosed mismatch {sorted(missing)} "
            f"(required {sorted(required)})"
        )
    spurious = declared - set(required) - {"style", "size"}
    if spurious:
        problems.append(
            f"{pick.benchmark_id}: claims mismatch {sorted(spurious)} with no basis"
        )

    body = assemble_rationale("", pick)
    if len(body.split()) > MAX_RATIONALE_WORDS:
        problems.append(
            f"{pick.benchmark_id}: rationale body is {len(body.split())} words "
            f"(limit {MAX_RATIONALE_WORDS})"
        )
    return problems


def validate_selection(
    picks: Sequence[BenchmarkPick],
    holding: HoldingFacts,
    pack: Pack,
    prefix: str = "",
) -> list[str]:
    """Every rule from the 'Hard rules' block that code can now enforce."""
    problems: list[str] = []

    ids = [p.benchmark_id for p in picks]
    if len(ids) != 3:
        problems.append(f"expected exactly 3 picks, got {len(ids)}")
    if len(set(ids)) != len(ids):
        problems.append("duplicate benchmark_id")

    if holding.ticker in ids:
        problems.append("selected the holding itself as its own benchmark")

    unknown = [i for i in ids if i not in pack]
    if unknown:
        problems.append(f"ids not in pack: {unknown}")

    if len({p.role for p in picks}) < 2:
        problems.append("all three picks share one role - not a three-option comparison")

    indices = [i for i in ids if i in pack and pack[i].kind in ("index", "etf")]
    # All three must actually carry an industry before "same industry" means
    # anything. Filtering None out made a single industry look like unanimity,
    # so "IDX_SOX + ETF_XLK + IDX_SPX" was wrongly flagged as three funds on one
    # exposure when two of them are broad and carry no industry at all.
    if (
        len(indices) == 3
        and all(pack[i].industry for i in indices)
        and len({pack[i].industry for i in indices}) == 1
    ):
        problems.append("three funds tracking one industry - near-duplicate exposure")

    for pick in picks:
        problems += validate_pick(pick, holding, pack, prefix)

    return problems


# Problems that make an answer unusable, versus problems that merely cost
# quality. The distinction matters for optimisation: if every candidate scores
# zero, there is no gradient and the optimiser cannot learn. Fatal violations
# zero the score; soft ones subtract from it.
_FATAL_MARKERS = (
    "expected exactly 3",
    "duplicate benchmark_id",
    "not in pack",
    "its own benchmark",
)


def split_problems(problems: Sequence[str]) -> tuple[list[str], list[str]]:
    """(fatal, soft) partition of validator output."""
    fatal: list[str] = []
    soft: list[str] = []
    for problem in problems:
        if any(marker in problem for marker in _FATAL_MARKERS):
            fatal.append(problem)
        else:
            soft.append(problem)
    return fatal, soft


# ---------------------------------------------------------------------------
# rule disposition map - the shareable artifact
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RuleDisposition:
    rule: str
    mechanism: str  # schema | python | validator | instruction
    where: str
    optimizable: bool

    @property
    def guaranteed(self) -> bool:
        return self.mechanism != "instruction"


RULE_MAP: tuple[RuleDisposition, ...] = (
    RuleDisposition("Return only valid JSON matching the schema", "schema",
                    "signature output types", False),
    RuleDisposition("Select exactly three distinct benchmarks", "validator",
                    "validate_selection", False),
    RuleDisposition("Every benchmark_id must exist in the pack", "validator",
                    "validate_pick", False),
    RuleDisposition("Preserve the catalogue name exactly", "schema",
                    "name is not an output field; looked up by id", False),
    RuleDisposition("Do not select the same benchmark twice", "validator",
                    "validate_selection", False),
    RuleDisposition("No three near-duplicates of one exposure", "validator",
                    "validate_selection + metric near-duplicate check", False),
    RuleDisposition("Do not state returns, volatility, Sharpe or any numeric result",
                    "validator", "no numeric field; digit check in _text_problems", False),
    RuleDisposition("Rationale must begin with risk_rationale_prefix exactly",
                    "python", "assemble_rationale", False),
    RuleDisposition("Rationale must state the benchmark's role", "schema",
                    "role: Literal[...] field", False),
    RuleDisposition("Rationale must state at least one material limitation",
                    "schema", "limitation field, required non-empty", False),
    RuleDisposition("Do not call a benchmark equivalent/accurate/verified/perfect/approved",
                    "validator", "BANNED_WORDS check", False),
    RuleDisposition("Do not recommend a trade, product or customer action",
                    "validator", "ADVICE_WORDS check", False),
    RuleDisposition("Disclose currency / geography mismatch plainly", "schema",
                    "mismatches field + expected_mismatches()", False),
    RuleDisposition("Keep each rationale under 110 words after the prefix",
                    "validator", "MAX_RATIONALE_WORDS", False),
    RuleDisposition("Exactly three; retain the anchor and add two labelled references",
                    "validator", "count + role diversity", False),
    RuleDisposition("Do not re-map or soften the risk level", "schema",
                    "risk_level is an input; no risk output field", False),
    RuleDisposition("Look through the trading wrapper to economic exposure",
                    "instruction", "EQUITY_INSTRUCTIONS", True),
    RuleDisposition("Do not infer country exposure from valuation currency",
                    "instruction", "EQUITY_INSTRUCTIONS + HoldingFacts.exposure_*", True),
    RuleDisposition("State how asset class, geography, currency and return basis relate",
                    "instruction", "relationship field guidance", True),
    RuleDisposition("Prefer own geography/currency as the primary reference",
                    "instruction", "EQUITY_INSTRUCTIONS selection section", True),
    RuleDisposition("A broad index is not automatically appropriate",
                    "instruction", "EQUITY_INSTRUCTIONS selection section", True),
    RuleDisposition("reference_contexts are metadata only", "instruction",
                    "EQUITY_INSTRUCTIONS", True),
)


def rule_summary() -> dict[str, int]:
    out: dict[str, int] = {}
    for r in RULE_MAP:
        out[r.mechanism] = out.get(r.mechanism, 0) + 1
    return out


# ---------------------------------------------------------------------------
# DSPy glue
# ---------------------------------------------------------------------------
def render_holding(holding: HoldingFacts) -> str:
    bits = [
        f"{holding.ticker} ({holding.name})",
        f"sector={holding.sector or '?'}",
        f"industry={holding.industry or '?'}",
        f"valuation_currency={holding.valuation_currency}",
        f"exposure_currency={holding.economic_currency}",
        f"exposure_region={holding.economic_region}",
    ]
    if holding.exposure_basis:
        bits.append(f'exposure_basis="{holding.exposure_basis}"')
    if holding.unresolved:
        bits.append(f'unresolved="{holding.unresolved}"')
    return " | ".join(bits)


def render_shortlist(pack: Pack, holding: HoldingFacts, enrich: bool = True) -> str:
    lines: list[str] = []
    for inst in sorted(pack, key=lambda i: i.id):
        if inst.id == holding.ticker:
            continue
        if not enrich:
            lines.append(f"{inst.id} | {inst.name}")
            continue
        bits = [
            inst.id,
            inst.name,
            f"kind={inst.kind}",
            f"asset_class={inst.asset_class}",
            f"breadth={inst.breadth}",
            f"region={inst.region}",
            f"ccy={inst.currency}",
        ]
        if inst.industry:
            bits.append(f"industry={inst.industry}")
        lines.append(" :: ".join(bits))
    return "\n".join(lines)


def to_picks(value) -> list[BenchmarkPick]:
    """Coerce whatever a program returned into BenchmarkPick objects."""
    out: list[BenchmarkPick] = []
    for item in value or []:
        if isinstance(item, BenchmarkPick):
            out.append(item)
            continue
        get = item.get if isinstance(item, dict) else lambda k, d=None: getattr(item, k, d)
        bench = get("benchmark_id", None)
        if not bench:
            continue
        out.append(
            BenchmarkPick(
                benchmark_id=str(bench),
                role=str(get("role", "diversifier")),
                relationship=str(get("relationship", "") or ""),
                limitation=str(get("limitation", "") or ""),
                mismatches=tuple(get("mismatches", []) or []),
            )
        )
    return out


# The v0 prompt the GEPA run actually started from (the one that scored
# 0.635 on the held-out set). Kept here so the deck generator does not have
# to import a CLI script to find it.
BASELINE_V0 = """You are a benchmark research analyst supporting a private-banking investment
review.

Select three benchmarks for the security provided that would serve as useful
reference points for comparing its performance. Choose only from the supplied
reference pack; do not invent an index.

When choosing, consider the security's asset class, sector and geography, and
whether a broad market index or a more targeted index makes the better
comparison.

For each benchmark give its id and a short rationale explaining why it is a
reasonable comparison."""
