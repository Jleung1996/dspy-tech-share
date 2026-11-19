"""Tests for the decomposed equity prompt and the regression loop."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import peerlens as pl
from peerlens import regression
from peerlens.prompt_v2 import (
    MAX_RATIONALE_WORDS,
    RULE_MAP,
    BenchmarkPick,
    HoldingFacts,
    assemble_rationale,
    expected_mismatches,
    rule_summary,
    to_picks,
    validate_pick,
    validate_selection,
)

_VENDORED = Path(__file__).resolve().parents[1] / ".pydeps"
if _VENDORED.is_dir() and str(_VENDORED) not in sys.path:
    sys.path.insert(0, str(_VENDORED))

CASES_FILE = Path(__file__).resolve().parents[1] / "cases" / "regressions.yaml"

PREFIX = "Risk profile: balanced growth."


def _holding(ticker="EQ_NVDA", **kw) -> HoldingFacts:
    return HoldingFacts.from_instrument(pl.PACK[ticker], **kw)


def _pick(bench="EQ_AMD", **kw) -> BenchmarkPick:
    default = dict(
        role="dominant_sleeve",
        relationship="Same semiconductor design exposure as the holding.",
        limitation="Single-name concentration, narrower than the holding's "
                   "end-market spread.",
    )
    default.update(kw)
    return BenchmarkPick(benchmark_id=bench, **default)


# ---------------------------------------------------------------------------
# rule disposition
# ---------------------------------------------------------------------------
def test_rule_map_is_complete_and_partitioned():
    assert len(RULE_MAP) == 22
    counts = rule_summary()
    assert counts == {"schema": 6, "validator": 9, "python": 1, "instruction": 6}
    assert sum(counts.values()) == 22


def test_only_instructions_are_optimisable():
    """Guarantees must never appear in the optimisable surface."""
    for rule in RULE_MAP:
        assert rule.optimizable == (rule.mechanism == "instruction"), rule.rule


def test_majority_of_rules_are_mechanical():
    mechanical = sum(1 for r in RULE_MAP if r.guaranteed)
    assert mechanical / len(RULE_MAP) > 0.7


# ---------------------------------------------------------------------------
# prefix assembly - rule 8
# ---------------------------------------------------------------------------
def test_rationale_always_starts_with_prefix():
    text = assemble_rationale(PREFIX, _pick())
    assert text.startswith(PREFIX)


def test_prefix_concatenation_cannot_be_violated():
    """Whatever the model emits, the prefix is correct - it never sees it."""
    hostile = _pick(relationship="I will not start with the prefix.", limitation="None.")
    text = assemble_rationale(PREFIX, hostile)
    assert text.startswith(PREFIX)
    assert PREFIX in text


def test_rationale_includes_limitation_and_mismatches():
    text = assemble_rationale(
        PREFIX, _pick(mismatches=("currency",), limitation="Reports in a different currency.")
    )
    assert "Limitation:" in text
    assert "currency" in text


# ---------------------------------------------------------------------------
# mismatch disclosure - rule 13, and the look-through rule
# ---------------------------------------------------------------------------
def test_look_through_uses_exposure_not_valuation_currency():
    """A US company held in HKD has no currency mismatch against USD benchmarks."""
    held = _holding(valuation_currency="HKD", exposure_currency="USD",
                    exposure_region="United States")

    assert expected_mismatches(held, pl.PACK["IDX_SPX"]) == frozenset()

    hk = expected_mismatches(held, pl.PACK["IDX_HSI"])
    assert "currency" in hk          # HSI is HKD, exposure is USD
    assert "geography" in hk


def test_valuation_currency_alone_would_have_been_wrong():
    """Without the exposure fields, the naive reading inverts the answer."""
    naive = HoldingFacts(
        ticker="EQ_NVDA", name="NVIDIA", sector=None, industry=None,
        region="Hong Kong", valuation_currency="HKD",
    )
    # naive: HKD holding vs USD benchmark looks like a currency mismatch
    assert "currency" in expected_mismatches(naive, pl.PACK["IDX_SPX"])


def test_undisclosed_mismatch_is_rejected():
    held = _holding(valuation_currency="HKD", exposure_currency="USD")
    bad = _pick("IDX_HSI", mismatches=())
    problems = validate_pick(bad, held, pl.PACK)
    assert any("undisclosed mismatch" in p for p in problems)


def test_spurious_mismatch_is_rejected():
    held = _holding()
    bad = _pick("EQ_AMD", mismatches=("currency",))  # AMD is also USD
    problems = validate_pick(bad, held, pl.PACK)
    assert any("no basis" in p for p in problems)


# ---------------------------------------------------------------------------
# text rules
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text,fragment",
    [
        ("This benchmark is an accurate reflection.", "banned word"),
        ("Volatility was 12 percent last year.", "numeric claim"),
        ("We recommend an allocation to this index.", "advice"),
    ],
)
def test_text_rules_are_enforced(text, fragment):
    problems = validate_pick(_pick(relationship=text), _holding(), pl.PACK)
    assert any(fragment in p for p in problems)


def test_empty_limitation_is_rejected():
    problems = validate_pick(_pick(limitation=" "), _holding(), pl.PACK)
    assert any("limitation is empty" in p for p in problems)


def test_word_limit_is_enforced():
    long_text = " ".join(["exposure"] * (MAX_RATIONALE_WORDS + 5))
    problems = validate_pick(_pick(relationship=long_text), _holding(), pl.PACK)
    assert any("words" in p for p in problems)


def test_clean_pick_passes():
    assert validate_pick(_pick(), _holding(), pl.PACK) == []


# ---------------------------------------------------------------------------
# selection rules
# ---------------------------------------------------------------------------
def test_selection_requires_exactly_three():
    picks = [_pick("EQ_AMD"), _pick("EQ_TSM")]
    problems = validate_selection(picks, _holding(), pl.PACK)
    assert any("exactly 3" in p for p in problems)


def test_duplicate_ids_rejected():
    picks = [_pick("EQ_AMD"), _pick("EQ_AMD"), _pick("EQ_TSM")]
    problems = validate_selection(picks, _holding(), pl.PACK)
    assert any("duplicate" in p for p in problems)


def test_unknown_id_rejected():
    picks = [_pick("EQ_AMD"), _pick("EQ_TSM"), _pick("EQ_FAKE")]
    problems = validate_selection(picks, _holding(), pl.PACK)
    assert any("not in pack" in p for p in problems)


def test_self_selection_rejected():
    picks = [_pick("EQ_NVDA"), _pick("EQ_AMD"), _pick("EQ_TSM")]
    problems = validate_selection(picks, _holding(), pl.PACK)
    assert any("its own benchmark" in p for p in problems)


def test_three_funds_on_one_industry_rejected():
    picks = [
        _pick("IDX_SOX"), _pick("ETF_SMH"), _pick("ETF_SOXX"),
    ]
    problems = validate_selection(picks, _holding(), pl.PACK)
    assert any("near-duplicate" in p for p in problems)


def test_three_companies_on_one_industry_is_allowed():
    """Three different chip companies is what the task asks for."""
    picks = [
        _pick("EQ_AMD", role="dominant_sleeve"),
        _pick("EQ_TSM", role="diversifier"),
        _pick("EQ_AVGO", role="whole_portfolio"),
    ]
    problems = validate_selection(picks, _holding(), pl.PACK)
    assert not any("near-duplicate" in p for p in problems)


def test_single_role_rejected():
    picks = [
        _pick("EQ_AMD", role="dominant_sleeve"),
        _pick("EQ_TSM", role="dominant_sleeve"),
        _pick("EQ_AVGO", role="dominant_sleeve"),
    ]
    problems = validate_selection(picks, _holding(), pl.PACK)
    assert any("one role" in p for p in problems)


# ---------------------------------------------------------------------------
# coercion
# ---------------------------------------------------------------------------
def test_to_picks_accepts_dicts_and_objects():
    class Obj:
        benchmark_id = "EQ_TSM"
        role = "diversifier"
        relationship = "Same foundry exposure."
        limitation = "Single geography."
        mismatches: list = []

    picks = to_picks([
        {"benchmark_id": "EQ_AMD", "role": "dominant_sleeve",
         "relationship": "r", "limitation": "l"},
        Obj(),
        {"role": "no-id"},
    ])
    assert [p.benchmark_id for p in picks] == ["EQ_AMD", "EQ_TSM"]


# ---------------------------------------------------------------------------
# regression suite
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def cases():
    return regression.load_cases(CASES_FILE, pl.PACK)


def test_cases_load(cases):
    assert len(cases) == 6
    assert {c.id for c in cases} == {f"REG-000{i}" for i in range(1, 7)}
    assert all(c.severity in regression.SEVERITIES for c in cases)


def test_replay_of_reported_failures_actually_fails(cases):
    """A regression test that passes on the broken output is worthless."""
    outputs = {
        c.id: [
            BenchmarkPick(benchmark_id=i, role="diversifier",
                          relationship="x", limitation="y")
            for i in c.reported_output
            if i in pl.PACK
        ]
        for c in cases
    }
    results = regression.run_suite(cases, outputs, pl.PACK)
    assert regression.summarise(results)["failed"] == len(cases)
    assert not regression.suite_passes(results)


def test_nvda_salesforce_case_is_blocking(cases):
    case = next(c for c in cases if c.id == "REG-0001")
    picks = [
        BenchmarkPick("EQ_CRM", "diversifier", "r", "l"),
        BenchmarkPick("EQ_ADBE", "diversifier", "r", "l"),
        BenchmarkPick("IDX_NDX", "whole_portfolio", "r", "l"),
    ]
    result = regression.evaluate_case(case, picks, pl.PACK)
    assert not result.passed
    assert result.blocking


def test_good_answer_passes_the_nvda_case(cases):
    case = next(c for c in cases if c.id == "REG-0001")
    picks = [
        BenchmarkPick("EQ_AMD", "dominant_sleeve",
                      "Same fabless GPU exposure.", "Single name."),
        BenchmarkPick("EQ_TSM", "dominant_sleeve",
                      "Foundry upstream of the holding.", "Geography differs."),
        BenchmarkPick("IDX_NDX", "whole_portfolio",
                      "Broad growth reference.", "Not a peer exposure."),
    ]
    result = regression.evaluate_case(case, picks, pl.PACK)
    assert result.passed, result.reasons


def test_high_severity_blocks_but_medium_does_not(cases):
    medium = next(c for c in cases if c.severity == "medium")
    picks = [
        BenchmarkPick("CASH_SGD", "diversifier", "r", "l"),
        BenchmarkPick("IDX_SPX", "whole_portfolio", "r", "l"),
        BenchmarkPick("ETF_TLT", "diversifier", "r", "l"),
    ]
    result = regression.evaluate_case(medium, picks, pl.PACK)
    assert not result.passed
    assert not result.blocking


def test_promote_stub_is_valid_yaml(cases):
    yaml = pytest.importorskip("yaml")
    stub = regression.promote_stub(
        "EQ_KO",
        "Cash proxy offered as an equity benchmark",
        observed=["CASH_SGD", "ETF_TLT", "IDX_SPX"],
        pack=pl.PACK,
        reporter="ops-hk",
        opened="2026-11-20",
    )
    parsed = yaml.safe_load(stub)
    assert isinstance(parsed, list)
    entry = parsed[0]
    assert entry["severity"] == "high"
    assert entry["complaint"].startswith("Cash proxy")
    assert "CASH_SGD" in entry["forbidden"]
    # required_any is deliberately left empty rather than guessed
    assert entry["required_any"] == []


def test_one_industry_fund_plus_two_broad_is_not_a_duplicate():
    """IDX_SOX + ETF_XLK + IDX_SPX is one peer plus two references, not three
    funds on one exposure. Only one of the three carries an industry, and the
    original check treated that single industry as unanimity."""
    picks = [
        _pick("IDX_SOX", role="dominant_sleeve"),
        _pick("ETF_XLK", role="diversifier"),
        _pick("IDX_SPX", role="whole_portfolio"),
    ]
    problems = validate_selection(picks, _holding(), pl.PACK)
    assert not any("near-duplicate" in p for p in problems)


def test_three_same_industry_funds_still_flag():
    picks = [
        _pick("IDX_SOX", role="dominant_sleeve"),
        _pick("ETF_SMH", role="diversifier"),
        _pick("ETF_SOXX", role="whole_portfolio"),
    ]
    problems = validate_selection(picks, _holding(), pl.PACK)
    assert any("near-duplicate" in p for p in problems)
