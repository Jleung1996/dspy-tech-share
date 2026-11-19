"""Tests for the peer-labelling harness.

Run with:  python -m pytest tests -q
"""

from __future__ import annotations

import math

import pytest

import peerlens as pl
from peerlens import harness, labeling, marketdata, metric, runners, signals
from peerlens.model import BR_BROAD, BR_INDUSTRY, Case


@pytest.fixture(scope="module")
def panel():
    return marketdata.synthetic_panel(pl.PACK, n_days=500, seed=11)


# ---------------------------------------------------------------------------
# pack / ground truth integrity
# ---------------------------------------------------------------------------
def test_pack_ids_unique_and_sized():
    assert len(pl.PACK) == len({i.id for i in pl.PACK})
    assert len(pl.PACK) >= 80


def test_every_case_asset_is_in_pack():
    for case in pl.CASES:
        assert case.asset_id in pl.PACK, case.asset_id


def test_case_tiers_are_disjoint():
    for case in pl.CASES:
        tiers = [case.acceptable, case.adjacent, case.hard_negatives, case.unacceptable]
        for i in range(len(tiers)):
            for j in range(i + 1, len(tiers)):
                assert not (tiers[i] & tiers[j]), (
                    f"{case.asset_id}: tiers {i} and {j} overlap"
                )


def test_no_case_lists_itself():
    for case in pl.CASES:
        everything = case.acceptable | case.adjacent | case.hard_negatives | case.unacceptable
        assert case.asset_id not in everything


def test_broad_indices_are_adjacent_not_negatives():
    """A broad index is a legitimate reference, so it must never be penalised."""
    for case in pl.CASES:
        for inst in pl.PACK:
            if inst.breadth == BR_BROAD and inst.asset_class == pl.model.EQUITY:
                if inst.id == case.asset_id:
                    continue
                assert inst.id not in case.unacceptable, (
                    f"{case.asset_id}: broad reference {inst.id} marked unacceptable"
                )


def test_hard_negatives_share_the_asset_sector():
    """Within-sector confusions are the discriminating set; they must really
    be within-sector or the whole 'hard' claim is hollow."""
    for case in pl.CASES:
        sector = pl.PACK[case.asset_id].sector
        for bench_id in case.hard_negatives:
            assert pl.PACK[bench_id].sector == sector, (
                f"{case.asset_id}: {bench_id} is not a within-sector negative"
            )


def test_nvda_salesforce_is_a_hard_negative():
    """The user's own example: AMD/TSM yes, Salesforce no."""
    case = pl.CASE_BY_ASSET["EQ_NVDA"]
    assert "EQ_AMD" in case.acceptable
    assert "EQ_TSM" in case.acceptable
    assert "EQ_CRM" in case.hard_negatives or "EQ_CRM" in case.unacceptable


# ---------------------------------------------------------------------------
# signals
# ---------------------------------------------------------------------------
def test_taxonomy_orders_exposure_proximity():
    nvda = pl.PACK["EQ_NVDA"]
    same_industry = pl.taxonomy_score(nvda, pl.PACK["EQ_AMD"])
    same_sector = pl.taxonomy_score(nvda, pl.PACK["EQ_CRM"])
    other_sector = pl.taxonomy_score(nvda, pl.PACK["EQ_KO"])
    other_class = pl.taxonomy_score(nvda, pl.PACK["ETF_TLT"])
    assert same_industry > same_sector > other_sector
    assert other_class == 0.0


def test_asset_class_mismatch_is_fatal():
    nvda = pl.PACK["EQ_NVDA"]
    for bench_id in ("ETF_TLT", "CASH_SGD", "IDX_UST_AGG"):
        assert pl.taxonomy_score(nvda, pl.PACK[bench_id]) == 0.0


def test_comovement_strips_market_beta(panel):
    """A broad index should not look like a peer once the market is removed."""
    scores = pl.comovement_scores(panel, "EQ_NVDA", ["IDX_SPX", "ETF_SPY", "EQ_AMD"])
    assert abs(scores["IDX_SPX"]) < 0.25
    assert abs(scores["ETF_SPY"]) < 0.25
    assert scores["EQ_AMD"] > abs(scores["IDX_SPX"])


def test_comovement_ranks_same_industry_above_cross_sector(panel):
    scores = pl.comovement_scores(
        panel, "EQ_NVDA", ["EQ_AMD", "EQ_TSM", "EQ_KO", "EQ_JPM"]
    )
    assert scores["EQ_AMD"] > scores["EQ_KO"]
    assert scores["EQ_TSM"] > scores["EQ_JPM"]


