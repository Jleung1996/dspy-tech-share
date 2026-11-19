"""Turn an end-user complaint into a permanent test case.

This is the mechanism you described: a client reports a bad answer, and that
answer becomes something the system must never produce again. The format is
deliberately YAML-and-no-code so operations can add a case without touching
Python.

Three properties make this work as a *ratchet* rather than a wish list:

1. Cases are additive. The suite only grows, so quality cannot silently regress
   between releases.
2. Each case carries a **severity**, and ``high`` blocks a build.
3. Each case records the output that was actually reported, so the case is
   reproducible before it is fixed. A test you cannot reproduce is folklore.

Case file format (``cases/regressions.yaml``)::

    - id: REG-0001
      opened: 2026-11-14
      reporter: ops-hk
      severity: high          # high | medium | low
      complaint: "..."        # the human description
      holding:
        ticker: EQ_NVDA
        valuation_currency: HKD
        exposure_currency: USD
      forbidden: [EQ_CRM, ETF_IGV]        # must never appear
      required_any: [EQ_AMD, IDX_SOX]     # at least min_peers of these
      min_peers: 2
      reported_output: [EQ_CRM, EQ_ADBE, IDX_NDX]

``reported_output`` is optional but encouraged: with it the suite can show the
case *failing today*, which is the proof that the fix is real.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from .model import Instrument, Pack
from .prompt_v2 import (
    HoldingFacts,
    BenchmarkPick,
    to_picks,
    validate_selection,
)

SEVERITIES = ("high", "medium", "low")


@dataclass(frozen=True)
class RegressionCase:
    id: str
    complaint: str
    holding: HoldingFacts
    forbidden: frozenset[str] = frozenset()
    required_any: frozenset[str] = frozenset()
    min_peers: int = 1
    severity: str = "medium"
    reporter: str = ""
    opened: str = ""
    reported_output: tuple[str, ...] = ()
    prefix: str = ""

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise ValueError(f"{self.id}: severity must be one of {SEVERITIES}")


@dataclass(frozen=True)
class CaseResult:
    case: RegressionCase
    passed: bool
    reasons: tuple[str, ...]
    picks: tuple[str, ...]
    validator_problems: tuple[str, ...] = ()

    @property
    def blocking(self) -> bool:
        return not self.passed and self.case.severity == "high"


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------
def _holding_from_dict(raw: Mapping, pack: Pack) -> HoldingFacts:
    ticker = str(raw["ticker"])
    inst: Optional[Instrument] = pack.get(ticker)

    if inst is None and not raw.get("sector"):
        raise ValueError(
            f"holding {ticker!r} is not in the pack, so sector/industry must be "
            "supplied explicitly in the case file"
        )

    return HoldingFacts(
        ticker=ticker,
        name=str(raw.get("name") or (inst.name if inst else ticker)),
        sector=raw.get("sector") or (inst.sector if inst else None),
        industry=raw.get("industry") or (inst.industry if inst else None),
        region=str(raw.get("region") or (inst.region if inst else "?")),
        valuation_currency=str(
            raw.get("valuation_currency") or (inst.currency if inst else "?")
        ),
        exposure_currency=raw.get("exposure_currency"),
        exposure_region=raw.get("exposure_region"),
        exposure_basis=raw.get("exposure_basis"),
        unresolved=raw.get("unresolved"),
    )


def case_from_dict(raw: Mapping, pack: Pack) -> RegressionCase:
    return RegressionCase(
        id=str(raw["id"]),
        complaint=str(raw.get("complaint", "")),
        holding=_holding_from_dict(raw["holding"], pack),
        forbidden=frozenset(raw.get("forbidden", []) or []),
        required_any=frozenset(raw.get("required_any", []) or []),
        min_peers=int(raw.get("min_peers", 1)),
        severity=str(raw.get("severity", "medium")),
        reporter=str(raw.get("reporter", "")),
        opened=str(raw.get("opened", "")),
        reported_output=tuple(raw.get("reported_output", []) or []),
        prefix=str(raw.get("prefix", "")),
    )


def load_cases(path: str | Path, pack: Pack) -> list[RegressionCase]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "PyYAML is required for YAML case files; use JSON instead, or "
                "install with `pip install pyyaml`"
            ) from exc
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    else:
        raw = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(raw, Mapping):
        raw = raw.get("cases", [])
    return [case_from_dict(item, pack) for item in raw]


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------
def evaluate_case(
    case: RegressionCase,
    picks: Sequence[BenchmarkPick],
    pack: Pack,
) -> CaseResult:
    ids = tuple(p.benchmark_id for p in picks)
    reasons: list[str] = []

    banned = [i for i in ids if i in case.forbidden]
    if banned:
        reasons.append(f"returned forbidden benchmark(s): {sorted(banned)}")

    hits = len(set(ids) & case.required_any)
    if hits < case.min_peers:
        reasons.append(
            f"only {hits} acceptable peer(s), need {case.min_peers} "
            f"from {sorted(case.required_any)}"
        )

    validator = validate_selection(picks, case.holding, pack, case.prefix)

    return CaseResult(
        case=case,
        passed=not reasons,
        reasons=tuple(reasons),
        picks=ids,
        validator_problems=tuple(validator),
    )


def run_suite(
    cases: Sequence[RegressionCase],
    outputs: Mapping[str, Sequence[BenchmarkPick]],
    pack: Pack,
) -> list[CaseResult]:
    """Evaluate every case against a mapping of case-id -> picks."""
    results: list[CaseResult] = []
    for case in cases:
        picks = outputs.get(case.id, ())
        results.append(evaluate_case(case, list(picks), pack))
    return results


def suite_passes(results: Sequence[CaseResult]) -> bool:
    """A build is blocked only by high-severity failures."""
    return not any(r.blocking for r in results)


def summarise(results: Sequence[CaseResult]) -> dict[str, int]:
    out = {
        "total": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "blocking": sum(1 for r in results if r.blocking),
    }
    for severity in SEVERITIES:
        out[f"failed_{severity}"] = sum(
            1 for r in results if not r.passed and r.case.severity == severity
        )
    return out


# ---------------------------------------------------------------------------
# promotion
# ---------------------------------------------------------------------------
def promote_stub(
    ticker: str,
    complaint: str,
    observed: Sequence[str],
    pack: Pack,
    forbidden: Optional[Sequence[str]] = None,
    required_any: Optional[Sequence[str]] = None,
    severity: str = "high",
    reporter: str = "",
    opened: str = "",
) -> str:
    """Emit a YAML stub for a newly reported failure.

    Deliberately leaves ``required_any`` blank when it cannot be inferred: a
    guessed expectation is worse than none, because it bakes in the guess.
    """
    inst = pack.get(ticker)
    held = {
        "ticker": ticker,
        **({"name": inst.name} if inst else {}),
        **({"sector": inst.sector} if inst and inst.sector else {}),
        **({"industry": inst.industry} if inst and inst.industry else {}),
        **({"region": inst.region} if inst else {}),
        **({"valuation_currency": inst.currency} if inst else {"valuation_currency": "?"}),
    }
    forbidden = list(forbidden or [i for i in observed if i not in (required_any or [])])

    lines = [
        f"- id: REG-{_next_stub_number():04d}",
        f"  opened: {opened or '<YYYY-MM-DD>'}",
        f"  reporter: {reporter or '<team>'}",
        f"  severity: {severity}",
        f"  complaint: {json.dumps(complaint)}",
        "  holding:",
    ]
    for key, value in held.items():
        lines.append(f"    {key}: {value}")
    lines.append(f"  forbidden: {json.dumps(sorted(set(forbidden)))}")
    lines.append(f"  required_any: {json.dumps(sorted(set(required_any or [])))}")
    lines.append("  min_peers: 2")
    lines.append(f"  reported_output: {json.dumps(sorted(set(observed)))}")
    return "\n".join(lines) + "\n"


_COUNTER = {"n": 1}


def _next_stub_number() -> int:
    return _COUNTER["n"]


def render_results(results: Sequence[CaseResult]) -> str:
    lines = [
        "| case | severity | result | picks | notes |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        mark = "PASS" if r.passed else ("**FAIL**" if r.blocking else "fail")
        notes = "; ".join(r.reasons) or "ok"
        if r.validator_problems:
            notes += f" [validator: {'; '.join(r.validator_problems[:2])}]"
        lines.append(
            f"| {r.case.id} | {r.case.severity} | {mark} | "
            f"{', '.join(r.picks) or '-'} | {notes} |"
        )
    return "\n".join(lines) + "\n"
