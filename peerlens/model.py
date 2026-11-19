"""Core data model for the peer-labelling harness.

The taxonomy is a deliberately simplified GICS-style tree:

    sector (11)
      └── industry (fine-grained)

Every catalogue entry also carries a ``breadth`` marker that says how much of the
economy the instrument spans.  This matters because a broad index is a
*legitimate* whole-portfolio reference for almost any asset, but it is not a
*peer*.  The peer metric must reward specificity, so breadth is first-class data
rather than something we try to infer from the name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# --------------------------------------------------------------------------
# asset classes
# --------------------------------------------------------------------------
EQUITY = "Equity"
FIXED_INCOME = "Fixed Income"
CASH = "Cash"

# --------------------------------------------------------------------------
# sectors (GICS-style, 11)
# --------------------------------------------------------------------------
IT = "Information Technology"
FIN = "Financials"
HC = "Health Care"
CD = "Consumer Discretionary"
CS = "Consumer Staples"
EN = "Energy"
IND = "Industrials"
MAT = "Materials"
UTIL = "Utilities"
RE = "Real Estate"
COMM = "Communication Services"

SECTORS = (IT, FIN, HC, CD, CS, EN, IND, MAT, UTIL, RE, COMM)

# --------------------------------------------------------------------------
# industries (fine-grained)
# --------------------------------------------------------------------------
SEMI = "Semiconductors"
SEMI_EQUIP = "Semiconductor Equipment"
TECH_HW = "Technology Hardware"
SOFTWARE = "Software"
BANKS = "Banks"
CAPMKTS = "Capital Markets"
TXN = "Transaction Processing"
MGD_CARE = "Managed Health Care"
PHARMA = "Pharmaceuticals"
INTEG_OIL = "Integrated Oil & Gas"
EP = "Oil & Gas Exploration & Production"
SOFT_DRINK = "Soft Drinks"
HOUSEHOLD = "Household Products"
CONSTR_MACH = "Construction Machinery"
AG_MACH = "Agricultural Machinery"
AERO_DEF = "Aerospace & Defense"
HOME_IMP = "Home Improvement Retail"
BROADLINE = "Broadline Retail"
INTERACTIVE = "Interactive Media"
ENTERTAIN = "Entertainment"
TELECOM = "Telecom"
ELEC_UTIL = "Electric Utility"
IND_REIT = "Industrial REIT"
IND_GAS = "Industrial Gases"
COPPER = "Copper"

# --------------------------------------------------------------------------
# regions / currencies
# --------------------------------------------------------------------------
US = "United States"
JP = "Japan"
HK = "Hong Kong"
EU = "Europe"
TW = "Taiwan"
SG = "Singapore"
GBL = "Global"

# --------------------------------------------------------------------------
# breadth of a benchmark's exposure
# --------------------------------------------------------------------------
BR_INDUSTRY = "industry"  # tracks one industry: a true peer
BR_SECTOR = "sector"      # tracks one sector: a loose peer
BR_BROAD = "broad"        # whole-market / multi-asset: a reference, not a peer

# how much credit each breadth tier earns from the taxonomy signal
BREADTH_CREDIT = {BR_INDUSTRY: 1.0, BR_SECTOR: 0.45, BR_BROAD: 0.20}


@dataclass(frozen=True)
class Instrument:
    """A catalogue entry that may be used as a benchmark reference.

    ``name`` is the catalogue name.  Downstream contracts require it to be
    reproduced exactly, so it is treated as an opaque identifier, never as
    a source of meaning to be paraphrased.
    """

    id: str
    name: str
    kind: str                      # "index" | "etf" | "equity" | "cash"
    asset_class: str
    breadth: str
    region: str
    currency: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_broad_reference(self) -> bool:
        return self.breadth == BR_BROAD


@dataclass(frozen=True)
class Case:
    """One asset under review, plus curated ground truth about its peers.

    Four tiers, because 'is this a good benchmark' is not a yes/no question:

    ``acceptable``    peer-level: same industry, genuinely substitutable.
    ``adjacent``      defensible comparison reference, but a weaker proxy -
                      a sector index standing in for a narrow industry, or a
                      same-sector neighbour with a different earnings driver.
    ``hard_negatives`` same sector, clearly *not* a peer.  This is the set that
                      actually discriminates between signals: anyone can reject
                      oil for a semiconductor, but only a real analysis rejects
                      a payments network as a bank benchmark.
    ``unacceptable``  cross-sector and cash/bond mismatches.  Documented as
                      partly implied by the taxonomy definition, so the
                      informative test is ``hard_negatives``.

    Everything else in the pack is neutral and unscored.
    """

    asset_id: str
    acceptable: frozenset[str]
    adjacent: frozenset[str] = frozenset()
    hard_negatives: frozenset[str] = frozenset()
    unacceptable: frozenset[str] = frozenset()
    note: str = ""

    def __post_init__(self) -> None:
        groups = {
            "acceptable": self.acceptable,
            "adjacent": self.adjacent,
            "hard_negatives": self.hard_negatives,
            "unacceptable": self.unacceptable,
        }
        names = list(groups)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                overlap = groups[a] & groups[b]
                if overlap:
                    raise ValueError(
                        f"case {self.asset_id}: {sorted(overlap)} marked both "
                        f"{a} and {b} - ground truth is contradictory"
                    )

    @property
    def negatives(self) -> frozenset[str]:
        return self.unacceptable | self.hard_negatives


@dataclass(frozen=True)
class Pack:
    """An immutable catalogue of benchmark references."""

    instruments: dict[str, Instrument]

    def __getitem__(self, key: str) -> Instrument:
        return self.instruments[key]

    def get(self, key: str) -> Optional[Instrument]:
        return self.instruments.get(key)

    def __contains__(self, key: object) -> bool:
        return key in self.instruments

    def __iter__(self):
        return iter(self.instruments.values())

    def __len__(self) -> int:
        return len(self.instruments)

    @property
    def ids(self) -> frozenset[str]:
        return frozenset(self.instruments)

    @property
    def names(self) -> dict[str, str]:
        return {k: v.name for k, v in self.instruments.items()}
