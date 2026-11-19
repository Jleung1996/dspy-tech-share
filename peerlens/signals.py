"""Three independent signals for 'is this benchmark an economic peer?'.

The point of having three is not redundancy, it is *disagreement*.  A pair that
all three signals accept is safe to label automatically.  A pair they split on
is exactly the case a human should look at, and it is also the case that will
break an optimiser trained on a single-signal proxy.

1. ``taxonomy``      - structured sector/industry match.  Cheap, deterministic,
                       blind to supply-chain coupling and to blended businesses.
2. ``comovement``    - correlation of **market-orthogonalised** residuals.
                       Using raw correlation would reward every asset that is
                       simply long the market, so broad indices would look like
                       peers of everything.  Removing the market factor first
                       is what makes this measure *beyond-beta* similarity.
3. ``description``   - TF-IDF cosine over business summaries and tags.  A
                       stand-in for embedding 10-K Item 1 text.

Each returns a score in roughly [0, 1] (comovement can go negative) and each is
scored against its own threshold, because they are not on a common scale.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

import numpy as np

from .marketdata import MARKET_PROXY, ReturnPanel
from .model import BR_BROAD, BR_INDUSTRY, BR_SECTOR, Instrument, Pack


@dataclass(frozen=True)
class SignalConfig:
    """Per-signal vote thresholds.  Tune these against curated data, not vibes."""

    taxonomy_threshold: float = 0.70
    comovement_threshold: float = 0.45
    text_threshold: float = 0.10

    def threshold(self, name: str) -> float:
        return {
            "taxonomy": self.taxonomy_threshold,
            "comovement": self.comovement_threshold,
            "description": self.text_threshold,
        }[name]


DEFAULT_CONFIG = SignalConfig()

SIGNAL_NAMES = ("taxonomy", "comovement", "description")


# ---------------------------------------------------------------------------
# 1. taxonomy
# ---------------------------------------------------------------------------
def taxonomy_score(asset: Instrument, bench: Instrument) -> float:
    """Structured exposure match.

    An asset class mismatch is fatal: a Treasury index is never a peer of a
    single-name equity, however broad the equity benchmark habit is.
    """
    if asset.asset_class != bench.asset_class:
        return 0.0

    if bench.breadth == BR_INDUSTRY and bench.industry and bench.industry == asset.industry:
        return 1.0
    if bench.breadth == BR_SECTOR and bench.sector and bench.sector == asset.sector:
        return 0.45
    if bench.breadth == BR_BROAD:
        return 0.20
    # industry mismatch even within the same sector
    if bench.sector and bench.sector == asset.sector:
        return 0.30
    return 0.05


def taxonomy_scores(pack: Pack, asset_id: str, candidates: Iterable[str]) -> dict[str, float]:
    asset = pack[asset_id]
    return {c: taxonomy_score(asset, pack[c]) for c in candidates if c != asset_id}


# ---------------------------------------------------------------------------
# 2. co-movement (market-orthogonalised)
# ---------------------------------------------------------------------------
def _residual(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """OLS residual of y on [1, x]."""
    design = np.column_stack([np.ones_like(x), x])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    return y - design @ beta


def comovement_scores(
    panel: Optional[ReturnPanel],
    asset_id: str,
    candidates: Iterable[str],
    market: str = MARKET_PROXY,
) -> dict[str, Optional[float]]:
    """Correlation of residuals after stripping the market factor.

    Returns ``None`` for any pair the panel cannot cover, so downstream code can
    tell 'no data' apart from 'measured and low'.
    """
    candidates = [c for c in candidates if c != asset_id]
    if panel is None or not panel.has(asset_id) or not panel.has(market):
        return {c: None for c in candidates}

    market_series = panel.series(market)
    cache: dict[str, np.ndarray] = {}

    def resid(ticker: str) -> Optional[np.ndarray]:
        if ticker in cache:
            return cache[ticker]
        if not panel.has(ticker):
            return None
        r = _residual(panel.series(ticker), market_series)
        cache[ticker] = r
        return r

    a = resid(asset_id)
    if a is None:
        return {c: None for c in candidates}

    out: dict[str, Optional[float]] = {}
    for c in candidates:
        b = resid(c)
        if b is None or a.std() < 1e-12 or b.std() < 1e-12:
            out[c] = 0.0 if b is not None else None
            continue
        out[c] = float(np.corrcoef(a, b)[0, 1])
    return out


# ---------------------------------------------------------------------------
# 3. description similarity
# ---------------------------------------------------------------------------
_TOKEN_RE = re.compile(r"[a-z][a-z\-]{2,}")

_STOP = frozenset(
    """
    the and for with that from its their this are was were has have had not but
    which who whom into over under than then they them these those such other
    including include includes across within both each more most less least
    company companies corporation incorporated inc plc operates operating
    operate provider provides provider's group holding holdings limited ltd
    business businesses services service products product segment segments
    united states listed exchange traded fund index tracking track large mid
    small capitalisation capitalization global market markets sector
    """.split()
)


def _tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP]


def _doc(inst: Instrument) -> list[str]:
    return _tokens(f"{inst.description} {' '.join(inst.tags)}")


def description_scores(
    pack: Pack,
    asset_id: str,
    candidates: Iterable[str],
) -> dict[str, float]:
    """TF-IDF cosine over business summaries."""
    docs = {i.id: _doc(i) for i in pack}
    n_docs = len(docs)
    df: Counter[str] = Counter()
    for toks in docs.values():
        df.update(set(toks))

    idf = {t: math.log((n_docs + 1) / (c + 1)) + 1.0 for t, c in df.items()}

    def vec(tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        return {t: (1.0 + math.log(n)) * idf.get(t, 1.0) for t, n in tf.items()}

    vectors = {k: vec(v) for k, v in docs.items()}

    def cosine(a: Mapping[str, float], b: Mapping[str, float]) -> float:
        if not a or not b:
            return 0.0
        # iterate the shorter side
        if len(a) > len(b):
            a, b = b, a
        dot = sum(w * b.get(t, 0.0) for t, w in a.items())
        na = math.sqrt(sum(w * w for w in a.values()))
        nb = math.sqrt(sum(w * w for w in b.values()))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return dot / (na * nb)

    base = vectors.get(asset_id, {})
    return {
        c: cosine(base, vectors[c])
        for c in candidates
        if c != asset_id and c in vectors
    }


# ---------------------------------------------------------------------------
# convenience
# ---------------------------------------------------------------------------
def score_pair(
    pack: Pack,
    panel: Optional[ReturnPanel],
    asset_id: str,
    bench_id: str,
    config: SignalConfig = DEFAULT_CONFIG,
) -> dict[str, Optional[float]]:
    """All three raw scores for one pair."""
    return {
        "taxonomy": taxonomy_scores(pack, asset_id, [bench_id]).get(bench_id),
        "comovement": comovement_scores(panel, asset_id, [bench_id]).get(bench_id),
        "description": description_scores(pack, asset_id, [bench_id]).get(bench_id),
    }


def votes(scores: Mapping[str, Optional[float]], config: SignalConfig = DEFAULT_CONFIG) -> tuple[int, int]:
    """(votes_for, signals_available) for one pair."""
    available = 0
    cast = 0
    for name in SIGNAL_NAMES:
        value = scores.get(name)
        if value is None:
            continue
        available += 1
        if value >= config.threshold(name):
            cast += 1
    return cast, available