def test_comovement_absent_when_panel_missing():
    scores = pl.comovement_scores(None, "EQ_NVDA", ["EQ_AMD"])
    assert scores["EQ_AMD"] is None


def test_description_scores_bounded_and_self_excluded():
    scores = pl.description_scores(pl.PACK, "EQ_NVDA", ["EQ_AMD", "EQ_KO", "EQ_NVDA"])
    assert "EQ_NVDA" not in scores
    for value in scores.values():
        assert 0.0 <= value <= 1.0
    assert scores["EQ_AMD"] > scores["EQ_KO"]


# ---------------------------------------------------------------------------
# labelling
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "scores,expected",
    [
        ({"taxonomy": 1.0, "comovement": 0.9, "description": 0.5}, labeling.ACCEPT),
        ({"taxonomy": 0.1, "comovement": 0.0, "description": 0.0}, labeling.REJECT),
        ({"taxonomy": 1.0, "comovement": 0.0, "description": 0.0}, labeling.CONFLICT),
        ({"taxonomy": 1.0, "comovement": None, "description": None}, labeling.INSUFFICIENT),
    ],
)
def test_label_pair_rules(scores, expected):
    label, _, _ = labeling.label_pair(scores)
    assert label == expected


def test_agreement_report_discriminates_description():
    """Description similarity should be the weakest of the three proxies."""
    panel = marketdata.synthetic_panel(pl.PACK, n_days=500, seed=11)
    report = labeling.agreement_report(pl.CASES[:12], pl.PACK, panel)
    assert report["description"].precision < report["taxonomy"].precision
    for a in report.values():
        assert a.support_pos > 0
        assert not math.isnan(a.f1)


def test_synthetic_panel_encodes_the_taxonomy():
    """Documented circularity: co-movement cannot corroborate taxonomy here.

    If this assertion ever starts failing, the synthetic generator changed and
    the README's caveat about the demo needs revisiting.
    """
    panel = marketdata.synthetic_panel(pl.PACK, n_days=500, seed=11)
    report = labeling.agreement_report(pl.CASES[:12], pl.PACK, panel)
    assert report["comovement"].hard_accuracy == pytest.approx(
        report["taxonomy"].hard_accuracy, abs=0.05
    )


def test_missed_peers_surfaces_asml():
    """ASML is a curated peer that no proxy detects - the review shortlist must
    contain it, because that is the whole point of that function."""
    panel = marketdata.synthetic_panel(pl.PACK, n_days=500, seed=11)
    verdicts = labeling.build_verdicts(pl.CASES, pl.PACK, panel)
    missed = labeling.missed_peers(pl.CASES, verdicts)
    pairs = {(a, b) for a, b, _ in missed}
    assert ("EQ_NVDA", "EQ_ASML") in pairs


# ---------------------------------------------------------------------------
# metric
# ---------------------------------------------------------------------------
def _sel(*ids, roles=None):
    roles = roles or ["dominant_sleeve", "diversifier", "whole_portfolio"]
    return [metric.Selection(benchmark_id=i, role=roles[k % 3]) for k, i in enumerate(ids)]


def test_three_peers_score_highly():
    case = pl.CASE_BY_ASSET["EQ_NVDA"]
    axes = metric.score_selection(
        "EQ_NVDA", _sel("EQ_AMD", "EQ_TSM", "EQ_AVGO"), pl.PACK, case
    )
    assert axes.peer_hits == 3
    assert axes.violations == 0
    assert axes.composite > 0.95


def test_salesforce_for_nvidia_is_penalised():
    case = pl.CASE_BY_ASSET["EQ_NVDA"]
    bad = metric.score_selection(
        "EQ_NVDA", _sel("EQ_CRM", "EQ_KO", "EQ_JPM"), pl.PACK, case
    )
    good = metric.score_selection(
        "EQ_NVDA", _sel("EQ_AMD", "EQ_TSM", "EQ_AVGO"), pl.PACK, case
    )
    assert bad.composite < good.composite
    assert bad.composite == 0.0


def test_wrong_count_scores_zero():
    case = pl.CASE_BY_ASSET["EQ_NVDA"]
    axes = metric.score_selection(
        "EQ_NVDA", _sel("EQ_AMD", "EQ_TSM"), pl.PACK, case
    )
    assert axes.wrong_count
    assert axes.composite == 0.0


