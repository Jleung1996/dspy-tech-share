"""The curated benchmark pack and the 30-asset test bed.

Two things live here and they must stay separate:

1. ``PACK``   - the catalogue of instruments a system is *allowed* to pick from.
2. ``CASES``  - the assets under review, each carrying hand-curated ground truth
                about which catalogue entries really are economic peers.

The ground truth is hand-written on purpose.  If it were derived from the
taxonomy it would be circular and the whole triangulation exercise would be
meaningless.  It disagrees with the taxonomy in a handful of documented places
(see ``CONFLICT_NOTES``) and those disagreements are the most useful output of
the harness.

Descriptions are short business summaries.  They stand in for 10-K Item 1 text
and are only used by the description-similarity signal, which is a placeholder
for a real embedding model.
"""

from __future__ import annotations

from .model import (
    AG_MACH,
    AERO_DEF,
    BANKS,
    BR_BROAD,
    BR_INDUSTRY,
    BR_SECTOR,
    BROADLINE,
    CAPMKTS,
    CASH,
    CD,
    COMM,
    CONSTR_MACH,
    COPPER,
    CS,
    ELEC_UTIL,
    EN,
    ENTERTAIN,
    EP,
    EQUITY,
    EU,
    FIN,
    FIXED_INCOME,
    GBL,
    HC,
    HK,
    HOME_IMP,
    HOUSEHOLD,
    IND,
    IND_GAS,
    IND_REIT,
    INTEG_OIL,
    INTERACTIVE,
    IT,
    JP,
    MAT,
    MGD_CARE,
    PHARMA,
    RE,
    SEMI,
    SEMI_EQUIP,
    SG,
    SOFT_DRINK,
    SOFTWARE,
    TELECOM,
    TW,
    TXN,
    US,
    UTIL,
    Case,
    Instrument,
    Pack,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _eq(
    id_: str,
    name: str,
    sector: str,
    industry: str,
    region: str,
    ccy: str,
    description: str,
    *tags: str,
) -> Instrument:
    return Instrument(
        id=id_,
        name=name,
        kind="equity",
        asset_class=EQUITY,
        breadth=BR_INDUSTRY,
        sector=sector,
        industry=industry,
        region=region,
        currency=ccy,
        description=description,
        tags=tags,
    )


def _fund(
    id_: str,
    name: str,
    kind: str,
    breadth: str,
    region: str,
    ccy: str,
    description: str,
    sector: str | None = None,
    industry: str | None = None,
    asset_class: str = EQUITY,
    *tags: str,
) -> Instrument:
    return Instrument(
        id=id_,
        name=name,
        kind=kind,
        asset_class=asset_class,
        breadth=breadth,
        region=region,
        currency=ccy,
        sector=sector,
        industry=industry,
        description=description,
        tags=tags,
    )


_ALL: list[Instrument] = []


def _add(*instruments: Instrument) -> None:
    _ALL.extend(instruments)


# ---------------------------------------------------------------------------
# Information Technology - semiconductors
# ---------------------------------------------------------------------------
_add(
    _eq("EQ_NVDA", "NVIDIA Corporation", IT, SEMI, US, "USD",
        "Fabless semiconductor designer of graphics processing units and "
        "accelerated computing platforms for data centres, gaming and "
        "artificial intelligence", "gpu", "ai", "fabless"),
    _eq("EQ_AMD", "Advanced Micro Devices, Inc.", IT, SEMI, US, "USD",
        "Fabless designer of central processing units and graphics processing "
        "units for data centre, client and embedded computing", "cpu", "gpu", "fabless"),
    _eq("EQ_TSM", "Taiwan Semiconductor Manufacturing Company", IT, SEMI, TW, "USD",
        "Semiconductor foundry manufacturing chips on behalf of fabless designers "
        "at leading process nodes", "foundry", "manufacturing"),
    _eq("EQ_AVGO", "Broadcom Inc.", IT, SEMI, US, "USD",
        "Designer of networking, broadband and custom accelerator semiconductors "
        "with an infrastructure software segment", "networking", "custom silicon"),
    _eq("EQ_INTC", "Intel Corporation", IT, SEMI, US, "USD",
        "Integrated device manufacturer of processors that designs and fabricates "
        "chips in its own foundries", "cpu", "idm", "foundry"),
    _eq("EQ_QCOM", "Qualcomm Incorporated", IT, SEMI, US, "USD",
        "Fabless designer of mobile system-on-chip and wireless modem "
        "semiconductors with patent licensing", "mobile", "fabless"),
    _eq("EQ_MU", "Micron Technology, Inc.", IT, SEMI, US, "USD",
        "Manufacturer of dynamic random access memory and NAND flash memory "
        "semiconductors", "memory", "dram", "nand"),
)

# ---------------------------------------------------------------------------
# Information Technology - equipment and software
# ---------------------------------------------------------------------------
_add(
    _eq("EQ_ASML", "ASML Holding N.V.", IT, SEMI_EQUIP, EU, "USD",
        "Supplier of lithography systems used by semiconductor foundries and "
        "memory manufacturers to pattern wafers", "lithography", "equipment"),
    _eq("EQ_CRM", "Salesforce, Inc.", IT, SOFTWARE, US, "USD",
        "Provider of cloud customer relationship management and enterprise "
        "application software sold on subscription", "saas", "crm"),
    _eq("EQ_MSFT", "Microsoft Corporation", IT, SOFTWARE, US, "USD",
        "Provider of enterprise software, cloud infrastructure and productivity "
        "applications with a large hyperscale cloud business", "saas", "cloud"),
    _eq("EQ_ORCL", "Oracle Corporation", IT, SOFTWARE, US, "USD",
        "Provider of database management software and enterprise applications "
        "with a growing cloud infrastructure business", "database", "cloud"),
    _eq("EQ_ADBE", "Adobe Inc.", IT, SOFTWARE, US, "USD",
        "Provider of creative, document and marketing software sold on "
        "subscription", "saas", "creative"),
)

# ---------------------------------------------------------------------------
# Financials
# ---------------------------------------------------------------------------
_add(
    _eq("EQ_JPM", "JPMorgan Chase & Co.", FIN, BANKS, US, "USD",
        "Diversified bank operating consumer and commercial lending, payments "
        "and an investment bank", "bank", "lending", "deposits"),
    _eq("EQ_BAC", "Bank of America Corporation", FIN, BANKS, US, "USD",
        "Diversified bank operating consumer deposits, lending and wealth "
        "management", "bank", "lending", "deposits"),
    _eq("EQ_GS", "The Goldman Sachs Group, Inc.", FIN, CAPMKTS, US, "USD",
        "Investment bank and securities firm engaged in trading, underwriting "
        "and asset management", "investment bank", "trading"),
    _eq("EQ_MS", "Morgan Stanley", FIN, CAPMKTS, US, "USD",
        "Investment bank and wealth manager engaged in trading, underwriting "
        "and brokerage", "investment bank", "wealth"),
    _eq("EQ_V", "Visa Inc.", FIN, TXN, US, "USD",
        "Operator of a card payment network that clears and settles transactions "
        "and earns fees on payment volume", "payments", "network"),
    _eq("EQ_MA", "Mastercard Incorporated", FIN, TXN, US, "USD",
        "Operator of a card payment network earning fees on payment volume and "
        "cross border transactions", "payments", "network"),
)

# ---------------------------------------------------------------------------
# Health Care
# ---------------------------------------------------------------------------
_add(
    _eq("EQ_UNH", "UnitedHealth Group Incorporated", HC, MGD_CARE, US, "USD",
        "Manages health insurance plans and operates a medical services and "
        "pharmacy benefits business", "insurance", "managed care"),
    _eq("EQ_ELV", "Elevance Health, Inc.", HC, MGD_CARE, US, "USD",
        "Manages health insurance plans for commercial and government "
        "programmes", "insurance", "managed care"),
    _eq("EQ_JNJ", "Johnson & Johnson", HC, PHARMA, US, "USD",
        "Develops and sells pharmaceutical products and medical devices", "drugs", "medtech"),
    _eq("EQ_LLY", "Eli Lilly and Company", HC, PHARMA, US, "USD",
        "Develops and sells branded pharmaceutical products including diabetes "
        "and obesity treatments", "drugs", "branded"),
    _eq("EQ_PFE", "Pfizer Inc.", HC, PHARMA, US, "USD",
        "Develops and sells branded and generic pharmaceutical products and "
        "vaccines", "drugs", "vaccines"),
)

# ---------------------------------------------------------------------------
# Energy
# ---------------------------------------------------------------------------
_add(
    _eq("EQ_XOM", "Exxon Mobil Corporation", EN, INTEG_OIL, US, "USD",
        "Integrated energy company engaged in upstream oil and gas production, "
        "refining and chemicals", "oil", "integrated", "upstream"),
    _eq("EQ_CVX", "Chevron Corporation", EN, INTEG_OIL, US, "USD",
        "Integrated energy company engaged in crude oil and natural gas "
        "production, refining and marketing", "oil", "integrated", "upstream"),
    _eq("EQ_COP", "ConocoPhillips", EN, EP, US, "USD",
        "Independent exploration and production company focused on upstream oil "
        "and gas assets", "oil", "upstream", "e&p"),
    _eq("EQ_SLB", "SLB", EN, EP, US, "USD",
        "Provider of oilfield services, drilling technology and reservoir "
        "characterisation to upstream operators", "oilfield services", "equipment"),
)

# ---------------------------------------------------------------------------
# Consumer Staples
# ---------------------------------------------------------------------------
_add(
    _eq("EQ_KO", "The Coca-Cola Company", CS, SOFT_DRINK, US, "USD",
        "Manufactures and sells non-alcoholic beverages and concentrates under "
        "branded soft drink trademarks", "beverages", "branded", "consumer"),
    _eq("EQ_PEP", "PepsiCo, Inc.", CS, SOFT_DRINK, US, "USD",
        "Manufactures and sells branded beverages and packaged snack foods", "beverages",
        "snacks", "branded", "consumer"),
    _eq("EQ_PG", "The Procter & Gamble Company", CS, HOUSEHOLD, US, "USD",
        "Manufactures branded household and personal care consumer products "
        "including detergents and paper goods", "household", "consumer", "branded"),
)

# ---------------------------------------------------------------------------
# Industrials
# ---------------------------------------------------------------------------
_add(
    _eq("EQ_CAT", "Caterpillar Inc.", IND, CONSTR_MACH, US, "USD",
        "Manufactures construction, mining and earthmoving machinery and engines", "machinery",
        "construction", "capital goods"),
    _eq("EQ_DE", "Deere & Company", IND, AG_MACH, US, "USD",
        "Manufactures agricultural machinery, tractors and construction equipment", "machinery",
        "agriculture", "capital goods"),
    _eq("EQ_BA", "The Boeing Company", IND, AERO_DEF, US, "USD",
        "Designs and manufactures commercial jet aircraft and defence and space "
        "systems", "aerospace", "defence", "aircraft"),
    _eq("EQ_LMT", "Lockheed Martin Corporation", IND, AERO_DEF, US, "USD",
        "Designs and manufactures defence aerospace, missile and mission systems "
        "for government customers", "aerospace", "defence", "government"),
)

# ---------------------------------------------------------------------------
# Consumer Discretionary / Communication Services
# ---------------------------------------------------------------------------
_add(
    _eq("EQ_HD", "The Home Depot, Inc.", CD, HOME_IMP, US, "USD",
        "Operates warehouse format retail stores selling building materials and "
        "home improvement products", "retail", "home improvement"),
    _eq("EQ_LOW", "Lowe's Companies, Inc.", CD, HOME_IMP, US, "USD",
        "Operates retail stores selling building materials, appliances and home "
        "improvement products", "retail", "home improvement"),
    _eq("EQ_AMZN", "Amazon.com, Inc.", CD, BROADLINE, US, "USD",
        "Operates an online marketplace and retail business alongside a "
        "hyperscale cloud computing segment", "retail", "cloud", "ecommerce"),
)

_add(
    _eq("EQ_GOOGL", "Alphabet Inc.", COMM, INTERACTIVE, US, "USD",
        "Operates search, advertising, video and cloud computing businesses", "advertising",
        "search", "cloud"),
    _eq("EQ_META", "Meta Platforms, Inc.", COMM, INTERACTIVE, US, "USD",
        "Operates social networking and messaging platforms monetised through "
        "digital advertising", "advertising", "social", "digital"),
    _eq("EQ_NFLX", "Netflix, Inc.", COMM, ENTERTAIN, US, "USD",
        "Operates a subscription streaming video entertainment service", "streaming",
        "media", "subscription"),
    _eq("EQ_T", "AT&T Inc.", COMM, TELECOM, US, "USD",
        "Provides wireless and fixed line telecommunications and broadband "
        "services to consumers and businesses", "telecom", "wireless", "subscription"),
    _eq("EQ_VZ", "Verizon Communications Inc.", COMM, TELECOM, US, "USD",
        "Provides wireless telecommunications, broadband and fixed line services "
        "to consumer and enterprise subscribers", "telecom", "wireless", "subscription"),
)

# ---------------------------------------------------------------------------
# Utilities / Real Estate / Materials
# ---------------------------------------------------------------------------
_add(
    _eq("EQ_NEE", "NextEra Energy, Inc.", UTIL, ELEC_UTIL, US, "USD",
        "Operates regulated electric utilities and renewable power generation "
        "assets", "utility", "regulated", "renewables"),
    _eq("EQ_DUK", "Duke Energy Corporation", UTIL, ELEC_UTIL, US, "USD",
        "Operates regulated electric and gas utility businesses serving retail "
        "customers", "utility", "regulated"),
    _eq("EQ_PLD", "Prologis, Inc.", RE, IND_REIT, US, "USD",
        "Owns and operates logistics and industrial real estate properties as a "
        "real estate investment trust", "reit", "logistics"),
    _eq("EQ_LIN", "Linde plc", MAT, IND_GAS, US, "USD",
        "Produces and distributes industrial and medical gases and process "
        "technology", "industrial gases", "chemicals"),
    _eq("EQ_APD", "Air Products and Chemicals, Inc.", MAT, IND_GAS, US, "USD",
        "Produces and distributes industrial gases for manufacturing, energy and "
        "medical customers", "industrial gases", "chemicals"),
    _eq("EQ_FCX", "Freeport-McMoRan Inc.", MAT, COPPER, US, "USD",
        "Mines and produces copper, gold and molybdenum from operating deposits", "mining",
        "copper", "commodity"),
)

# ---------------------------------------------------------------------------
# Industry benchmarks - true peers at index level
# ---------------------------------------------------------------------------
_add(
    _fund("IDX_SOX", "PHLX Semiconductor Index", "index", BR_INDUSTRY, US, "USD",
          "Capitalisation weighted index tracking United States listed semiconductor "
          "design, manufacturing and equipment companies", IT, SEMI, EQUITY, "semis", "index"),
    _fund("ETF_SMH", "iShares Semiconductor ETF", "etf", BR_INDUSTRY, US, "USD",
          "Exchange traded fund tracking an index of United States listed "
          "semiconductor companies", IT, SEMI, EQUITY, "semis", "physical"),
    _fund("ETF_SOXX", "Invesco PHLX Semiconductor ETF", "etf", BR_INDUSTRY, US, "USD",
          "Exchange traded fund tracking the PHLX semiconductor index of chip "
          "design and manufacturing companies", IT, SEMI, EQUITY, "semis", "physical"),
    _fund("IDX_JP_SEMI", "TOPIX Semiconductor Index", "index", BR_INDUSTRY, JP, "JPY",
          "Index tracking Japanese listed semiconductor and semiconductor "
          "equipment companies", IT, SEMI, EQUITY, "semis", "japan"),
    _fund("IDX_HK_TECH", "Hang Seng TECH Index", "index", BR_SECTOR, HK, "HKD",
          "Index tracking large Hong Kong listed technology and internet "
          "companies", IT, None, EQUITY, "tech", "hong kong"),
)

# ---------------------------------------------------------------------------
# Sector benchmarks
# ---------------------------------------------------------------------------
_add(
    _fund("ETF_XLK", "Technology Select Sector SPDR Fund", "etf", BR_SECTOR, US, "USD",
          "Exchange traded fund tracking the United States information technology "
          "sector including software, hardware and semiconductor companies", IT, None),
    _fund("ETF_IGV", "iShares Expanded Tech-Software ETF", "etf", BR_SECTOR, US, "USD",
          "Exchange traded fund tracking United States software and application "
          "software companies", IT, None),
    _fund("ETF_XLF", "Financial Select Sector SPDR Fund", "etf", BR_SECTOR, US, "USD",
          "Exchange traded fund tracking the United States financial sector "
          "including banks, insurers and capital markets firms", FIN, None),
    _fund("ETF_XLV", "Health Care Select Sector SPDR Fund", "etf", BR_SECTOR, US, "USD",
          "Exchange traded fund tracking the United States health care sector "
          "including pharmaceuticals, devices and managed care", HC, None),
    _fund("ETF_XLE", "Energy Select Sector SPDR Fund", "etf", BR_SECTOR, US, "USD",
          "Exchange traded fund tracking the United States energy sector "
          "including integrated oil companies and oilfield services", EN, None),
    _fund("ETF_XLP", "Consumer Staples Select Sector SPDR Fund", "etf", BR_SECTOR, US, "USD",
          "Exchange traded fund tracking the United States consumer staples sector "
          "of food beverage and household product companies", CS, None),
    _fund("ETF_XLI", "Industrial Select Sector SPDR Fund", "etf", BR_SECTOR, US, "USD",
          "Exchange traded fund tracking the United States industrial sector "
          "including machinery, aerospace and transportation", IND, None),
    _fund("ETF_XLY", "Consumer Discretionary Select Sector SPDR Fund", "etf", BR_SECTOR, US, "USD",
          "Exchange traded fund tracking the United States consumer discretionary "
          "sector including retail and restaurants", CD, None),
    _fund("ETF_XLC", "Communication Services Select Sector SPDR Fund", "etf", BR_SECTOR, US,
          "USD",
          "Exchange traded fund tracking the United States communication services "
          "sector including media, internet and telecom companies", COMM, None),
    _fund("ETF_XLU", "Utilities Select Sector SPDR Fund", "etf", BR_SECTOR, US, "USD",
          "Exchange traded fund tracking the United States utilities sector of "
          "regulated electric and gas companies", UTIL, None),
    _fund("ETF_XLRE", "Real Estate Select Sector SPDR Fund", "etf", BR_SECTOR, US, "USD",
          "Exchange traded fund tracking the United States real estate sector of "
          "real estate investment trusts", RE, None),
    _fund("ETF_XLB", "Materials Select Sector SPDR Fund", "etf", BR_SECTOR, US, "USD",
          "Exchange traded fund tracking the United States materials sector "
          "including chemicals, mining and industrial gases", MAT, None),
)

# ---------------------------------------------------------------------------
# Broad equity references (legitimate, but NOT peers)
# ---------------------------------------------------------------------------
_add(
    _fund("IDX_SPX", "S&P 500 Index", "index", BR_BROAD, US, "USD",
          "Capitalisation weighted index of large United States listed companies "
          "spanning every sector", None, None, EQUITY, "broad", "us"),
    _fund("ETF_SPY", "SPDR S&P 500 ETF Trust", "etf", BR_BROAD, US, "USD",
          "Exchange traded fund tracking the S&P 500 index of large United States "
          "listed companies", None, None, EQUITY, "broad", "us"),
    _fund("IDX_NDX", "Nasdaq-100 Index", "index", BR_BROAD, US, "USD",
          "Index of the largest non financial companies listed on the Nasdaq "
          "exchange with a technology and growth tilt", None, None, EQUITY, "broad", "us"),
    _fund("ETF_QQQ", "Invesco QQQ Trust", "etf", BR_BROAD, US, "USD",
          "Exchange traded fund tracking the Nasdaq-100 index of large non "
          "financial growth companies", None, None, EQUITY, "broad", "us"),
    _fund("IDX_RUT", "Russell 2000 Index", "index", BR_BROAD, US, "USD",
          "Index of small capitalisation United States listed companies", None, None,
          EQUITY, "broad", "us"),
    _fund("IDX_MSCI_WORLD", "MSCI World Index", "index", BR_BROAD, GBL, "USD",
          "Index of large and mid capitalisation developed market equities across "
          "North America Europe and Asia Pacific", None, None, EQUITY, "broad", "global"),
    _fund("IDX_ACWI", "MSCI ACWI Index", "index", BR_BROAD, GBL, "USD",
          "Index of large and mid capitalisation equities across developed and "
          "emerging markets", None, None, EQUITY, "broad", "global"),
    _fund("ETF_VT", "Vanguard Total World Stock ETF", "etf", BR_BROAD, GBL, "USD",
          "Exchange traded fund tracking global developed and emerging market "
          "equity indices", None, None, EQUITY, "broad", "global"),
)

# ---------------------------------------------------------------------------
# Regional equity references
# ---------------------------------------------------------------------------
_add(
    _fund("IDX_TPX", "TOPIX Index", "index", BR_BROAD, JP, "JPY",
          "Capitalisation weighted index of Japanese listed companies across all "
          "sectors", None, None, EQUITY, "broad", "japan"),
    _fund("ETF_EWJ", "iShares MSCI Japan ETF", "etf", BR_BROAD, JP, "USD",
          "Exchange traded fund tracking Japanese large and mid capitalisation "
          "equities", None, None, EQUITY, "broad", "japan"),
    _fund("IDX_HSI", "Hang Seng Index", "index", BR_BROAD, HK, "HKD",
          "Capitalisation weighted index of Hong Kong listed companies", None, None,
          EQUITY, "broad", "hong kong"),
    _fund("ETF_EWH", "iShares MSCI Hong Kong ETF", "etf", BR_BROAD, HK, "USD",
          "Exchange traded fund tracking Hong Kong large and mid capitalisation "
          "equities", None, None, EQUITY, "broad", "hong kong"),
    _fund("IDX_SX5E", "STOXX Europe 600 Index", "index", BR_BROAD, EU, "EUR",
          "Index of large mid and small capitalisation European companies", None, None,
          EQUITY, "broad", "europe"),
    _fund("IDX_SGX", "Straits Times Index", "index", BR_BROAD, SG, "SGD",
          "Index of the largest companies listed on the Singapore Exchange", None, None,
          EQUITY, "broad", "singapore"),
)

# ---------------------------------------------------------------------------
# Fixed income and cash
# ---------------------------------------------------------------------------
_add(
    _fund("IDX_UST_AGG", "Bloomberg US Aggregate Bond Index", "index", BR_BROAD, US, "USD",
          "Index of United States investment grade government and corporate bonds "
          "of intermediate duration", None, None, FIXED_INCOME, "bonds", "ig"),
    _fund("ETF_AGG", "iShares Core US Aggregate Bond ETF", "etf", BR_BROAD, US, "USD",
          "Exchange traded fund tracking United States investment grade "
          "aggregate bond indices", None, None, FIXED_INCOME, "bonds", "ig"),
    _fund("ETF_TLT", "iShares 20+ Year Treasury Bond ETF", "etf", BR_BROAD, US, "USD",
          "Exchange traded fund holding long duration United States Treasury "
          "bonds", None, None, FIXED_INCOME, "treasuries", "long duration"),
    _fund("IDX_UST_10Y", "US Treasury 10 Year Note", "index", BR_BROAD, US, "USD",
          "On the run ten year United States Treasury note representing "
          "intermediate government bond duration", None, None, FIXED_INCOME,
          "treasuries", "intermediate duration"),
    _fund("ETF_LQD", "iShares iBoxx Investment Grade Corporate Bond ETF", "etf", BR_BROAD,
          US, "USD",
          "Exchange traded fund holding United States investment grade corporate "
          "bonds", None, None, FIXED_INCOME, "credit", "ig"),
    _fund("ETF_HYG", "iShares iBoxx High Yield Corporate Bond ETF", "etf", BR_BROAD, US,
          "USD",
          "Exchange traded fund holding below investment grade United States "
          "corporate bonds", None, None, FIXED_INCOME, "credit", "high yield"),
    _fund("IDX_ASIA_IG", "Asia USD Investment Grade Bond Index", "index", BR_BROAD, GBL,
          "USD",
          "Index of United States dollar denominated investment grade bonds "
          "issued by Asian sovereigns and corporates", None, None, FIXED_INCOME,
          "bonds", "asia", "ig"),
    _fund("IDX_SGS", "Singapore Government Securities Bond Index", "index", BR_BROAD, SG,
          "SGD",
          "Index of Singapore dollar denominated Singapore Government Securities "
          "of varying maturities", None, None, FIXED_INCOME, "bonds", "singapore", "sgd"),
    _fund("CASH_SGD", "Singapore Dollar Cash", "cash", BR_BROAD, SG, "SGD",
          "Singapore dollar deposit and liquidity balance held as a cash "
          "liquidity exposure", None, None, CASH, "cash", "liquidity"),
    _fund("CASH_USD", "US Dollar Cash", "cash", BR_BROAD, US, "USD",
          "United States dollar deposit and liquidity balance held as a cash "
          "liquidity exposure", None, None, CASH, "cash", "liquidity"),
)

PACK = Pack({i.id: i for i in _ALL})

if len(PACK) != len(_ALL):  # pragma: no cover - guards duplicate ids
    raise RuntimeError("duplicate instrument ids in PACK")


# ---------------------------------------------------------------------------
# Curated ground truth
# ---------------------------------------------------------------------------
#
# Reusable hand-curated groups.  Written once so the cases below stay
# auditable, but every use is an explicit human decision.
#
# The rule used throughout: a *peer* is same-industry and genuinely
# substitutable.  A sector index standing in for a narrow industry is
# *adjacent* - defensible, worth half credit, not a peer.

# ---- peer groups (same industry) -----------------------------------------
SEMI_PEERS = frozenset({
    "EQ_NVDA", "EQ_AMD", "EQ_TSM", "EQ_AVGO", "EQ_INTC", "EQ_QCOM", "EQ_MU",
    "EQ_ASML", "IDX_SOX", "ETF_SMH", "ETF_SOXX",
})
SOFTWARE_PEERS = frozenset({"EQ_CRM", "EQ_MSFT", "EQ_ORCL", "EQ_ADBE", "ETF_IGV"})
BANK_PEERS = frozenset({"EQ_JPM", "EQ_BAC"})
CAPMKTS_PEERS = frozenset({"EQ_GS", "EQ_MS"})
TXN_PEERS = frozenset({"EQ_V", "EQ_MA"})
MANCARE_PEERS = frozenset({"EQ_UNH", "EQ_ELV"})
PHARMA_PEERS = frozenset({"EQ_JNJ", "EQ_LLY", "EQ_PFE"})
OIL_PEERS = frozenset({"EQ_XOM", "EQ_CVX"})
EP_PEERS = frozenset({"EQ_COP", "EQ_XOM", "EQ_CVX"})
DRINK_PEERS = frozenset({"EQ_KO", "EQ_PEP"})
MACH_PEERS = frozenset({"EQ_CAT", "EQ_DE"})
AERO_PEERS = frozenset({"EQ_BA", "EQ_LMT"})
HOMEIMP_PEERS = frozenset({"EQ_HD", "EQ_LOW"})
INTERACTIVE_PEERS = frozenset({"EQ_GOOGL", "EQ_META"})
TELECOM_PEERS = frozenset({"EQ_T", "EQ_VZ"})
UTIL_PEERS = frozenset({"EQ_NEE", "EQ_DUK"})
GAS_PEERS = frozenset({"EQ_LIN", "EQ_APD"})

# ---- adjacent groups (sector proxies and cross-industry neighbours) ------
SEMI_ADJ = frozenset({"ETF_XLK", "IDX_NDX", "ETF_QQQ"})
SOFTWARE_ADJ = frozenset({"ETF_XLK", "IDX_NDX", "ETF_QQQ"})
BANK_ADJ = frozenset({"ETF_XLF", "EQ_GS", "EQ_MS"})
CAPMKTS_ADJ = frozenset({"ETF_XLF", "EQ_JPM", "EQ_BAC"})
TXN_ADJ = frozenset({"ETF_XLF"})
MANCARE_ADJ = frozenset({"ETF_XLV"})
PHARMA_ADJ = frozenset({"ETF_XLV"})
OIL_ADJ = frozenset({"ETF_XLE", "EQ_COP"})
EP_ADJ = frozenset({"ETF_XLE", "EQ_SLB"})
DRINK_ADJ = frozenset({"ETF_XLP", "EQ_PG"})
MACH_ADJ = frozenset({"ETF_XLI"})
AERO_ADJ = frozenset({"ETF_XLI"})
HOMEIMP_ADJ = frozenset({"ETF_XLY"})
INTERACTIVE_ADJ = frozenset({"ETF_XLC", "IDX_NDX"})
TELECOM_ADJ = frozenset({"ETF_XLC"})
UTIL_ADJ = frozenset({"ETF_XLU"})
REIT_ADJ = frozenset({"ETF_XLRE"})
GAS_ADJ = frozenset({"ETF_XLB"})
BROADLINE_ADJ = frozenset({"ETF_XLY", "IDX_NDX", "ETF_QQQ"})
ENTERTAIN_ADJ = frozenset({"ETF_XLC", "IDX_NDX", "EQ_GOOGL", "EQ_META"})

# ---- within-sector confusions -------------------------------------------
# These are the pairs a sector-level view gets wrong, so they carry the real
# discriminating power in the agreement report.
SW_FOR_SEMI = frozenset({"EQ_CRM", "EQ_MSFT", "EQ_ORCL", "EQ_ADBE", "ETF_IGV"})
SEMI_FOR_SW = frozenset({
    "EQ_NVDA", "EQ_AMD", "EQ_TSM", "EQ_AVGO", "EQ_INTC", "EQ_QCOM", "EQ_MU",
    "EQ_ASML", "IDX_SOX", "ETF_SMH", "ETF_SOXX",
})
PAY_FOR_BANK = frozenset({"EQ_V", "EQ_MA"})
BANK_FOR_PAY = frozenset({"EQ_JPM", "EQ_BAC"})
PHARMA_FOR_MANCARE = frozenset({"EQ_JNJ", "EQ_LLY", "EQ_PFE"})
MANCARE_FOR_PHARMA = frozenset({"EQ_UNH", "EQ_ELV"})
TEL_FOR_INTERNET = frozenset({"EQ_T", "EQ_VZ"})
INTERNET_FOR_TEL = frozenset({"EQ_GOOGL", "EQ_META", "EQ_NFLX"})
HOMEIMP_FOR_BROADLINE = frozenset({"EQ_HD", "EQ_LOW"})
MINING_FOR_GAS = frozenset({"EQ_FCX"})


def _cross_sector(asset_id: str) -> frozenset[str]:
    """Everything in the pack with a different asset class or sector.

    Mechanically derived, and that is a documented limitation: the taxonomy
    signal's precision against this set is partly true by construction.  The
    honest test of a signal is ``hard_negatives``, not this.
    """
    asset = PACK[asset_id]
    return frozenset(
        inst.id
        for inst in PACK
        if inst.id != asset_id
        and (inst.asset_class != asset.asset_class or inst.sector != asset.sector)
    )


# A broad equity index is a legitimate whole-portfolio comparison reference for
# *any* equity, so it is always adjacent rather than unacceptable.  It never
# counts as a peer: picking three broad indices is a valid answer to "give me
# references" and a useless answer to "find me a benchmark for this stock".
BROAD_REFS = frozenset(
    inst.id
    for inst in PACK
    if inst.breadth == BR_BROAD and inst.asset_class == EQUITY
)


def _case(
    asset_id: str,
    peers: frozenset[str],
    adjacent: frozenset[str] = frozenset(),
    hard_neg: frozenset[str] = frozenset(),
    note: str = "",
) -> Case:
    peer = peers - {asset_id}
    adj = (adjacent | BROAD_REFS) - {asset_id} - peer
    hard = hard_neg - {asset_id} - peer - adj
    cross = _cross_sector(asset_id) - peer - adj - hard
    return Case(
        asset_id=asset_id,
        acceptable=peer,
        adjacent=adj,
        hard_negatives=hard,
        unacceptable=cross,
        note=note,
    )


CASES: tuple[Case, ...] = (
    # ---- Information Technology -------------------------------------------
    _case("EQ_NVDA", SEMI_PEERS, SEMI_ADJ, SW_FOR_SEMI,
          "Reference case. AI/gaming GPU exposure. Salesforce here is the "
          "canonical wrong answer even though both are IT."),
    _case("EQ_AMD", SEMI_PEERS, SEMI_ADJ, SW_FOR_SEMI,
          "Fabless CPU/GPU designer competing directly with NVDA and INTC."),
    _case("EQ_TSM", SEMI_PEERS, SEMI_ADJ, SW_FOR_SEMI,
          "Look-through case: Taiwan domicile, USD-traded ADR. Currency is not "
          "domicile, so USD benchmarks are not automatically wrong."),
    _case("EQ_ASML", SEMI_PEERS, SEMI_ADJ, SW_FOR_SEMI,
          "Europe domicile, USD ADR, upstream of the semis complex. Curated as "
          "a peer by human judgement, which none of the three signals detect - "
          "a deliberate blind spot kept in to show where review is still needed."),
    _case("EQ_AVGO", SEMI_PEERS, SEMI_ADJ, SW_FOR_SEMI,
          "Semis with an infrastructure software segment."),
    _case("EQ_MU", SEMI_PEERS, SEMI_ADJ, SW_FOR_SEMI,
          "Memory cycle drives returns; high co-movement with the semis complex."),
    _case("EQ_CRM", SOFTWARE_PEERS, SOFTWARE_ADJ, SEMI_FOR_SW,
          "Enterprise SaaS. Failure mode: matching on 'tech' or market cap "
          "instead of software exposure."),
    _case("EQ_MSFT", SOFTWARE_PEERS, SOFTWARE_ADJ, SEMI_FOR_SW,
          "Software plus hyperscale cloud."),

    # ---- Financials --------------------------------------------------------
    _case("EQ_JPM", BANK_PEERS, BANK_ADJ, PAY_FOR_BANK,
          "Diversified bank. Payment networks share the sector but have no "
          "balance-sheet economics in common."),
    _case("EQ_V", TXN_PEERS, TXN_ADJ, BANK_FOR_PAY,
          "Payment network, not a lender. The test is whether the system reads "
          "industry rather than the sector label."),
    _case("EQ_GS", CAPMKTS_PEERS, CAPMKTS_ADJ, PAY_FOR_BANK,
          "Capital markets: trading and underwriting, not deposit spreads."),
    _case("EQ_MA", TXN_PEERS, TXN_ADJ, BANK_FOR_PAY,
          "Near-duplicate of V; useful for checking duplicate-diversity rules."),

    # ---- Health Care -------------------------------------------------------
    _case("EQ_UNH", MANCARE_PEERS, MANCARE_ADJ, PHARMA_FOR_MANCARE,
          "Managed care. Pharma shares the sector and almost none of the "
          "earnings drivers."),
    _case("EQ_LLY", PHARMA_PEERS, PHARMA_ADJ, MANCARE_FOR_PHARMA,
          "Branded pharma with a concentrated obesity franchise."),
    _case("EQ_PFE", PHARMA_PEERS, PHARMA_ADJ, MANCARE_FOR_PHARMA,
          "Large-cap pharma with a vaccine franchise."),

    # ---- Energy ------------------------------------------------------------
    _case("EQ_XOM", OIL_PEERS, OIL_ADJ, frozenset(),
          "Integrated oil: upstream, refining and chemicals."),
    _case("EQ_COP", EP_PEERS, EP_ADJ, frozenset(),
          "Pure upstream E&P; the tightest of the energy cases."),

    # ---- Consumer Staples --------------------------------------------------
    _case("EQ_KO", DRINK_PEERS, DRINK_ADJ, frozenset(),
          "Defensive branded beverage."),
    _case("EQ_PEP", DRINK_PEERS, DRINK_ADJ, frozenset(),
          "Beverages plus snacks; a small discretionary tilt."),

    # ---- Industrials -------------------------------------------------------
    _case("EQ_CAT", MACH_PEERS, MACH_ADJ, frozenset(),
          "Cyclical capital goods; Deere is a defensible peer despite a "
          "different end market."),
    _case("EQ_DE", MACH_PEERS, MACH_ADJ, frozenset(),
          "Agricultural machinery."),
    _case("EQ_BA", AERO_PEERS, AERO_ADJ, frozenset(),
          "Commercial aerospace with defence overlap."),

    # ---- Consumer Discretionary / Communication ---------------------------
    _case("EQ_HD", HOMEIMP_PEERS, HOMEIMP_ADJ, frozenset(),
          "Housing-linked retail."),
    _case("EQ_AMZN", frozenset(), BROADLINE_ADJ, HOMEIMP_FOR_BROADLINE,
          "No true peer in this pack: the graceful-degradation case. The best "
          "available answers are broad or sector references, and the system "
          "should say so rather than manufacture a peer."),
    _case("EQ_GOOGL", INTERACTIVE_PEERS, INTERACTIVE_ADJ, TEL_FOR_INTERNET,
          "Advertising-funded internet platform."),
    _case("EQ_NFLX", frozenset(), ENTERTAIN_ADJ, TEL_FOR_INTERNET,
          "Subscription streaming; no same-industry peer in the pack."),
    _case("EQ_T", TELECOM_PEERS, TELECOM_ADJ, INTERNET_FOR_TEL,
          "Sector is Communication Services but the industry is telecom, not "
          "internet. Tests over-trust of the sector label."),

    # ---- Utilities / Real Estate / Materials ------------------------------
    _case("EQ_NEE", UTIL_PEERS, UTIL_ADJ, frozenset(),
          "Regulated utility with a renewables development arm."),
    _case("EQ_PLD", frozenset(), REIT_ADJ, frozenset(),
          "Logistics REIT: narrow industry, thin peer group by construction."),
    _case("EQ_LIN", GAS_PEERS, GAS_ADJ, MINING_FOR_GAS,
          "Industrial gases: materials sector, defensive cash-flow profile."),
)

CASE_BY_ASSET: dict[str, Case] = {c.asset_id: c for c in CASES}

if len(CASE_BY_ASSET) != len(CASES):  # pragma: no cover
    raise RuntimeError("duplicate asset ids in CASES")

for _c in CASES:
    _known = _c.acceptable | _c.adjacent | _c.hard_negatives | _c.unacceptable
    _missing = {i for i in _known if i not in PACK}
    if _missing:  # pragma: no cover
        raise RuntimeError(f"case {_c.asset_id} references unknown ids {sorted(_missing)}")
    if _c.asset_id not in PACK:  # pragma: no cover
        raise RuntimeError(f"case asset {_c.asset_id} is not in the pack")


# ---------------------------------------------------------------------------
# Documented places where a proxy cannot see what a human can.
# ---------------------------------------------------------------------------
CONFLICT_NOTES: dict[tuple[str, str], str] = {
    ("EQ_ASML", "EQ_AMD"): (
        "Different industry (Semiconductor Equipment vs Semiconductors) but "
        "tightly coupled through the foundry supply chain. Taxonomy under-rates."
    ),
    ("EQ_NVDA", "EQ_ASML"): (
        "Upstream supplier, not a product peer. Curated as acceptable because "
        "the exposure is genuinely linked, but no proxy in this harness sees it."
    ),
    ("EQ_T", "EQ_GOOGL"): (
        "Same Communication Services sector, unrelated industry. A sector-only "
        "signal calls this a peer; a human does not."
    ),
    ("EQ_V", "EQ_JPM"): (
        "Both Financials. Payments networks and banks share almost no "
        "balance-sheet economics; sector-only matching fails here."
    ),
    ("EQ_LIN", "EQ_FCX"): (
        "Both Materials. Industrial gases and copper mining have nothing in "
        "common except the sector label."
    ),
    ("EQ_AMZN", "EQ_HD"): (
        "Both Consumer Discretionary, both retail, entirely different margin "
        "structures and demand drivers."
    ),
}
