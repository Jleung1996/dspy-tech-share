"""Return history for the co-movement signal.

Two paths, deliberately kept apart:

``load_returns_csv``      - the real path.  A CSV of dates x tickers.
``synthetic_panel``       - a seeded factor model used to exercise the
                            pipeline when no market feed is available.

The synthetic panel is **not market data**.  It exists so the harness can be
tested end to end and so the conflict report can be validated against a process
whose structure is known.  Every number it produces should be read as a test
fixture, never as a finding about real securities.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Optional

import numpy as np

from .model import CASH, EQUITY, FIXED_INCOME, Pack

MARKET_PROXY = "ETF_SPY"


@dataclass(frozen=True)
class ReturnPanel:
    """Simple daily return matrix aligned to a ticker list."""

    tickers: tuple[str, ...]
    dates: tuple[date, ...]
    values: np.ndarray  # shape (len(dates), len(tickers))

    def __post_init__(self) -> None:
        if self.values.shape != (len(self.dates), len(self.tickers)):
            raise ValueError(
                f"panel shape {self.values.shape} does not match "
                f"{len(self.dates)} dates x {len(self.tickers)} tickers"
            )

    @property
    def column(self) -> dict[str, int]:
        return {t: i for i, t in enumerate(self.tickers)}

    def series(self, ticker: str) -> np.ndarray:
        return self.values[:, self.column[ticker]]

    def has(self, ticker: str) -> bool:
        return ticker in self.column

    def __len__(self) -> int:
        return len(self.dates)


def synthetic_panel(
    pack: Pack,
    n_days: int = 750,
    seed: int = 7,
    start: date = date(2022, 1, 3),
) -> ReturnPanel:
    """Generate a factor-model return panel with a known peer structure.

    Equities load on a market factor, a sector factor and an industry factor.
    Instruments sharing an industry therefore share a real common component,
    which is what makes residual correlation a meaningful proxy for peer-ness.
    """
    rng = np.random.default_rng(seed)

    instruments = [i for i in pack]
    tickers = tuple(i.id for i in instruments)

    sectors = sorted({i.sector for i in instruments if i.sector})
    industries = sorted({i.industry for i in instruments if i.industry})

    # --- factors ---------------------------------------------------------
    # Volatility of each layer is chosen so that, after the market factor is
    # removed, same-industry names land around 0.7-0.8 residual correlation,
    # same-sector-different-industry around 0.15, and cross-sector near zero.
    # That is the separation the labelling logic needs in order to be useful.
    market = rng.normal(0.0004, 0.0095, n_days)
    sector_f = {s: rng.normal(0.0001, 0.0050, n_days) for s in sectors}
    ind_f = {k: rng.normal(0.0001, 0.0060, n_days) for k in industries}
    rates_f = rng.normal(0.0001, 0.0040, n_days)  # duration factor

    # --- loadings --------------------------------------------------------
    cols: list[np.ndarray] = []
    for inst in instruments:
        if inst.id == MARKET_PROXY:
            # the market proxy *is* the market factor, so residual correlation
            # against it is what separates industry peers from market beta
            cols.append(market + rng.normal(0, 0.0006, n_days))
            continue

        if inst.asset_class == CASH:
            cols.append(np.full(n_days, 0.0001) + rng.normal(0, 0.0002, n_days))
            continue

        if inst.asset_class == FIXED_INCOME:
            dur = -0.35 if "long duration" in inst.tags else -0.12
            credit = 0.25 if "high yield" in inst.tags else 0.0
            vol = 0.0022 if "long duration" in inst.tags else 0.0011
            cols.append(
                dur * rates_f
                + credit * market
                + rng.normal(0.00005, vol, n_days)
            )
            continue

        # equities: beta to the market, then a breadth-dependent exposure
        ret = rng.normal(1.0, 0.15) * market

        if inst.breadth == "industry" and inst.industry in ind_f:
            # an industry index *is* its industry, with very little else
            ret += ind_f[inst.industry]
            if inst.sector in sector_f:
                ret += rng.normal(0.30, 0.05) * sector_f[inst.sector]
            ret += rng.normal(0, 0.0015, n_days)
        elif inst.breadth == "sector" and inst.sector in sector_f:
            ret += rng.normal(0.95, 0.10) * sector_f[inst.sector]
            ret += rng.normal(0, 0.0020, n_days)
        elif inst.breadth == "broad":
            ret += rng.normal(0, 0.0040, n_days)
        elif inst.industry and inst.industry in ind_f:
            if inst.sector and inst.sector in sector_f:
                ret += rng.normal(0.55, 0.10) * sector_f[inst.sector]
            ret += rng.normal(0.95, 0.12) * ind_f[inst.industry]
            ret += rng.normal(0, 0.0035, n_days)
        elif inst.sector and inst.sector in sector_f:
            ret += rng.normal(0.95, 0.12) * sector_f[inst.sector]
            ret += rng.normal(0, 0.0050, n_days)
        else:
            ret += rng.normal(0, 0.0090, n_days)

        cols.append(ret)

    values = np.column_stack(cols)
    dates = tuple(start + timedelta(days=i) for i in range(n_days))
    return ReturnPanel(tickers=tickers, dates=dates, values=values)


def load_returns_csv(
    path: str | Path,
    tickers: Optional[Iterable[str]] = None,
    date_column: str = "date",
) -> ReturnPanel:
    """Load a real returns CSV: one date column plus one column per ticker.

    Missing values are forward-filled then zero-filled, which is the least
    surprising behaviour for a panel that is only used to compute correlations.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    if not rows:
        raise ValueError(f"{path} is empty")

    header = list(rows[0].keys())
    if date_column not in header:
        raise ValueError(f"{path}: no {date_column!r} column (found {header})")

    wanted = [t for t in (tickers if tickers is not None else header) if t != date_column]
    missing = [t for t in wanted if t not in header]
    if missing:
        raise ValueError(f"{path}: columns not found for {missing}")

    dates: list[date] = []
    matrix: list[list[float]] = []
    for row in rows:
        raw = row[date_column]
        dates.append(date.fromisoformat(raw[:10]))
        matrix.append([_to_float(row.get(t)) for t in wanted])

    arr = np.array(matrix, dtype=float)
    # forward fill, then back fill, then zero
    for c in range(arr.shape[1]):
        col = arr[:, c]
        mask = np.isnan(col)
        if mask.all():
            arr[:, c] = 0.0
            continue
        if mask.any():
            idx = np.where(~mask, np.arange(len(col)), 0)
            np.maximum.accumulate(idx, out=idx)
            col = col[idx]
            arr[:, c] = np.nan_to_num(col, nan=0.0)

    return ReturnPanel(tickers=tuple(wanted), dates=tuple(dates), values=arr)


def _to_float(raw: str | None) -> float:
    if raw is None or raw == "":
        return float("nan")
    return float(raw)


def percentile_returns(panel: ReturnPanel, windows: int = 3) -> ReturnPanel:
    """Roll a returns panel up into non-overlapping period returns.

    Correlations on daily data are dominated by market noise; period returns
    (monthly-ish) are what a benchmark review actually cares about.
    """
    n = len(panel)
    step = max(1, n // windows)
    rows: list[np.ndarray] = []
    dates: list[date] = []
    for start in range(0, n - step + 1, step):
        block = panel.values[start:start + step]
        rows.append(np.prod(1.0 + block, axis=0) - 1.0)
        dates.append(panel.dates[start + step - 1])
    return ReturnPanel(tickers=panel.tickers, dates=tuple(dates),
                       values=np.vstack(rows))