def test_duplicate_ids_score_zero():
    case = pl.CASE_BY_ASSET["EQ_NVDA"]
    axes = metric.score_selection(
        "EQ_NVDA", _sel("EQ_AMD", "EQ_AMD", "EQ_TSM"), pl.PACK, case
    )
    assert axes.wrong_count
    assert axes.composite == 0.0


def test_unknown_id_scores_zero():
    case = pl.CASE_BY_ASSET["EQ_NVDA"]
    axes = metric.score_selection(
        "EQ_NVDA", _sel("EQ_AMD", "EQ_TSM", "EQ_MADE_UP"), pl.PACK, case
    )
    assert axes.unknown_ids == ("EQ_MADE_UP",)
    assert axes.composite == 0.0


def test_three_industry_etfs_are_flagged_redundant():
    """Three indices tracking one industry is the redundancy the rules forbid."""
    case = pl.CASE_BY_ASSET["EQ_NVDA"]
    axes = metric.score_selection(
        "EQ_NVDA", _sel("IDX_SOX", "ETF_SMH", "ETF_SOXX"), pl.PACK, case
    )
    assert axes.duplicate_exposure or axes.near_duplicate


def test_peer_plus_two_broad_indices_is_not_redundant():
    """A real model answer: one industry peer plus two broad references.

    Broad indices carry no industry, so a naive 'all industries identical' test
    sees a single-element set and wrongly calls this a duplicate.
    """
    case = pl.CASE_BY_ASSET["EQ_NVDA"]
    axes = metric.score_selection(
        "EQ_NVDA", _sel("IDX_SOX", "ETF_SPY", "ETF_VT"), pl.PACK, case
    )
    assert not axes.duplicate_exposure
    assert axes.peer_hits == 1
    assert axes.adjacent_hits == 2


def test_broad_index_earns_partial_credit_only():
    case = pl.CASE_BY_ASSET["EQ_NVDA"]
    axes = metric.score_selection(
        "EQ_NVDA", _sel("EQ_AMD", "EQ_TSM", "IDX_SPX"), pl.PACK, case
    )
    assert axes.peer_hits == 2
    assert 0.6 < axes.composite < 1.0


def test_adjacent_and_peer_weighting():
    case = pl.CASE_BY_ASSET["EQ_V"]
    axes = metric.score_selection(
        "EQ_V", _sel("EQ_MA", "ETF_XLF", "IDX_SPX"), pl.PACK, case
    )
    assert axes.peer_hits == 1
    assert axes.adjacent_hits == 2
    assert axes.violations == 0


# ---------------------------------------------------------------------------
# runners / harness
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("runner", runners.SCRIPTED_RUNNERS, ids=lambda r: r.name[:18])
def test_runners_return_three_valid_distinct_ids(runner):
    for case in pl.CASES:
        picks = runner.select(case, pl.PACK)
        ids = [s.benchmark_id for s in picks]
        assert len(ids) == 3, f"{case.asset_id}: {ids}"
        assert len(set(ids)) == 3, f"{case.asset_id}: duplicates {ids}"
        assert case.asset_id not in ids, f"{case.asset_id}: selected itself"
        for i in ids:
            assert i in pl.PACK


def test_harness_orders_runners_by_context_quality():
    panel = marketdata.synthetic_panel(pl.PACK, n_days=500, seed=11)
    results = harness.compare(runners.SCRIPTED_RUNNERS, pl.CASES, pl.PACK, panel)
    by_name = {r.runner: r.aggregate.composite for r in results}
    enriched = by_name["C: industry-aware + enriched pack"]
    sector_only = by_name["B: sector-only"]
    naive = by_name["A: naive (description only)"]
    assert enriched > sector_only
    assert enriched > naive


def test_enrichment_without_comovement_scores_slightly_lower():
    panel = marketdata.synthetic_panel(pl.PACK, n_days=500, seed=11)
    results = harness.compare(runners.SCRIPTED_RUNNERS, pl.CASES, pl.PACK, panel)
    by_name = {r.runner: r.aggregate.composite for r in results}
    assert by_name["C: industry-aware + enriched pack"] >= by_name[
        "C': industry-aware, no co-movement"
    ]


def test_render_comparison_is_markdown():
    panel = marketdata.synthetic_panel(pl.PACK, n_days=200, seed=3)
    results = harness.compare(runners.SCRIPTED_RUNNERS[:2], pl.CASES[:4], pl.PACK, panel)
    text = harness.render_comparison(results)
    assert text.startswith("|")
    assert text.count("|") > 10
