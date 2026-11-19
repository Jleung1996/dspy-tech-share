"""Integration tests for the optional DSPy layer.

Skipped automatically when DSPy is not importable.  These do not call a model -
they verify that the signatures, programs and prompt rendering are well-formed,
and that the metric accepts the shape a DSPy program actually returns.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import peerlens as pl

_VENDORED = Path(__file__).resolve().parents[1] / ".pydeps"
if _VENDORED.is_dir() and str(_VENDORED) not in sys.path:
    sys.path.insert(0, str(_VENDORED))

dspy = pytest.importorskip("dspy", reason="DSPy not installed")

from peerlens import dspy_program as dp  # noqa: E402
from peerlens import metric  # noqa: E402


def test_three_variants_defined():
    assert [v.key for v in dp.VARIANTS] == ["A", "B", "C"]
    assert dp.VARIANTS[2].include_metadata
    assert not dp.VARIANTS[1].include_metadata


def test_b_uses_the_same_prompt_as_c():
    """The whole experiment rests on B and C differing only in context."""
    assert dp.VARIANTS[1].instructions == dp.VARIANTS[2].instructions
    assert dp.VARIANTS[1].instructions != dp.VARIANTS[0].instructions


@pytest.mark.parametrize("variant", dp.VARIANTS, ids=lambda v: v.key)
def test_programs_build_with_expected_fields(variant):
    program = dp.build_program(variant)
    inner = getattr(program, "predict", program)
    signature = inner.signature
    assert set(signature.input_fields) == {"securities", "shortlist", "risk_level"}
    # ChainOfThought adds its own reasoning field on top of ours
    assert {"look_through_analysis", "selections"} <= set(signature.output_fields)


def test_enriched_shortlist_carries_metadata():
    plain = dp.render_shortlist(pl.PACK, "EQ_NVDA", False)
    rich = dp.render_shortlist(pl.PACK, "EQ_NVDA", True, {"EQ_AMD": 0.42})

    assert "industry=" not in plain
    assert "industry=Semiconductors" in rich
    assert "resid_corr_vs_asset=+0.42" in rich


def test_shortlist_excludes_the_asset_itself():
    text = dp.render_shortlist(pl.PACK, "EQ_NVDA", True)
    assert not any(line.startswith("EQ_NVDA ") for line in text.splitlines())
    assert "EQ_AMD" in text


def test_shortlist_lists_every_other_instrument():
    text = dp.render_shortlist(pl.PACK, "EQ_NVDA", False)
    ids = {line.split(" | ")[0] for line in text.splitlines()}
    assert ids == set(pl.PACK.ids) - {"EQ_NVDA"}


def test_holding_rendering_includes_exposure_basis():
    text = dp.render_holding(pl.PACK["EQ_NVDA"])
    assert "industry=Semiconductors" in text
    assert "valuation_currency=USD" in text


def test_to_selections_passes_failures_through():
    """A bad model answer must be visible to the metric, not silently fixed."""

    class FakePred:
        selections = [
            {"benchmark_id": "EQ_AMD", "role": "dominant_sleeve", "rationale": "ok"},
            {"benchmark_id": "EQ_MADE_UP", "role": "diversifier", "rationale": "x"},
        ]

    picks = dp.DspyRunner._to_selections(FakePred())
    assert [p.benchmark_id for p in picks] == ["EQ_AMD", "EQ_MADE_UP"]


def test_metric_accepts_dspy_shaped_prediction():
    class Gold:
        asset_id = "EQ_NVDA"
        pack = pl.PACK
        case = pl.CASE_BY_ASSET["EQ_NVDA"]

    class Pred:
        selections = [
            {"benchmark_id": "EQ_AMD", "role": "dominant_sleeve"},
            {"benchmark_id": "EQ_TSM", "role": "dominant_sleeve"},
            {"benchmark_id": "IDX_SPX", "role": "whole_portfolio"},
        ]

    result = metric.peer_metric(Gold(), Pred())
    # DSPy present -> Prediction(score, feedback); absent -> bare float
    score = getattr(result, "score", result)
    assert 0.5 < score <= 1.0
    assert getattr(result, "feedback", None)
