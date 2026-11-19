"""peerlens - a peer-labelling and prompt-comparison harness.

The package answers three questions in order of increasing difficulty:

1. *Can I even tell whether a benchmark pick is sensible?*
   -> ``peerlens.labeling`` triangulates three independent signals and queues
      the disagreements for human review.

2. *Which of my similarity notions actually predicts a real peer?*
   -> ``peerlens.labeling.agreement_report`` scores each signal against curated
      truth, so you learn which proxy is load-bearing and which is noise.

3. *Does a better prompt or better context move the number?*
   -> ``peerlens.harness`` runs every runner over the test bed and prints the
      comparison table.

DSPy is an optional dependency.  Everything above works without it; only
``peerlens.dspy_program`` needs it, and it imports lazily.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .marketdata import (
    MARKET_PROXY,
    ReturnPanel,
    load_returns_csv,
    percentile_returns,
    synthetic_panel,
)
from .metric import (
    ROLES,
    Aggregate,
    AxisScores,
    Selection,
    aggregate,
    peer_metric,
    score_selection,
)
from .model import Case, Instrument, Pack
from .pack import CASE_BY_ASSET, CASES, CONFLICT_NOTES, PACK
from .signals import (
    DEFAULT_CONFIG,
    SIGNAL_NAMES,
    SignalConfig,
    comovement_scores,
    description_scores,
    taxonomy_score,
    taxonomy_scores,
    votes,
)

__all__ = [
    "Aggregate",
    "AxisScores",
    "CASE_BY_ASSET",
    "CASES",
    "CONFLICT_NOTES",
    "Case",
    "DEFAULT_CONFIG",
    "Instrument",
    "MARKET_PROXY",
    "PACK",
    "ROLES",
    "ReturnPanel",
    "SIGNAL_NAMES",
    "Selection",
    "SignalConfig",
    "aggregate",
    "comovement_scores",
    "description_scores",
    "load_returns_csv",
    "peer_metric",
    "percentile_returns",
    "score_selection",
    "synthetic_panel",
    "taxonomy_score",
    "taxonomy_scores",
    "votes",
]
